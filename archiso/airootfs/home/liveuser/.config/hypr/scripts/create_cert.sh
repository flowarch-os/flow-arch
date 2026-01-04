#!/bin/bash
CERT_DIR="$HOME/.config/hypr/scripts/certs"
mkdir -p "$CERT_DIR"

if [ ! -f "$CERT_DIR/server.pem" ]; then
    echo "Generating self-signed certificate..."
    openssl req -new -x509 -keyout "$CERT_DIR/server.pem" \
        -out "$CERT_DIR/server.pem" -days 365 -nodes \
        -subj "/C=US/ST=Focus/L=Land/O=HyprFocus/CN=focus.local"
    chmod 600 "$CERT_DIR/server.pem"
    echo "Certificate created at $CERT_DIR/server.pem"
else
    echo "Certificate already exists."
fi
