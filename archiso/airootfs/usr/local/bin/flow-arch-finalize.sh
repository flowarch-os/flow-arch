#!/bin/bash
# Flow Arch Finalization Script
# This runs inside the target system (chroot)

echo "Finalizing Flow Arch installation..."

# Find the new user home (assuming uid 1000)
NEW_USER=$(id -nu 1000)
if [ -n "$NEW_USER" ]; then
    USER_HOME="/home/$NEW_USER"
    
    # 1. Restore Smuggled Scripts and Themes
    mkdir -p /usr/share/sddm/themes/simple
    if [ -d "$USER_HOME/.sddm-theme-transfer" ]; then
        # Copy everything to /usr/local/bin and /usr/share
        cp -r "$USER_HOME/.sddm-theme-transfer/." /usr/share/sddm/themes/simple/
        cp "$USER_HOME/.sddm-theme-transfer/hosts_manager.py" /usr/local/bin/
        cp "$USER_HOME/.sddm-theme-transfer/redirect_server.py" /usr/local/bin/
        cp "$USER_HOME/.sddm-theme-transfer/ca_manager.py" /usr/local/bin/
        
        chmod +x /usr/local/bin/hosts_manager.py /usr/local/bin/redirect_server.py /usr/local/bin/ca_manager.py
    fi
fi

# 2. Run CA Manager to generate certificates
if [ -f /usr/local/bin/ca_manager.py ]; then
    echo "Generating Root CA..."
    /usr/bin/python3 /usr/local/bin/ca_manager.py
    echo "Generating default Server Certificate..."
    /usr/bin/python3 /usr/local/bin/ca_manager.py localhost
fi

# 3. Root CA Trust
mkdir -p /etc/ca-certificates/trust-source/anchors
# Certs were generated in /root/.config/hypr/scripts/certs because we ran as root in chroot
GEN_CERT_DIR="/root/.config/hypr/scripts/certs"

if [ -f "$GEN_CERT_DIR/myCA.pem" ]; then
    cp "$GEN_CERT_DIR/myCA.pem" /etc/ca-certificates/trust-source/anchors/FlowArchCA.crt
    trust extract-compat
    
    # Also copy the generated certs to the user's directory so the server can use them
    if [ -n "$USER_HOME" ]; then
        mkdir -p "$USER_HOME/.config/hypr/scripts/certs"
        cp -r "$GEN_CERT_DIR/." "$USER_HOME/.config/hypr/scripts/certs/"
        chown -R 1000:1000 "$USER_HOME/.config/hypr"
    fi
fi

# 4. Firefox Policies
mkdir -p /usr/lib/firefox/distribution
if [ -f /etc/ca-certificates/trust-source/anchors/FlowArchCA.crt ]; then
cat <<EOF > /usr/lib/firefox/distribution/policies.json
{
  "policies": {
    "Certificates": {
      "Install": ["/etc/ca-certificates/trust-source/anchors/FlowArchCA.crt"]
    }
  }
}
EOF
fi

# 5. SDDM Config Generation
mkdir -p /etc/sddm.conf.d
cat <<EOF > /etc/sddm.conf.d/flow-arch.conf
[Theme]
Current=simple

[Users]
MaximumUid=60000
MinimumUid=1000
RememberLastSession=true
RememberLastUser=true

[Autologin]
Relogin=false
EOF

# 6. SDDM State (Pre-fill User)
if [ -n "$NEW_USER" ]; then
    mkdir -p /var/lib/sddm
    cat <<EOF > /var/lib/sddm/state.conf
[Last]
User=$NEW_USER
Session=/usr/share/wayland-sessions/hyprland.desktop
EOF
fi

# 7. Sudoers
mkdir -p /etc/sudoers.d
echo "ALL ALL=(root) NOPASSWD: /usr/local/bin/hosts_manager.py, /usr/local/bin/redirect_server.py, /usr/local/bin/ca_manager.py" > /etc/sudoers.d/flow-arch-hosts
chmod 440 /etc/sudoers.d/flow-arch-hosts

# 8. Services
systemctl enable sddm
systemctl enable NetworkManager
systemctl enable bluetooth
systemctl enable power-profiles-daemon
systemctl start power-profiles-daemon || true
systemctl set-default graphical.target

# 9. Cleanup Transfer folders
if [ -n "$USER_HOME" ]; then
    rm -rf "$USER_HOME/.sddm-theme-transfer"
    rm -rf "$USER_HOME/.sddm-config-transfer"
fi

echo "Flow Arch finalization complete."
