#!/usr/bin/env bash
# Start a dedicated Firefox profile as a SEPARATE instance with Marionette (automation) on, so an agent can
# drive it, without touching any other Firefox the user has open (their everyday profile).
#   --new-instance  stops Firefox handing the launch to an already-running browser
#   nothing here kills or signals any other process
# Safe to re-run: exits early if the automation instance is already listening.
#
# Usage: firefox-control-launcher.sh "<profile dir>" [marionette port, default 2828]
#   e.g. firefox-control-launcher.sh "$HOME/snap/firefox/common/.mozilla/firefox/xxxxxxxx.Profile 1"
# Tip: copy it to ~/.local/bin/firefox-claude with PROFILE_DIR filled in, and add a .desktop entry if wanted.
set -euo pipefail

PROFILE_DIR="${1:?usage: $0 <profile dir> [port]}"
PORT="${2:-2828}"

port_up() { (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; }

if port_up; then
  echo "Automation Firefox already running (Marionette on :$PORT)."
  exit 0
fi

[ -d "$PROFILE_DIR" ] || { echo "Profile not found: $PROFILE_DIR" >&2; exit 1; }

# The same profile open WITHOUT automation would block a second launch (profile lock). Report only.
for pid in $(pgrep -x firefox -x firefox-bin 2>/dev/null || true); do
  if tr '\0' '\n' < "/proc/$pid/cmdline" 2>/dev/null | grep -qxF -- "$PROFILE_DIR"; then
    echo "That profile is open without automation (pid $pid). Close that window, then re-run." >&2
    exit 1
  fi
done

nohup firefox --new-instance --marionette --remote-debugging-port --profile "$PROFILE_DIR" >/dev/null 2>&1 &

for _ in $(seq 1 30); do
  sleep 1
  if port_up; then
    echo "Automation Firefox started, Marionette on :$PORT."
    exit 0
  fi
done
echo "Firefox launched but Marionette did not come up on :$PORT within 30s." >&2
exit 1
