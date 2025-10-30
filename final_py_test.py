#!/usr/bin/env python3
import sys, os, asyncio, json
from pathlib import Path
sys.path.insert(0, 'src')

async def final_test_py_to_py():
    from tofusoup.rpc.client import KVClient

    test_dir = Path('/tmp/FINAL_PY_PY_TEST')
    test_dir.mkdir(exist_ok=True, parents=True)

    client = KVClient(
        server_path=str(Path.cwd() / 'src' / 'tofusoup' / 'rpc' / 'server.py'),
        tls_mode='disabled'
    )

    client.subprocess_env['KV_STORAGE_DIR'] = str(test_dir)
    client.subprocess_env['SERVER_LANGUAGE'] = 'python'
    client.subprocess_env['CLIENT_LANGUAGE'] = 'python'
    client.subprocess_env['COMBO_ID'] = 'py_to_py_final'

    print('='*60)
    print('FINAL TEST: Python → Python')
    print('='*60)

    await client.start()
    print('✓ Client connected')

    key = 'final_key'
    value = json.dumps({'test': 'python_to_python'}).encode()

    await client.put(key, value)
    print('✓ Put succeeded')

    retrieved = await client.get(key)
    data = json.loads(retrieved.decode())

    print(f'✓ Get succeeded - {len(retrieved)} bytes')
    print(f'  server_handshake present: {"server_handshake" in data}')

    if 'server_handshake' in data:
        sh = data['server_handshake']
        print(f'  server_language: {sh.get("server_language")}')
        print(f'  client_language: {sh.get("client_language")}')

    storage_path = test_dir / f'kv-data-{key}'
    if storage_path.exists():
        with storage_path.open() as f:
            stored = json.load(f)
        print(f'\\n✓ Storage: {storage_path}')
        print(f'  Raw JSON (no handshake): {"server_handshake" not in stored}')

    await client.close()
    print(f'\\n✅ Python → Python WORKS!')

asyncio.run(final_test_py_to_py())
