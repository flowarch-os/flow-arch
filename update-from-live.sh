#!/usr/bin/env bash
# Sync the live running system into archiso/airootfs/ in this repo.
#
# Strategy: discovery-based for user dotfiles, whitelist for /etc.
#
#   USER CONFIG (~/.config and ~/dotfiles)
#     - For every dir already tracked under etc/skel/.config/, rsync from
#       $HOME/.config/<same-name>/. New files/subdirs are picked up
#       automatically. Personal app dirs not in the repo (chromium, discord,
#       vscode, etc.) are skipped because they have no counterpart.
#     - For every top-level file already tracked under etc/skel/.config/,
#       copy from $HOME/.config/.
#     - For every dotfile already tracked directly under etc/skel/ (e.g.
#       .Xresources), copy from $HOME/. .bashrc is filtered to drop personal
#       PATH lines (npm-global, openclaw, wakatime).
#
#   SYMLINKS
#     - Absolute symlinks copied from live that point into ~/.config/hypr/
#       are rewritten into relative paths within skel so they resolve inside
#       the ISO chroot. This handles waybar/style.css, hypr/theme.conf,
#       wofi/style.css, and anything else following the same pattern.
#
#   /ETC
#     - Whitelist only. Files the user has deliberately customised live and
#       wants reflected in the ISO. Everything else under /etc/ is
#       package-managed or archiso-specific and must NOT be auto-synced.
#     - To track a new file, add its path (relative to /etc/) to ETC_TRACK.
#
#   MIRROR
#     - After all updates, etc/skel/.config/ is rsync'd byte-identically to
#       home/liveuser/.config/, and the same for .bashrc / .Xresources.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
SKEL="$REPO_ROOT/archiso/airootfs/etc/skel"
LIVEUSER="$REPO_ROOT/archiso/airootfs/home/liveuser"
ETC_REPO="$REPO_ROOT/archiso/airootfs/etc"

# rsync excludes use bare filenames so they match at any depth inside the
# per-dir sync source. All names listed are unique enough across tracked dirs
# that name-collision risk is acceptable.
EXCLUDES=(
  --exclude='__pycache__'
  --exclude='*.pyc'
  --exclude='*.swp'
  --exclude='.DS_Store'
  # hypr runtime state (machine-local)
  --exclude='blue_light_state'
  --exclude='blue_light_temp'
  --exclude='wlsunset_temp'
  # hypr personal data (goals, calendar, blacklists, tasks)
  --exclude='settings.json'
  --exclude='settings.json.v*.bak'
  # gtk personal bookmarks
  --exclude='bookmarks'
  # systemd user units tied to local tooling
  --exclude='openclaw-gateway.service'
  --exclude='default.target.wants'
)

# Whitelist of /etc files synced from live. Add a line here when you start
# tracking a new file. Paths are relative to /etc/.
ETC_TRACK=(
  default/grub
)

log() { printf '  %s\n' "$*"; }
section() { printf '\n==> %s\n' "$*"; }

# ------------------------------------------------------------------
# 1. Sync each tracked .config subdir
# ------------------------------------------------------------------
section "Syncing user .config dirs (skel)"
for dir in "$SKEL/.config/"*/; do
  name="$(basename "$dir")"
  src="$HOME/.config/$name"
  [ -d "$src" ] || { log "skip: $name (no live dir)"; continue; }
  # --delete-excluded removes any pre-existing excluded files from the
  # destination (self-heals if a personal/state file leaked in previously).
  # We do NOT use plain --delete because a file present in repo but
  # absent on live should be kept (e.g. .bashrc edits) unless the user
  # explicitly git-rms it.
  rsync -a --delete-excluded "${EXCLUDES[@]}" "$src/" "$dir"
  log "synced: .config/$name"
done

# ------------------------------------------------------------------
# 2. Sync each tracked top-level file in .config (e.g. mimeapps.list)
# ------------------------------------------------------------------
section "Syncing user .config top-level files"
for f in "$SKEL/.config/"*; do
  [ -f "$f" ] || continue
  name="$(basename "$f")"
  src="$HOME/.config/$name"
  [ -f "$src" ] || { log "skip: $name (no live file)"; continue; }
  cp -p "$src" "$f"
  log "synced: .config/$name"
done

# ------------------------------------------------------------------
# 3. Rewrite absolute symlinks pointing into ~/.config/hypr/ as relative
#    paths within skel. Generalises waybar/style.css, hypr/theme.conf,
#    wofi/style.css, and any future file following the active-theme pattern.
# ------------------------------------------------------------------
section "Re-rooting absolute symlinks into hypr/"
while IFS= read -r link; do
  target="$(readlink "$link")"
  case "$target" in
    "$HOME/.config/hypr/"*|"/home/"*"/.config/hypr/"*)
      # Take the path tail starting at hypr/
      tail="${target#*/.config/hypr/}"
      link_dir="$(dirname "$link")"
      new_target="$(realpath -m --relative-to="$link_dir" "$SKEL/.config/hypr/$tail")"
      ln -sfn "$new_target" "$link"
      log "$(realpath --relative-to="$SKEL/.config" "$link") -> $new_target"
      ;;
  esac
done < <(find "$SKEL/.config" -type l)

# ------------------------------------------------------------------
# 4. Sync dotfiles directly under $HOME tracked in skel. .bashrc filtered.
# ------------------------------------------------------------------
section "Syncing \$HOME dotfiles tracked in skel"
for f in "$SKEL"/.*; do
  name="$(basename "$f")"
  case "$name" in
    .|..|.config|.sddm-config-transfer|.sddm-theme-transfer) continue;;
  esac
  src="$HOME/$name"
  [ -f "$src" ] || { log "skip: $name (no live file)"; continue; }
  if [ "$name" = ".bashrc" ]; then
    grep -vE '(\.npm-global|openclaw|wakatime)' "$src" > "$f"
    log "synced: .bashrc (personal PATH lines stripped)"
  else
    cp -p "$src" "$f"
    log "synced: $name"
  fi
done

# ------------------------------------------------------------------
# 5. Sync /etc files from the whitelist
# ------------------------------------------------------------------
section "Syncing tracked /etc files (whitelist)"
for rel in "${ETC_TRACK[@]}"; do
  live="/etc/$rel"
  repo="$ETC_REPO/$rel"
  if [ ! -f "$live" ]; then
    log "skip: /etc/$rel (not on live system)"; continue
  fi
  if [ ! -f "$repo" ]; then
    log "warn: /etc/$rel — repo path missing, copying anyway"
    mkdir -p "$(dirname "$repo")"
  fi
  if cmp -s "$live" "$repo"; then
    log "unchanged: /etc/$rel"
  else
    cp -p "$live" "$repo"
    log "synced: /etc/$rel"
  fi
done

# ------------------------------------------------------------------
# 6. Mirror skel → liveuser
# ------------------------------------------------------------------
section "Mirroring skel -> liveuser"
rsync -a --delete "$SKEL/.config/" "$LIVEUSER/.config/"
[ -f "$SKEL/.bashrc" ] && [ -e "$LIVEUSER/.bashrc" ] && cp -p "$SKEL/.bashrc" "$LIVEUSER/.bashrc"
# Verify the mirror
if diff -rq "$SKEL/.config" "$LIVEUSER/.config" >/dev/null 2>&1; then
  log "skel/.config == liveuser/.config"
else
  log "WARNING: mirror diverged — inspect manually"
  diff -rq "$SKEL/.config" "$LIVEUSER/.config" | head -10
fi

# ------------------------------------------------------------------
# 7. Summary
# ------------------------------------------------------------------
section "git status"
cd "$REPO_ROOT"
git status --short | head -60
total=$(git status --short | wc -l)
printf '\n%d files changed in working tree.\n' "$total"
printf 'Review with: git diff --stat\n'
printf "To track a new /etc file, add it to ETC_TRACK in this script.\n"
