#!/bin/bash

SHADER_PATH="$HOME/.config/hypr/shaders/blue_light.glsl"
STATE_FILE="$HOME/.config/hypr/blue_light_state"
TEMP_FILE="$HOME/.config/hypr/blue_light_temp"

# Default temp if not set
if [ ! -f "$TEMP_FILE" ]; then
    echo "3500" > "$TEMP_FILE"
fi

# Function to generate GLSL shader
generate_shader() {
    local temp=$1
    # Simple linear mapping: 
    # 6500K -> 1.0 blue
    # 1000K -> 0.4 blue
    
    # Normalize temp (1000 to 6500)
    if [ "$temp" -gt 6500 ]; then temp=6500; fi
    if [ "$temp" -lt 1000 ]; then temp=1000; fi
    
    # Calculate blue component (roughly)
    # y = mx + c
    # 1.0 = m(6500) + c
    # 0.4 = m(1000) + c
    # m = 0.6 / 5500 = 0.000109
    # c = 0.29
    
    blue=$(echo "0.000109 * $temp + 0.2909" | bc)
    
    # If temp is close to 6500, just make it 1.0
    if [ "$temp" -ge 6400 ]; then blue="1.0"; fi

    cat <<EOF > "$SHADER_PATH"
#version 300 es
precision highp float;
in vec2 v_texcoord;
uniform sampler2D tex;
out vec4 fragColor;

void main() {
    vec4 pixColor = texture(tex, v_texcoord);
    pixColor.b *= $blue;
    fragColor = pixColor;
}
EOF
}

command=$1
arg=$2

case $command in
    toggle)
        if grep -q "screen_shader" ~/.config/hypr/hyprland.conf; then
             # It's currently manually set in config? usually we use runtime keyword
             :
        fi
        
        # Check if shader is currently applied via hyprctl
        current_shader=$(hyprctl -j getoption decoration:screen_shader | grep "str" | grep "blue_light.glsl")
        
        if [ -n "$current_shader" ]; then
            # Turn OFF
            hyprctl keyword decoration:screen_shader "[[EMPTY]]"
            echo "OFF" > "$STATE_FILE"
        else
            # Turn ON
            current_temp=$(cat "$TEMP_FILE")
            generate_shader "$current_temp"
            hyprctl keyword decoration:screen_shader "$SHADER_PATH"
            echo "ON" > "$STATE_FILE"
        fi
        ;;
    
    set_temp)
        new_temp=$arg
        echo "$new_temp" > "$TEMP_FILE"
        
        # If currently ON, update live
        state=$(cat "$STATE_FILE" 2>/dev/null)
        if [ "$state" == "ON" ]; then
            generate_shader "$new_temp"
            hyprctl keyword decoration:screen_shader "$SHADER_PATH"
        fi
        ;;
        
    adjust)
        # arg is "up" or "down"
        step=500
        current_temp=$(cat "$TEMP_FILE")
        
        if [ "$arg" == "up" ]; then
            new_temp=$((current_temp + step))
        else
            new_temp=$((current_temp - step))
        fi
        
        # Clamp
        if [ "$new_temp" -gt 6500 ]; then new_temp=6500; fi
        if [ "$new_temp" -lt 1000 ]; then new_temp=1000; fi
        
        echo "$new_temp" > "$TEMP_FILE"
        
        # Update if ON
        state=$(cat "$STATE_FILE" 2>/dev/null)
        if [ "$state" == "ON" ]; then
            generate_shader "$new_temp"
            hyprctl keyword decoration:screen_shader "$SHADER_PATH"
        fi
        
        notify-send -t 1000 "Night Light" "Temperature: ${new_temp}K"
        ;;
        
    status)
        # Used for Waybar icon
        current_shader=$(hyprctl -j getoption decoration:screen_shader | grep "str" | grep "blue_light.glsl")
        if [ -n "$current_shader" ]; then
            echo "󰖔" # Moon
        else
            echo "󰖙" # Sun
        fi
        ;;
esac
