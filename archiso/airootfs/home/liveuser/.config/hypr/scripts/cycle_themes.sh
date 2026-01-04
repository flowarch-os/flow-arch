#!/bin/bash
# cycles through available themes alphabetically

hypr_dir="$HOME/.config/hypr"
themes_dir="$hypr_dir/themes"
scripts_dir="$hypr_dir/scripts"

# get current theme from the symlink target
# target looks like: .../themes/<theme_name>/hypr.conf
current_link=$(readlink "$hypr_dir/theme.conf")
current_theme=$(basename $(dirname "$current_link"))

# get list of themes (subdirectories in themes folder)
# sorted alphabetically
themes=($(ls -d "$themes_dir"/*/ | sort | xargs -n 1 basename))

# find index of current theme
current_index=0
for i in "${!themes[@]}"; do
   if [[ "${themes[$i]}" = "${current_theme}" ]]; then
       current_index=$i
       break
   fi
done

# calculate next theme index
next_index=$(( (current_index + 1) % ${#themes[@]} ))
next_theme=${themes[$next_index]}

# apply the next theme
"$scripts_dir/switch_theme.sh" "$next_theme"