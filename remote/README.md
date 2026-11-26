# sleepq-remote

A web page for controlling sleepq from another machine that is always on, such as a home server.
It works only through the queue repo, so it is useful while the sleepq machine is asleep:

- **Hold / Release:** commit or delete the `HOLD` file. The machine stays awake from its next wake
  until the file is deleted.
- **Queue a command:** write `queue/<timestamp>-<name>.sh` in the same format as `sleepq submit -c`,
  with optional `not-before` and `timeout` headers. It runs at the next wake.
- **Cancel** a pending task (if it hasn't started yet).
- **See** pending tasks, recent results and their output.

If the sleeping machine runs `sleepq web` (see the main README) and the server can reach it, the page
also shows its live status: awake or asleep, what keeps it awake, and the next wake. It keeps the
last answer it got, so while the machine sleeps you still see when it last checked in and when it
planned to wake next.

> **There is no login.** Anyone who can open the page can queue commands that run on the sleepq
> machine as its `run_as` user. Only expose it on a network you trust (a home LAN, a tailnet), or put
> it behind a reverse proxy with authentication. POSTs need an `X-Sleepq: 1` header, so other websites
> can't trigger them from a visitor's browser.

## How it writes

Every change starts from the remote state: fetch, `reset --hard`, apply the change, commit, push.
If the push is rejected because the sleepq machine pushed results in the meantime, it starts over,
up to 4 times. Its clone (`data/repo`) is a disposable cache. It fetches every 60 s, and polls the
live status every 30 s.

## Setup

Standard library only. It runs as a uv project (Python 3.13+) under a hardened systemd unit with
`DynamicUser`.

1. On the server, create a deploy key and add it to the queue repo **with write access**:
   ```sh
   sudo install -d -m 700 /etc/sleepq-remote
   sudo ssh-keygen -t ed25519 -N '' -C sleepq-remote -f /etc/sleepq-remote/deploy_key
   sudo cat /etc/sleepq-remote/deploy_key.pub
   ```
   (`gh repo deploy-key add key.pub --repo you/sleepq-queue --allow-write`, or in the repo's settings.)
   Keep it a deploy key: the service doesn't need access to anything else.
2. Copy `deploy/sleepq-remote.service.example` and fill in the placeholders (paths, repo URL, live
   status URL, port).
3. From this directory: `deploy/install.sh me@server my-sleepq-remote.service`. It copies the app to
   `~/apps/sleepq-remote` on the server, builds the environment with `./sync.sh` (uv, with its own
   Python in `.python/`), and installs, enables and restarts `sleepq-remote.service`. Rerun it after
   every update.

Configuration (the unit's `Environment=` lines):

| Variable | Meaning |
|---|---|
| `SLEEPQ_REMOTE_REPO` | git URL of the queue repo (required) |
| `SLEEPQ_REMOTE_DIR` | where to keep the clone (default `./data/repo`) |
| `SLEEPQ_REMOTE_KEY` | ssh key for git (default: the `deploy_key` credential) |
| `SLEEPQ_REMOTE_BRANCH` | default `main` |
| `SLEEPQ_REMOTE_LIVE` | the machine's `sleepq web` `/api/status` URL (optional) |
| `SLEEPQ_REMOTE_LISTEN` | address:port, default `0.0.0.0:8378` |
