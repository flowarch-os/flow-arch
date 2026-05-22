#!/bin/bash
# Wallpaper dispatcher. Reads the active theme's wallpaper.conf manifest and
# starts the appropriate wallpaper engine (awww slideshow / mpvpaper video /
# hyprpaper static), tearing down whatever was previously running.
#
# Usage: wallpaper_engine.sh <theme_name>
#
# Manifest format (themes/<name>/wallpaper.conf):
#   type=slideshow|video|static
#   engine=swww|mpvpaper|hyprpaper        # swww name kept for compat; resolves to awww
#   images_dir=images/        # slideshow
#   interval=300              # slideshow
#   transition=fade           # slideshow
#   video=loop.mp4            # video
#   videos_dir=videos/        # video (optional, picks random from pool)
#
# Logs go to /tmp/wallpaper_engine.log for debugging silent failures.

set -u

theme="${1:?usage: $0 <theme>}"
hypr_dir="$HOME/.config/hypr"
theme_dir="$hypr_dir/themes/$theme"
manifest="$theme_dir/wallpaper.conf"
LOG=/tmp/wallpaper_engine.log

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOG" >&2; }

log "switch → $theme"

if [ ! -d "$theme_dir" ]; then
    log "error: theme $theme not found"
    exit 1
fi

# defaults if no manifest exists (legacy themes)
type="static"
engine="hyprpaper"
images_dir="images/"
interval="300"
transition="fade"
video="loop.mp4"
videos_dir=""

if [ -f "$manifest" ]; then
    # shellcheck disable=SC1090
    source "$manifest"
fi

# Resolve relative paths against theme_dir
case "$images_dir" in /*) ;; *) images_dir="$theme_dir/${images_dir%/}" ;; esac
case "$video"      in /*) ;; *) video="$theme_dir/$video" ;; esac
[ -n "$videos_dir" ] && case "$videos_dir" in /*) ;; *) videos_dir="$theme_dir/${videos_dir%/}" ;; esac

# ---- Tear down anything currently running ----
# Belt-and-suspenders: kill via pidfile AND by script name pattern.
if [ -f /tmp/wallpaper_rotator.pid ]; then
    kill "$(cat /tmp/wallpaper_rotator.pid)" 2>/dev/null || true
fi
# Catch any stray rotators (e.g. orphaned from previous session)
pkill -f 'wallpaper_rotator\.sh' 2>/dev/null || true
rm -f /tmp/wallpaper_rotator.pid

# mpvpaper ignores SIGTERM — needs SIGKILL. The others stop cleanly.
pkill -KILL -x mpvpaper 2>/dev/null || true
pkill -x hyprpaper 2>/dev/null || true
pkill -x awww-daemon 2>/dev/null || true
pkill -x swww-daemon 2>/dev/null || true
sleep 0.4   # let daemons unbind sockets fully

# ---- Helpers ----
has() { command -v "$1" >/dev/null 2>&1; }

# Wait up to N*0.15s for awww-daemon to accept queries
wait_for_awww() {
    local tries=${1:-50}
    for _ in $(seq 1 "$tries"); do
        awww query >/dev/null 2>&1 && return 0
        sleep 0.15
    done
    return 1
}

# Set wallpaper with retry; logs success/failure
set_awww_image() {
    local img="$1" trans="${2:-fade}"
    local err
    for attempt in 1 2 3; do
        if err=$(awww img "$img" \
                 --transition-type "$trans" \
                 --transition-duration 2 \
                 --transition-fps 60 \
                 --resize crop \
                 --filter Lanczos3 2>&1); then
            log "awww img ok (attempt $attempt): $(basename "$img")"
            return 0
        fi
        log "awww img fail (attempt $attempt): $err"
        sleep 0.3
    done
    return 1
}

fallback_static() {
    local img="$theme_dir/wallpaper.png"
    [ -f "$img" ] || { log "no fallback wallpaper.png in $theme_dir"; return 1; }
    if has hyprpaper; then
        printf 'preload = %s\nwallpaper = ,%s\n' "$img" "$img" > "$hypr_dir/hyprpaper.conf"
        setsid hyprpaper >/dev/null 2>&1 < /dev/null &
        disown
        log "static fallback ($(basename "$img")) via hyprpaper"
    else
        log "no wallpaper daemon available"
        return 1
    fi
}

start_swww_slideshow() {
    if ! has awww; then
        log "awww/swww not installed, falling back to static"
        fallback_static
        return
    fi
    if [ ! -d "$images_dir" ] || [ -z "$(find "$images_dir" -maxdepth 1 -type f \
         \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) -size +30k -print -quit 2>/dev/null)" ]; then
        log "no images in $images_dir, falling back to static"
        fallback_static
        return
    fi

    setsid awww-daemon >/dev/null 2>&1 < /dev/null &
    disown

    if ! wait_for_awww 50; then
        log "awww-daemon never became reachable (7.5s wait), falling back to static"
        fallback_static
        return
    fi

    # Set an initial image immediately (with retry)
    local first
    first=$(find "$images_dir" -maxdepth 1 -type f \
            \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) \
            -size +30k -printf '%p\n' 2>/dev/null | shuf -n 1)
    if [ -n "$first" ]; then
        if ! set_awww_image "$first" fade; then
            log "initial awww img failed; static fallback as last resort"
            fallback_static
            return
        fi
    fi

    # Background rotator
    setsid "$hypr_dir/scripts/wallpaper_rotator.sh" "$images_dir" "$interval" "$transition" \
        >/dev/null 2>&1 < /dev/null &
    disown
    log "awww slideshow ($images_dir, every ${interval}s, $transition)"
}

start_mpvpaper_video() {
    if ! has mpvpaper; then
        log "mpvpaper not installed, falling back to slideshow/static"
        start_swww_slideshow
        return
    fi
    local target="$video"
    if [ -n "$videos_dir" ] && [ -d "$videos_dir" ]; then
        local pool
        pool=$(find "$videos_dir" -maxdepth 1 -type f \
               \( -iname '*.mp4' -o -iname '*.webm' -o -iname '*.mkv' \) \
               -size +500k -printf '%p\n' 2>/dev/null)
        if [ -n "$pool" ]; then
            if [ -f "$video" ] && [ $((RANDOM % 2)) -eq 0 ]; then
                target="$video"
            else
                target=$(printf '%s\n' "$pool" | shuf -n 1)
            fi
        fi
    fi
    if [ ! -f "$target" ]; then
        log "no video at $target, falling back"
        start_swww_slideshow
        return
    fi
    setsid mpvpaper -o "loop=inf no-audio hwdec=auto vo=gpu video-sync=audio" \
        ALL "$target" >/dev/null 2>&1 < /dev/null &
    disown
    log "mpvpaper looping $(basename "$target")"
}

case "$type" in
    slideshow) start_swww_slideshow ;;
    video)     start_mpvpaper_video ;;
    static|*)  fallback_static ;;
esac
