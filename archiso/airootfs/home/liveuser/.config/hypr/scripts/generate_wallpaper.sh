#!/bin/bash
# generates a wallpaper for a given theme using python and rsvg-convert

pattern=$1
bg_color=$2
fg_color=$3
theme_name=$4

if [ -z "$theme_name" ]; then
    echo "usage: $0 <pattern> <bg_hex> <fg_hex> <theme_name>"
    echo "patterns: hex, circles, triangles, waves"
    exit 1
fi

# paths
hypr_dir="$HOME/.config/hypr"
themes_dir="$hypr_dir/themes"
scripts_dir="$hypr_dir/scripts"
theme_dir="$themes_dir/$theme_name"

# ensure theme directory exists
mkdir -p "$theme_dir"

svg_file="$theme_dir/wallpaper.svg"
png_file="$theme_dir/wallpaper.png"

# generate svg using the python script
python3 "$scripts_dir/generate_pattern.py" "$pattern" "$bg_color" "$fg_color" "$svg_file"

# convert svg to png
rsvg-convert -w 1920 -h 1080 "$svg_file" -o "$png_file"

echo "generated wallpaper: $png_file"