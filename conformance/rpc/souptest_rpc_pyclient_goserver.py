import pytest
import asyncio
from pathlib import Path
import os

from tofusoup.rpc.client import KVClient

@pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
@pytest.mark.asyncio
async def test_pyclient_goserver_put_get_string(go_harness_executable: Path):
    """
    Tests Put/Get between Python KVClient and the unified Go KVServer.
    """
    if not go_harness_executable.exists():
        pytest.skip("Go harness executable not found.")

    # The KVClient will start the `soup-go rpc server-start` command as a subprocess.
    client = KVClient(server_path=str(go_harness_executable))
    
    try:
        await client.start()

        key = "py-to-go-key"
        value = b"Hello from Python client to Go server!"
        
        await client.put(key, value)
        retrieved = await client.get(key)
        
        assert retrieved is not None
        assert retrieved == value

    finally:
        if client:
            await client.close()

# 🍲🥄🧪🪄
