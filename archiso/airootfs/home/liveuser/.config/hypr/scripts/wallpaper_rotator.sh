#!/bin/bash
# Backgrounded slideshow loop. Picks a random image from $1 every $2 seconds
# and runs `awww img` with a soft fade transition.
#
# Args: <images_dir> <interval_seconds> [transition_type]
#
# Resilience:
#  - if awww-daemon isn't reachable, sleeps 5s and re-checks (don't lock the CPU)
#  - retries `awww img` up to 3 times per cycle if it fails
#  - logs to /tmp/wallpaper_rotator.log so silent failures are visible
#  - writes its PID to /tmp/wallpaper_rotator.pid for the dispatcher

set -u

images_dir="${1:?usage: $0 <images_dir> <interval> [transition]}"
interval="${2:-300}"
transition="${3:-fade}"
LOG=/tmp/wallpaper_rotator.log

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >> "$LOG"; }

if [ ! -d "$images_dir" ]; then
    log "$images_dir not found, exiting"
    exit 1
fi

echo $$ > /tmp/wallpaper_rotator.pid
log "started pid=$$ dir=$images_dir interval=${interval}s transition=$transition"

pick_image() {
    find "$images_dir" -maxdepth 1 -type f \
        \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) \
        -size +30k -printf '%p\n' 2>/dev/null | shuf -n 1
}

set_image() {
    local img="$1" err
    for attempt in 1 2 3; do
        if err=$(awww img "$img" \
                 --transition-type "$transition" \
                 --transition-duration 3 \
                 --transition-fps 60 \
                 --resize crop \
                 --filter Lanczos3 2>&1); then
            return 0
        fi
        log "awww img fail (attempt $attempt) for $(basename "$img"): $err"
        sleep 0.4
    done
    return 1
}

last=""
while true; do
    # Verify daemon is up before each cycle. If down, wait (don't busy-loop).
    if ! awww query >/dev/null 2>&1; then
        log "awww-daemon not reachable, waiting 5s"
        sleep 5
        continue
    fi

    pick=$(pick_image)
    if [ -z "$pick" ]; then
        log "no usable images in $images_dir"
        sleep "$interval"
        continue
    fi
    # Try once for variety if the random pick repeated
    if [ "$pick" = "$last" ]; then
        alt=$(pick_image)
        [ -n "$alt" ] && pick="$alt"
    fi

    if set_image "$pick"; then
        last="$pick"
    fi
    sleep "$interval"
done
