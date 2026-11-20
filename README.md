# sleepq

Lets a machine without Wake-on-LAN take jobs on demand while sleeping most of the time.

It wakes on its RTC alarm every hour (configurable), pulls a task queue from a git repo, runs
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

Files: `/usr/bin/sleepq`, `sleepq.service`, `/usr/lib/systemd/system-sleep/sleepq`,
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
- **Any suspend sets the alarm:** the sleep hook arms the RTC before *every* suspend, including lid,
  menu and idle suspends, so the machine always comes back for the next check.
- **Power loss / crash:** a task that was running is retried; after `max_attempts` interruptions it's
  marked `interrupted` instead of looping forever. Set "Restore on AC power loss" in the BIOS so the
  machine boots again after an outage.
- **Wake times:** a task can wait up to one `wake_interval` before it starts. The alarm overwrites
  any other RTC alarm.

`sudo sleepq status` shows pending tasks, the current alarm and what's keeping the machine awake.

## Uninstall

```bash
sudo pacman -R sleepq          # also disables the service
sudo rm -r /var/lib/sleepq      # queue clone and logs, if you don't want them
```
