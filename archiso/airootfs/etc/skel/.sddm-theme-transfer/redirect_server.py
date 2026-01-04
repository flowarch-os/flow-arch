#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
import ssl
import threading

HTTP_PORT = 80
HTTPS_PORT = 443
SESSION_FILE = "/tmp/sddm_session.json"

# Portable way to get the actual user's home even under sudo
real_user = os.getenv("SUDO_USER") or os.getenv("USER")
if os.getuid() == 0 and os.getenv("SUDO_USER"):
    home_dir = os.path.expanduser(f"~{os.getenv('SUDO_USER')}")
else:
    home_dir = os.path.expanduser("~")

CERT_FILE = os.path.join(home_dir, ".config/hypr/scripts/certs/server.pem")

class FocusHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        goal = "Focus"
        intention = "Stay on task"
        
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r') as f:
                    data = json.load(f)
                    goal = data.get("goal", goal)
                    intention = data.get("intention", intention)
            except: pass

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Focus Mode Active</title>
            <style>
                body {{
                    background-color: #1e1e2e;
                    color: #cba6f7;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                    text-align: center;
                }}
                h1 {{ font-size: 4em; margin-bottom: 0; color: #f38ba8; }}
                h2 {{ font-size: 2em; color: #fab387; margin-top: 10px; }}
                .card {{
                    background: #313244;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                    max-width: 600px;
                }}
                p {{ font-size: 1.5em; color: #cdd6f4; }}
                .highlight {{ color: #a6e3a1; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🛑 Access Denied</h1>
                <p>This site is blocked to help you achieve your goal.</p>
                <hr style="border: 1px solid #45475a; margin: 20px 0;">
                <p>Current Goal:</p>
                <h2>{goal}</h2>
                <p>Intention: <span class="highlight">{intention}</span></p>
                <br>
                <p style="font-size: 1em; opacity: 0.6;">Stay Hard.</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))

    def log_message(self, format, *args):
        return # Silence logs

def run_http():
    try:
        class ThreadingSimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            pass
        with ThreadingSimpleServer(("0.0.0.0", HTTP_PORT), FocusHandler) as httpd:
            print(f"Serving HTTP focus page on port {HTTP_PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"HTTP Server Error: {e}")

def run_https():
    try:
        class ThreadingSimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            pass
        
        httpd = ThreadingSimpleServer(("0.0.0.0", HTTPS_PORT), FocusHandler)
        
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=CERT_FILE)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        
        print(f"Serving HTTPS focus page on port {HTTPS_PORT}")
        httpd.serve_forever()
    except Exception as e:
        print(f"HTTPS Server Error: {e}")

if __name__ == "__main__":
    if not os.path.exists(CERT_FILE):
        print("Certificate not found. HTTPS will fail.")
    
    t1 = threading.Thread(target=run_http)
    t2 = threading.Thread(target=run_https)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()