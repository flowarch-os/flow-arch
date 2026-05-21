#!/bin/bash
# Caffeine toggle: when ON, the system will not idle-lock, DPMS-off,
# suspend, hibernate, or react to lid close. Pauses hypridle (SIGSTOP)
# and holds a systemd-inhibit lock on logind power/lid handling.

STATE_FILE="/tmp/caffeine.state"
PID_FILE="/tmp/caffeine_inhibit.pid"
ICON_ON=""
ICON_OFF="󰛊"

is_on() {
    [[ -f "$STATE_FILE" ]]
}

inhibit_alive() {
    [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

start_inhibit() {
    systemd-inhibit \
        --what=sleep:idle:handle-lid-switch:handle-suspend-key:handle-hibernate-key \
        --who="Caffeine" \
        --why="User toggle: stay awake" \
        --mode=block \
        sleep infinity &
    echo $! > "$PID_FILE"
}

stop_inhibit() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        kill "$pid" 2>/dev/null
        rm -f "$PID_FILE"
    fi
    pkill -f 'systemd-inhibit.*Caffeine' 2>/dev/null
}

pause_hypridle() {
    pkill -STOP -x hypridle 2>/dev/null
}

resume_hypridle() {
    pkill -CONT -x hypridle 2>/dev/null
}

on() {
    pause_hypridle
    inhibit_alive || start_inhibit
    touch "$STATE_FILE"
}

off() {
    stop_inhibit
    resume_hypridle
    rm -f "$STATE_FILE"
}

status() {
    if is_on; then
        printf '{"text":"%s","alt":"on","class":"active","tooltip":"Caffeine: ON — system will not sleep, lock, or DPMS off"}\n' "$ICON_ON"
    else
        printf '{"text":"%s","alt":"off","class":"inactive","tooltip":"Caffeine: OFF"}\n' "$ICON_OFF"
    fi
}

case "${1:-status}" in
    on)     on ;;
    off)    off ;;
    toggle) if is_on; then off; else on; fi ;;
    status) status ;;
    *) echo "usage: $0 {on|off|toggle|status}" >&2; exit 2 ;;
esac
