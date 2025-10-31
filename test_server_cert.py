#!/usr/bin/env python3
"""Test what certificate type the server actually generates."""

import subprocess
import sys
import os
import time
import base64
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
print(f"   PLUGIN_AUTO_MTLS={env['PLUGIN_AUTO_MTLS']}")
print()

proc = subprocess.Popen(
    [str(soup_path), "rpc", "kv", "server", "--tls-mode", "auto", "--tls-key-type", "rsa"],
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)

# Read the handshake (first line on stdout)
try:
    stdout_line = proc.stdout.readline()
    print(f"📋 Handshake received (length: {len(stdout_line)} chars)")

    # Parse the handshake: 1|1|protocol|address|grpc|CERT_BASE64
    parts = stdout_line.strip().split("|")
    print(f"   Parts count: {len(parts)}")
    if len(parts) >= 6:
        cert_b64 = parts[5]
        print(f"   Cert base64 length: {len(cert_b64)}")
        print(f"   Cert base64 (last 20 chars): ...{cert_b64[-20:]}")

        # Try to decode with lenient padding
        missing_padding = len(cert_b64) % 4
        if missing_padding:
            cert_b64 += '=' * (4 - missing_padding)

        cert_der = base64.b64decode(cert_b64)

        # Parse the certificate to see what type it is
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend

        cert = x509.load_der_x509_certificate(cert_der, default_backend())
        pub_key = cert.public_key()

        from cryptography.hazmat.primitives.asymmetric import rsa, ec

        if isinstance(pub_key, rsa.RSAPublicKey):
            print(f"✅ Server generated RSA certificate (key size: {pub_key.key_size})")
            print("   ✅ CORRECT - Server respected PLUGIN_TLS_KEY_TYPE=rsa")
        elif isinstance(pub_key, ec.EllipticCurvePublicKey):
            curve_name = pub_key.curve.name
            print(f"❌ Server generated ECDSA certificate (curve: {curve_name})")
            print("   ❌ BUG - Server ignored PLUGIN_TLS_KEY_TYPE=rsa and used ECDSA instead!")
            print(f"   ❌ This proves the server doesn't read PLUGIN_TLS_KEY_TYPE environment variable")
        else:
            print(f"❓ Unknown key type: {type(pub_key)}")
    else:
        print(f"❌ Invalid handshake format: {parts}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    proc.kill()
    try:
        proc.wait(timeout=1)
    except:
        pass
