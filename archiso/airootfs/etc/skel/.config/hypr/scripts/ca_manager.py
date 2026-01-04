#!/usr/bin/env python3
import os
import sys
import subprocess
import json

CERTS_DIR = os.path.expanduser("~/.config/hypr/scripts/certs")
CA_KEY = os.path.join(CERTS_DIR, "myCA.key")
CA_CERT = os.path.join(CERTS_DIR, "myCA.pem")
SERVER_KEY = os.path.join(CERTS_DIR, "server.key")
SERVER_CERT = os.path.join(CERTS_DIR, "server.pem") # This will be Key + Cert bundle
CONFIG_FILE = os.path.join(CERTS_DIR, "openssl.cnf")

def run_cmd(cmd):
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def setup_ca():
    if not os.path.exists(CERTS_DIR):
        os.makedirs(CERTS_DIR)

    # 1. Generate Root CA Key if missing
    if not os.path.exists(CA_KEY):
        print("Generating Root CA Key...")
        run_cmd(f"openssl genrsa -out {CA_KEY} 2048")

    # 2. Generate Root CA Cert if missing
    if not os.path.exists(CA_CERT):
        print("Generating Root CA Certificate...")
        run_cmd(f"openssl req -x509 -new -nodes -key {CA_KEY} -sha256 -days 3650 -out {CA_CERT} -subj '/C=US/ST=Focus/L=OS/O=HyprFocus Root/CN=HyprFocus CA'")
        print(f"\nIMPORTANT: You must trust this CA: {CA_CERT}\n")

def generate_server_cert(domains):
    setup_ca()
    
    if not domains:
        domains = ["localhost"]

    # 1. Generate Server Key if missing (reusable)
    if not os.path.exists(SERVER_KEY):
        run_cmd(f"openssl genrsa -out {SERVER_KEY} 2048")

    # 2. Create OpenSSL Config for SANs
    print(f"Generating certificate for: {', '.join(domains)}")
    with open(CONFIG_FILE, 'w') as f:
        f.write("[req]\n")
        f.write("default_bits = 2048\n")
        f.write("prompt = no\n")
        f.write("default_md = sha256\n")
        f.write("distinguished_name = dn\n")
        f.write("req_extensions = req_ext\n")
        f.write("\n[dn]\n")
        f.write("C=US\nST=Focus\nL=Land\nO=HyprFocus\nCN=FocusMode\n")
        f.write("\n[req_ext]\n")
        f.write("subjectAltName = @alt_names\n")
        f.write("\n[alt_names]\n")
        for i, domain in enumerate(domains):
            f.write(f"DNS.{i+1} = {domain}\n")
            # Also add www prefix if not present
            if not domain.startswith("www."):
                f.write(f"DNS.{i+1000} = www.{domain}\n")

    # 3. Generate CSR
    csr_path = os.path.join(CERTS_DIR, "server.csr")
    run_cmd(f"openssl req -new -key {SERVER_KEY} -out {csr_path} -config {CONFIG_FILE}")

    # 4. Sign CSR with Root CA
    srv_crt_path = os.path.join(CERTS_DIR, "server.crt")
    run_cmd(f"openssl x509 -req -in {csr_path} -CA {CA_CERT} -CAkey {CA_KEY} -CAcreateserial -out {srv_crt_path} -days 365 -sha256 -extensions req_ext -extfile {CONFIG_FILE}")

    # 5. Bundle Key + Cert for Python Server
    with open(SERVER_CERT, 'w') as f_out:
        with open(SERVER_KEY, 'r') as f_key:
            f_out.write(f_key.read())
        with open(srv_crt_path, 'r') as f_crt:
            f_out.write(f_crt.read())
            
    # Cleanup intermediate files
    try:
        os.remove(csr_path)
        os.remove(srv_crt_path)
        os.remove(CONFIG_FILE)
    except: pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        domains = sys.argv[1].split(',')
        generate_server_cert(domains)
    else:
        setup_ca()
