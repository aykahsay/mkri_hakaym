"""
Simple Web Server for Mkri Hakaym (ምኽሪ ሓካይም) Website
=====================================================
Serves the website locally on http://localhost:3000
"""
import http.server
import socketserver
import os
from pathlib import Path

PORT = 3000
DIRECTORY = Path(__file__).resolve().parent

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def log_message(self, format, *args):
        # Clean logging
        print(f"[Website] {self.address_string()} - {format % args}")

def run():
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print("=" * 70)
        print("🌐 MKRI HAKAYM (ምኽሪ ሓካይም) WEBSITE SERVER LIVE")
        print("=" * 70)
        print(f"👉 Local URL: http://localhost:{PORT}")
        print(f"📁 Serving directory: {DIRECTORY}")
        print("Press Ctrl+C to stop.")
        print("=" * 70)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == "__main__":
    run()
