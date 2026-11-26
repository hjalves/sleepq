# sleepq

Lets a machine without Wake-on-LAN take jobs on demand while sleeping most of the time.

It wakes on its RTC alarm at the top of every hour (configurable), pulls a task queue from a git repo, runs
whatever is due, pushes the results back, waits a short grace period, then suspends again.
Because the machine can't be reached while asleep, the queue lives in a git remote that is always online.

```
 you (any machine)                git remote                 this machine
 sleepq submit ... ──push──▶  queue/  results/  ◀──pull/push── sleepq daemon
                                                              wake → pull → run → push → suspend
```

## Setup

1. Create an empty **private** repo (GitHub, Gitea, a bare repo on a NAS…) with `queue/` and `results/`.
   Anyone who can push to it can run code on this machine as `run_as`, so keep it private.
2. Give this machine a deploy key with write access and no passphrase (the service has no ssh-agent):
   `ssh-keygen -t ed25519 -N '' -f ~/.ssh/sleepq_deploy`, and pass its path to `sleepq setup` (step 5).
3. Test that RTC wake works on this hardware: `sudo rtcwake -m mem -s 120`. The machine should come back by itself.
4. Build and install the package from this directory: `makepkg -si`.
   Installing alone changes nothing: the sleep hook does nothing until the service is enabled.
5. Point it at your queue (sets `run_as` to you and clones the repo with the deploy key):
   ```bash
   sudo sleepq setup git@github.com:you/sleepq-queue.git ~/.ssh/sleepq_deploy
   ```
6. The shipped config has `dry_run = true`. Run `sudo systemctl enable --now sleepq` and
   `journalctl -u sleepq -f`, and once it looks right set `dry_run = false` and restart the service.

Files: `/usr/bin/sleepq`, `sleepq.service`, `sleepq-web.service`, `/usr/lib/systemd/system-sleep/sleepq`,
`/etc/sleepq/config.toml` (kept across upgrades), and `/var/lib/sleepq/` for the clone and logs.

## Submitting tasks

From any machine with a clone of the queue repo:

```bash
sleepq submit --repo ~/sleepq-queue backup.sh
sleepq submit --repo ~/sleepq-queue -c 'pacman -Syu --noconfirm' --name upgrade --timeout 1h
sleepq submit --repo ~/sleepq-queue render.sh --not-before 2026-11-21T03:00
```

(`export SLEEPQ_REPO=~/sleepq-queue` to skip `--repo`.) Or just commit a bash script into `queue/`
yourself. Headers in the script are optional:

```bash
#!/bin/bash
# sleepq: not-before=2026-11-21T03:00   # local time; the next wake is moved earlier to match
# sleepq: timeout=2h
```

Results land in `results/<task-id>/`: the script, `output.log` (tail, capped by `max_log_bytes`) and
`result.json` (`ok` / `failed` / `timeout` / `interrupted`, exit code, timings). Full logs stay in
`/var/lib/sleepq/state/logs/`.

## Behaviour

- **What gets run:** due tasks in filename order, one at a time, as `run_as` (never root), in a scratch
  dir. Tasks submitted while it's working are picked up before it sleeps.
- **No suspending mid-task:** a logind sleep inhibitor is held while working, so neither sleepq nor
  your desktop's idle timer suspends mid-task (closing a lid still does). It doesn't block *idle*, which
  would keep resetting idle detection.
- **When it won't suspend:**
  - an active, non-idle local session (you're at the desktop)
  - any SSH session (SSH in during the grace period to keep it up)
  - `sudo sleepq hold`, until `sudo sleepq release`
  - a `HOLD` file committed to the repo root (remote switch)

  While held it keeps checking the queue every `awake_poll`.
- **Idle TTY detection:** on some systems, this logind configuration may be needed for idle TTY
  sessions to be detected as idle:
  ```bash
  sudo mkdir -p /etc/systemd/logind.conf.d
  sudo tee /etc/systemd/logind.conf.d/idle.conf <<'EOF'
  [Login]
  IdleAction=ignore
  IdleActionSec=5min
  EOF
  ```
- **Any suspend sets the alarm:** the sleep hook arms the RTC before *every* suspend, including lid,
  menu and idle suspends, so the machine always comes back for the next check.
- **Power loss / crash:** a task that was running is retried; after `max_attempts` interruptions it's
  marked `interrupted` instead of looping forever. Set "Restore on AC power loss" in the BIOS so the
  machine boots again after an outage.
- **Wake times:** with `align_wakes = true` (the default) it wakes on the clock, at multiples of
  `wake_interval` from local midnight: with `1h`, every hour at :00. So you know the next wake without
  asking the machine. A slot less than 5 minutes away is skipped. Intervals that don't divide 24h
  restart at midnight, for example 7h wakes at 00:00, 07:00, 14:00 and 21:00. A task's `not-before`
  moves the wake earlier, to that time. A task can wait up to one `wake_interval` before it starts.
  The alarm overwrites any other RTC alarm.

`sudo sleepq status` shows pending tasks, the current alarm and what's keeping the machine awake.

## Web page

`sudo systemctl enable --now sleepq-web` serves a status page on port 8377 (`web_listen` in the config):
daemon state, alarm and next wake, what keeps the machine awake, pending tasks, recent results with
their output, the daemon log, and **Hold** / **Release** buttons (the same as `sleepq hold` / `release`).
It has no login, so anyone who can reach the port can see the queue and keep the machine awake.
It's only reachable while the machine is awake; to keep it up remotely, commit a `HOLD` file instead.

## Tray icon

`sleepq-tray` puts a crescent moon in the desktop's system tray. It needs the optional
`python-pystray` package and polls the web API (`--url`, default `http://localhost:8377`), so
`sleepq-web.service` must be running. It is started by `/etc/xdg/autostart/sleepq-tray.desktop`.
On Wayland it registers as a StatusNotifierItem (the Xfce panel's Status Tray plugin shows it).

Colour: green = will suspend when idle, blue = kept awake by sessions, amber = on hold,
red = `sleepq.service` not active, grey = web API unreachable. A red dot means the last task failed.
The menu shows the next wake, why it is staying awake, pending tasks and the last result, plus a
**Hold** toggle (the same local hold as `sleepq hold`/`release`) and a link to the web page.

## Controlling it from another machine

[`remote/`](remote/) is a separate web app for an always-on server. It commits `HOLD`, queues and
cancels commands, and shows results through the queue repo, so it works while this machine sleeps.
It isn't part of the package; see [remote/README.md](remote/README.md).

## Uninstall

```bash
sudo pacman -R sleepq          # also disables the services
sudo rm -r /var/lib/sleepq      # queue clone and logs, if you don't want them
```
