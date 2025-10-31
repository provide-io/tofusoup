#!/usr/bin/env python3
"""Test what certificate type the server generates, including stderr output."""

import subprocess
import os
from pathlib import Path

# Run the server with PLUGIN_TLS_KEY_TYPE=rsa
env = os.environ.copy()
env["PLUGIN_TLS_KEY_TYPE"] = "rsa"
env["PLUGIN_AUTO_MTLS"] = "true"
env["BASIC_PLUGIN"] = "hello"
env["PLUGIN_MAGIC_COOKIE_KEY"] = "BASIC_PLUGIN"

soup_path = Path(__file__).parent / ".venv" / "bin" / "soup"

print("🚀 Starting server subprocess with PLUGIN_TLS_KEY_TYPE=rsa...")
print(f"   PLUGIN_TLS_KEY_TYPE={env['PLUGIN_TLS_KEY_TYPE']}")
print()

proc = subprocess.Popen(
    [str(soup_path), "rpc", "kv", "server", "--tls-mode", "auto", "--tls-key-type", "rsa"],
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)

# Give it a moment to start and log
import time
time.sleep(1)

# Kill it
proc.kill()
try:
    stdout, stderr = proc.communicate(timeout=1)
except:
    stdout = proc.stdout.read() if proc.stdout else ""
    stderr = proc.stderr.read() if proc.stderr else ""

print("=== STDOUT (handshake) ===")
print(stdout[:200])
print()
print("=== STDERR (logs) ===")
print(stderr)
