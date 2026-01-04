#!/bin/bash
# setup_focus_ca.sh - Automate CA trust for HyprFocus

CA_SCRIPT="$HOME/.config/hypr/scripts/ca_manager.py"
CA_PEM="$HOME/.config/hypr/scripts/certs/myCA.pem"

# 1. Initialize CA
echo "--- Initializing CA ---"
$CA_SCRIPT

if [ ! -f "$CA_PEM" ]; then
    echo "Error: CA certificate not created. Check ca_manager.py logs."
    exit 1
fi

# 2. Trust in System Store (Arch Linux)
echo "--- Trusting CA in Arch System Store ---"
sudo trust anchor "$CA_PEM"

# 3. Trust in Chrome/Chromium (NSS DB)
echo "--- Attempting to Trust in Chrome/NSS ---"
if command -v certutil >/dev/null 2>&1; then
    # Common NSS database locations on Linux
    NSS_DIRS=("$HOME/.pki/nssdb" $(find $HOME/.config -name "cert9.db" 2>/dev/null | xargs -I {} dirname {}))
    
    for dir in "${NSS_DIRS[@]}"; do
        if [ -d "$dir" ] || [ -f "$dir/cert9.db" ]; then
            # Use 'sql:' prefix for newer cert9.db
            db_prefix=""
            if [ -f "$dir/cert9.db" ]; then db_prefix="sql:"; fi
            
            echo "Importing to: $dir"
            certutil -A -n "HyprFocus CA" -t "C,," -i "$CA_PEM" -d "$db_prefix$dir"
        fi
    done
    echo "Done! Restart Chrome to apply."
else
    echo "certutil (nss package) not found."
    echo "Please install it: sudo pacman -S nss"
    echo "Or manually import $CA_PEM in chrome://settings/certificates (Authorities tab)."
fi
