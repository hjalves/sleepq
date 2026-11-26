"""sleepq-remote: web front-end for a sleepq queue repo.

Works only through git, so it is useful while the sleepq machine is asleep: it shows the queue,
the HOLD switch and recent results from its own clone of the queue repo, and can commit a HOLD
file, remove it, queue a command or cancel a pending task. If the machine's `sleepq web` page is
reachable it also shows its live status (and remembers the last one it saw).

Configuration (environment):
  SLEEPQ_REMOTE_REPO    git URL of the queue repo (required)
  SLEEPQ_REMOTE_DIR     where to keep the clone (default ./data/repo)
  SLEEPQ_REMOTE_KEY     ssh private key for pushing (default: $CREDENTIALS_DIRECTORY/deploy_key)
  SLEEPQ_REMOTE_BRANCH  default main
  SLEEPQ_REMOTE_LIVE    URL of the machine's `sleepq web` /api/status (optional)
  SLEEPQ_REMOTE_LISTEN  address:port (default 0.0.0.0:8378)
"""

import datetime as dt
import json
import os
import re
import socket
import socketserver
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
HEADER_RE = re.compile(r"^#\s*sleepq:\s*([\w-]+)\s*=\s*(.+?)\s*$")
DURATION_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([smhd]?)")
FETCH_EVERY = 60   # seconds between background fetches
LIVE_EVERY = 30    # seconds between live-status polls


def parse_duration(value):
    """Same syntax sleepq accepts: 90s, 5m, 1h30m, 2d."""
    text = str(value).strip().lower()
    pos, total = 0, 0.0
    for m in DURATION_RE.finditer(text):
        if text[pos:m.start()].strip():
            break
        total += float(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]
        pos = m.end()
    if pos == 0 or text[pos:].strip():
        raise ValueError(f"bad duration: {value!r} (use e.g. 90s, 5m, 1h30m)")
    return total


class Busy(Exception):
    pass


class Queue:
    def __init__(self):
        self.url = os.environ["SLEEPQ_REMOTE_REPO"]
        self.dir = Path(os.environ.get("SLEEPQ_REMOTE_DIR", "data/repo")).resolve()
        self.branch = os.environ.get("SLEEPQ_REMOTE_BRANCH", "main")
        key = os.environ.get("SLEEPQ_REMOTE_KEY") or (
            Path(os.environ["CREDENTIALS_DIRECTORY"]) / "deploy_key"
            if "CREDENTIALS_DIRECTORY" in os.environ else None)
        known = self.dir.parent / "known_hosts"
        self.ssh = ("ssh -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new "
                    f"-o UserKnownHostsFile={known}" + (f" -i {key}" if key else ""))
        self.lock = threading.Lock()
        self.fetched_at = None
        self.fetch_error = None
        self.host = socket.gethostname()

    def git(self, *args, check=True, cwd=True):
        cmd = ["git", *(["-C", str(self.dir)] if cwd else []), "-c", "safe.directory=*",
               "-c", "user.name=sleepq-remote", "-c", f"user.email=sleepq-remote@{self.host}", *args]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                           env=os.environ | {"GIT_SSH_COMMAND": self.ssh, "GIT_TERMINAL_PROMPT": "0"})
        if check and r.returncode != 0:
            raise RuntimeError(f"git {args[0]} failed: {(r.stderr or r.stdout).strip()[-400:]}")
        return r

    def fetch(self):
        """Bring the clone to the remote's state (cloning on first use)."""
        with self.lock:
            try:
                if not (self.dir / ".git").exists():
                    self.dir.parent.mkdir(parents=True, exist_ok=True)
                    self.git("clone", "-q", "-b", self.branch, self.url, str(self.dir), cwd=False)
                else:
                    self.git("fetch", "-q", "origin", self.branch)
                    self.git("reset", "-q", "--hard", f"origin/{self.branch}")
                    self.git("clean", "-qfd")
                self.fetched_at, self.fetch_error = time.time(), None
            except Exception as e:  # noqa: BLE001 - shown on the page
                self.fetch_error = str(e)

    def change(self, message, apply):
        """Fresh state, apply(), commit, push; on a rejected push (the machine pushed meanwhile)
        start over from the new remote state. apply() returns False when there is nothing to do."""
        with self.lock:
            last = None
            for _ in range(4):
                self.git("fetch", "-q", "origin", self.branch)
                self.git("reset", "-q", "--hard", f"origin/{self.branch}")
                self.git("clean", "-qfd")
                if apply(self.dir) is False:
                    return
                self.git("add", "-A")
                if self.git("diff", "--cached", "--quiet", check=False).returncode == 0:
                    return
                self.git("commit", "-q", "-m", message)
                r = self.git("push", "-q", "origin", f"HEAD:{self.branch}", check=False)
                if r.returncode == 0:
                    self.fetched_at, self.fetch_error = time.time(), None
                    return
                last = r.stderr.strip()
            raise RuntimeError(f"push kept failing: {last[-400:] if last else '?'}")

    # ---------- reading ----------

    def last_commit(self, path):
        r = self.git("log", "-1", "--format=%cI%x00%s", "--", path, check=False)
        if r.returncode or not r.stdout.strip():
            return None
        when, subject = r.stdout.strip().split("\0", 1)
        return {"when": when, "subject": subject}

    def state(self):
        d = self.dir
        pending = []
        if (d / "queue").is_dir():
            for p in sorted(d / "queue" / n for n in os.listdir(d / "queue")):
                if not p.is_file() or p.name.startswith("."):
                    continue
                text = p.read_text(errors="replace")
                headers = {}
                for line in text.splitlines()[:40]:
                    m = HEADER_RE.match(line.strip())
                    if m:
                        headers[m.group(1).lower()] = m.group(2)
                pending.append({"name": p.name, "headers": headers, "script": text[:4000]})
        results = []
        if (d / "results").is_dir():
            dirs = sorted((p for p in (d / "results").iterdir() if p.is_dir()), reverse=True)[:15]
            for p in dirs:
                try:
                    r = json.loads((p / "result.json").read_text())
                except (OSError, ValueError):
                    r = {"id": p.name, "status": "?"}
                results.append(r | {"dir": p.name})
        hold = (d / "HOLD").exists()
        return {
            "repo": self.url, "fetched_at": self.fetched_at, "fetch_error": self.fetch_error,
            "hold": hold, "hold_commit": self.last_commit("HOLD"),
            "hold_text": (d / "HOLD").read_text(errors="replace")[:500] if hold else "",
            "pending": pending, "results": results,
        }

    def result_log(self, name):
        p = self.dir / "results" / name
        if not re.fullmatch(r"[\w.-]+", name) or not p.is_dir():
            return None
        files = {f.name: f for f in p.iterdir() if f.is_file()}
        out = files.get("output.log")
        script = next((f for n, f in files.items() if n.endswith(".sh")), None)
        return {"script": script.read_text(errors="replace") if script else "",
                "output": out.read_text(errors="replace") if out else "(no output.log)"}

    # ---------- writing ----------

    def set_hold(self, on, who):
        def apply(d):
            f = d / "HOLD"
            if on == f.exists():
                return False
            if on:
                f.write_text(f"Held from the sleepq-remote page on {self.host} by {who} "
                             f"at {dt.datetime.now().astimezone():%Y-%m-%d %H:%M %Z}.\n")
            else:
                f.unlink()
        self.change("Hold: keep machine awake" if on else "Release hold", apply)

    def submit(self, command, name, not_before, timeout):
        if not command.strip():
            raise ValueError("empty command")
        headers = []
        if not_before:
            nb = dt.datetime.fromisoformat(not_before)
            nb = nb if nb.tzinfo else nb.astimezone()
            headers.append(f"# sleepq: not-before={nb.isoformat(timespec='seconds')}")
        if timeout:
            parse_duration(timeout)
            headers.append(f"# sleepq: timeout={timeout.strip()}")
        body = "#!/bin/bash\n" + "".join(h + "\n" for h in headers) + "set -euo pipefail\n" \
            + command.replace("\r\n", "\n").rstrip("\n") + "\n"
        name = re.sub(r"[^\w.-]+", "-", name or "cmd").strip("-")[:40] or "cmd"
        task_id = f"{dt.datetime.now():%Y%m%d-%H%M%S}-{name}"

        def apply(d):
            (d / "queue").mkdir(exist_ok=True)
            (d / "queue" / f"{task_id}.sh").write_text(body)
        self.change(f"submit {task_id}", apply)
        return task_id

    def cancel(self, name):
        if not re.fullmatch(r"[\w.-]+", name):
            raise ValueError("bad task name")

        def apply(d):
            f = d / "queue" / name
            if not f.exists():
                raise Busy(f"{name} is no longer pending (it may have started already)")
            f.unlink()
        self.change(f"cancel {Path(name).stem}", apply)


class Live:
    """Polls the machine's `sleepq web` status; keeps the last successful answer."""

    def __init__(self, url):
        self.url = url
        self.last = None
        self.last_ok_at = None
        self.checked_at = None
        self.awake = False

    def poll(self):
        if not self.url:
            return
        try:
            with urllib.request.urlopen(self.url, timeout=4) as r:
                self.last = json.load(r)
            self.awake, self.last_ok_at = True, time.time()
        except Exception:  # noqa: BLE001 - asleep or unreachable look the same
            self.awake = False
        self.checked_at = time.time()

    def state(self):
        return {"configured": bool(self.url), "awake": self.awake, "checked_at": self.checked_at,
                "last_ok_at": self.last_ok_at, "status": self.last}


def serve(queue, live, listen):
    page = (HERE / "static" / "index.html").read_bytes()

    def snapshot():
        return queue.state() | {"live": live.state()}

    class Handler(BaseHTTPRequestHandler):
        def send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", f"{ctype}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/":
                return self.send(200, page, "text/html")
            if path == "/api/state":
                return self.send(200, snapshot())
            m = re.fullmatch(r"/api/result/([\w.-]+)", path)
            if m:
                r = queue.result_log(m.group(1))
                return self.send(200, r) if r else self.send(404, {"error": "no such result"})
            self.send(404, {"error": "not found"})

        def do_POST(self):
            # A custom header can't be sent cross-origin without a CORS preflight, which is never
            # answered, so other web pages can't make a visitor's browser queue commands here.
            if self.headers.get("X-Sleepq") != "1":
                return self.send(403, {"error": "missing X-Sleepq header"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                who = self.client_address[0]
                if self.path == "/api/hold":
                    queue.set_hold(bool(body.get("on")), who)
                    msg = "HOLD committed" if body.get("on") else "HOLD removed"
                elif self.path == "/api/submit":
                    tid = queue.submit(body.get("command", ""), body.get("name", ""),
                                       body.get("not_before", ""), body.get("timeout", ""))
                    msg = f"queued {tid}"
                elif self.path == "/api/cancel":
                    queue.cancel(body.get("name", ""))
                    msg = f"cancelled {body.get('name')}"
                elif self.path == "/api/refresh":
                    queue.fetch()
                    live.poll()
                    msg = "refreshed"
                else:
                    return self.send(404, {"error": "not found"})
                print(f"{who}: {msg}", flush=True)
                return self.send(200, snapshot() | {"message": msg})
            except (ValueError, Busy) as e:
                return self.send(400, {"error": str(e)})
            except Exception as e:  # noqa: BLE001
                return self.send(502, {"error": str(e)})

        def log_message(self, *a):
            pass

    class Server(ThreadingHTTPServer):
        daemon_threads = True

        def server_bind(self):  # skip HTTPServer's reverse DNS lookup (getfqdn), slow on some LANs
            socketserver.TCPServer.server_bind(self)
            self.server_name, self.server_port = queue.host, self.server_address[1]

    host, _, port = listen.rpartition(":")
    print(f"sleepq-remote on {listen}: repo {queue.url}, live {live.url or '-'}", flush=True)
    Server((host.strip("[]") or "0.0.0.0", int(port)), Handler).serve_forever()


def background(queue, live):
    next_fetch = 0
    while True:
        if time.monotonic() >= next_fetch:
            queue.fetch()
            next_fetch = time.monotonic() + FETCH_EVERY
        live.poll()
        time.sleep(LIVE_EVERY)


def main():
    queue = Queue()
    live = Live(os.environ.get("SLEEPQ_REMOTE_LIVE", ""))
    threading.Thread(target=background, args=(queue, live), daemon=True).start()
    serve(queue, live, os.environ.get("SLEEPQ_REMOTE_LISTEN", "0.0.0.0:8378"))


if __name__ == "__main__":
    main()
