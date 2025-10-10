#
# tofusoup/rpc/client.py
#
import asyncio
import logging
import os
import time

import grpc
from provide.foundation import logger

from tofusoup.config.defaults import (
    CONNECTION_TIMEOUT,
    ENV_GRPC_DEFAULT_CLIENT_CERTIFICATE_PATH,
    ENV_GRPC_DEFAULT_CLIENT_PRIVATE_KEY_PATH,
    ENV_GRPC_DEFAULT_SSL_ROOTS_FILE_PATH,
    REQUEST_TIMEOUT,
)

# Optional RPC integration
try:
    from pyvider.rpcplugin.client import RPCPluginClient
    from pyvider.rpcplugin.config import rpcplugin_config

    HAS_RPC = True
except ImportError:
    HAS_RPC = False
    RPCPluginClient = None
    rpcplugin_config = {}
from tofusoup.harness.proto.kv import KVProtocol, kv_pb2, kv_pb2_grpc

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s.%(msecs)03d [%(levelname)-7s] %(name)s: 🐍 C> %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class KVClient:
    """Client for KV plugin server with mTLS and explicit config capabilities."""

    def __init__(
        self,
        server_path: str,
        tls_mode: str = "disabled",
        tls_key_type: str = "ec",
        tls_curve: str = "P-256",
        cert_file: str | None = None,
        key_file: str | None = None,
    ) -> None:
        self.tls_mode = tls_mode
        self.tls_key_type = tls_key_type
        self.tls_curve = tls_curve
        self.server_path = server_path
        self.cert_file = cert_file
        self.key_file = key_file
        self._client: RPCPluginClient | None = None
        self._stub: kv_pb2_grpc.KVStub | None = None
        self.is_started = False
        self.connection_timeout = CONNECTION_TIMEOUT

        # Map tls_mode to enable_mtls for internal use
        self.enable_mtls = self.tls_mode != "disabled"

        go_server_expected_cookie_key = "BASIC_PLUGIN"
        go_server_expected_cookie_value = "hello"
        go_server_protocol_version = "1"

        self.subprocess_env = {
            "PLUGIN_MAGIC_COOKIE_KEY": go_server_expected_cookie_key,
            go_server_expected_cookie_key: go_server_expected_cookie_value,
            "PLUGIN_PROTOCOL_VERSIONS": go_server_protocol_version,
            "LOG_LEVEL": os.getenv("LOG_LEVEL", logger.level.name if hasattr(logger, "level") else "INFO"),  # type: ignore
            "PYTHONUNBUFFERED": "1",
            "GODEBUG": os.getenv("GODEBUG", "asyncpreemptoff=1,panicasync=1"),
            "PLUGIN_AUTO_MTLS": "true" if self.enable_mtls else "false",
        }

        # Map TLS key type to legacy environment variables if needed
        if self.tls_key_type == "ec":
            self.subprocess_env["PYVIDER_CLIENT_CERT_ALGO"] = "ecdsa"
            self.subprocess_env["PYVIDER_CLIENT_CERT_CURVE"] = self.tls_curve
        elif self.tls_key_type == "rsa":
            self.subprocess_env["PYVIDER_CLIENT_CERT_ALGO"] = "rsa"

        # Magic cookie configuration is set via subprocess_env dict above
        # No need to modify rpcplugin_config directly as it reads from environment
        logger.info(f"[KVClient.__init__] self.subprocess_env for plugin: {self.subprocess_env}")

    async def start(self) -> None:
        start_time = time.time()
        self.is_started = False
        try:
            # TLS/mTLS configuration is passed via subprocess_env and client constructor config
            # No need to modify rpcplugin_config directly

            logger.debug(f"KVClient attempting to start server: {self.server_path}")

            if not os.path.exists(self.server_path):
                raise FileNotFoundError(f"Server executable not found: {self.server_path}")
            if not os.access(self.server_path, os.X_OK):
                raise PermissionError(f"Server executable not executable: {self.server_path}")

            server_command = [self.server_path]
            # Prepare effective_env early as it might be modified
            effective_env = (
                os.environ.copy()
            )  # Start with current env, which includes what tests monkeypatched
            effective_env.update(
                self.subprocess_env
            )  # Merge KVClient's base env for plugin (e.g., GODEBUG, PYTHONUNBUFFERED)
            # Note: self.subprocess_env contains PLUGIN_AUTO_MTLS which pyvider-rpcplugin client might read via rpcplugin_config
            # This is separate from how the server is told to configure its TLS.

            # Add TLS configuration arguments
            # Check if binary name suggests it needs subcommands
            binary_name = os.path.basename(self.server_path)
            if binary_name in ["soup-go", "go-harness", "soup"]:
                # New harnesses (both Go and Python) expect rpc server-start subcommand
                server_command.extend(["rpc", "server-start"])
            # For existing go-rpc binary or old-style binaries, just pass flags directly

            server_command.extend(["--tls-mode", self.tls_mode])

            if self.tls_mode == "auto":
                # Only Python server (soup) supports --tls-key-type flag
                # Go server determines key type from env vars or uses defaults
                if binary_name == "soup":
                    server_command.extend(["--tls-key-type", self.tls_key_type])
                logger.info(f"KVClient: Auto TLS enabled with key type: {self.tls_key_type}")
            elif self.tls_mode == "manual":
                if self.cert_file and self.key_file:
                    server_command.extend(["--cert-file", self.cert_file])
                    server_command.extend(["--key-file", self.key_file])
                    logger.info(
                        f"KVClient: Manual TLS enabled with cert: {self.cert_file}, key: {self.key_file}"
                    )
                else:
                    # Fallback: try to get paths from environment variables
                    server_cert_path = os.getenv("PLUGIN_SERVER_CERT")
                    server_key_path = os.getenv("PLUGIN_SERVER_KEY")
                    if server_cert_path and server_key_path:
                        server_command.extend(["--cert-file", server_cert_path])
                        server_command.extend(["--key-file", server_key_path])
                        logger.info(
                            f"KVClient: Manual TLS enabled using env vars - cert: {server_cert_path}, key: {server_key_path}"
                        )
                    else:
                        logger.error("KVClient: Manual TLS mode requires cert-file and key-file")
                        raise ValueError(
                            "Manual TLS mode requires cert_file and key_file parameters or PLUGIN_SERVER_CERT/PLUGIN_SERVER_KEY environment variables"
                        )
            else:  # disabled
                logger.info("KVClient: TLS disabled - running in insecure mode")

            logger.info(f"Effective server command for plugin: {' '.join(server_command)}")

            # Ensure PLUGIN_AUTO_MTLS in effective_env (for pyvider-rpcplugin client itself) matches KVClient's intent
            effective_env["PLUGIN_AUTO_MTLS"] = "true" if self.enable_mtls else "false"

            # Set up magic cookies in the server's effective_env.
            go_server_expected_cookie_key_name = "BASIC_PLUGIN"
            go_server_expected_cookie_value = "hello"
            effective_env["PLUGIN_MAGIC_COOKIE_KEY"] = go_server_expected_cookie_key_name
            effective_env[go_server_expected_cookie_key_name] = go_server_expected_cookie_value
            if (
                "PLUGIN_MAGIC_COOKIE" in effective_env
                and go_server_expected_cookie_key_name != "PLUGIN_MAGIC_COOKIE"
            ):
                del effective_env["PLUGIN_MAGIC_COOKIE"]
            logger.info(
                f"Final effective_env for subprocess will include: PLUGIN_MAGIC_COOKIE_KEY={effective_env.get('PLUGIN_MAGIC_COOKIE_KEY')}, {go_server_expected_cookie_key_name}={effective_env.get(go_server_expected_cookie_key_name)}"
            )

            # --- Configure RPCPluginClient (the Python gRPC client part) ---
            client_constructor_config = {
                "plugins": {"kv": KVProtocol()},
                "env": effective_env,  # Env for the server subprocess it launches
                # Ensure RPCPluginClient knows mTLS is desired for its gRPC channel
                "enable_mtls": self.enable_mtls,
            }

            if self.enable_mtls:
                # Tests use GRPC_DEFAULT_* env vars for client's mTLS materials.
                # RPCPluginClient's explicit mTLS path expects these in its config dict.
                client_cert_path_env = os.getenv(ENV_GRPC_DEFAULT_CLIENT_CERTIFICATE_PATH)
                client_key_path_env = os.getenv(ENV_GRPC_DEFAULT_CLIENT_PRIVATE_KEY_PATH)
                server_ca_path_env = os.getenv(
                    ENV_GRPC_DEFAULT_SSL_ROOTS_FILE_PATH
                )  # CA client uses to verify server

                if client_cert_path_env and client_key_path_env and server_ca_path_env:
                    logger.info(
                        "KVClient: Populating RPCPluginClient config for mTLS with paths from GRPC_DEFAULT_* env vars."
                    )
                    client_constructor_config["client_cert_path"] = client_cert_path_env
                    client_constructor_config["client_key_path"] = client_key_path_env
                    client_constructor_config["server_root_ca_path"] = server_ca_path_env
                else:
                    logger.warning(
                        f"KVClient: mTLS enabled for KVClient, but not all {ENV_GRPC_DEFAULT_CLIENT_CERTIFICATE_PATH}, "
                        f"{ENV_GRPC_DEFAULT_CLIENT_PRIVATE_KEY_PATH}, or {ENV_GRPC_DEFAULT_SSL_ROOTS_FILE_PATH} env vars are set. "
                        "RPCPluginClient might not establish mTLS correctly if it relies on these config paths."
                    )

            logger.debug(
                f"KVClient: Final client_constructor_config for RPCPluginClient: {client_constructor_config}"
            )
            self._client = RPCPluginClient(
                command=server_command,
                config=client_constructor_config,
            )

            logger.debug(f"Starting RPCPluginClient (pyvider), timeout={self.connection_timeout}s")
            await asyncio.wait_for(self._client.start(), timeout=self.connection_timeout)

            if self._client._process and self._client._process.stderr:
                self._relay_stderr()

            self._stub = kv_pb2_grpc.KVStub(self._client.grpc_channel)
            self.is_started = True
            logger.info(
                f"KVClient connected to server in {time.time() - start_time:.3f}s. Server PID: {self._client._process.pid if self._client._process else 'N/A'}"
            )

        except TimeoutError:
            logger.error(f"KVClient connection to server timed out after {time.time() - start_time:.3f}s")
            if self._client and self._client._process and self._client._process.poll() is None:
                logger.debug("Server process was still running after client timeout.")
            self.is_started = False
            raise
        except Exception as e:
            logger.error(
                f"KVClient failed to connect/start server: {type(e).__name__} - {e}",
                exc_info=True,
            )
            self.is_started = False
            raise

    def _relay_stderr(self) -> None:
        import threading

        if not (self._client and self._client._process and self._client._process.stderr):
            logger.warning("stderr relay: client process or stderr not available.")
            return
        stderr_pipe = self._client._process.stderr

        def read_stderr_thread() -> None:
            logger.debug("stderr relay thread started.")
            while True:
                try:
                    if stderr_pipe.closed:
                        break
                    if not self._client or not self._client._process:
                        break
                    line_bytes = stderr_pipe.readline()
                    if not line_bytes:
                        break
                    decoded = line_bytes.decode("utf-8", errors="replace").strip()
                    if decoded:
                        logger.debug(f"SERVER_STDERR: {decoded}")
                except ValueError:
                    break
                except Exception as e:
                    logger.error(
                        f"Error in stderr relay thread: {type(e).__name__} - {e}",
                        exc_info=True,
                    )
                    break
            logger.debug("stderr relay thread finished.")

        thread = threading.Thread(target=read_stderr_thread, daemon=True)
        thread.start()

    async def close(self) -> None:
        if self._client:
            logger.debug("KVClient closing connection...")
            self.is_started = False
            try:
                if self._client._process and self._client._process.returncode is None:
                    if hasattr(self._client, "close") and asyncio.iscoroutinefunction(self._client.close):
                        await self._client.close()
                    elif hasattr(self._client, "close"):
                        self._client.close()
                    logger.debug("RPCPluginClient close called.")
                else:
                    logger.debug("RPCPluginClient process already terminated or not started.")
            except Exception as e:
                logger.error(
                    f"Error during RPCPluginClient.close(): {type(e).__name__} - {e}",
                    exc_info=True,
                )
            finally:
                self._client = None
                self._stub = None
                logger.debug("KVClient connection closed and attributes reset.")
        else:
            self.is_started = False
            logger.debug("KVClient.close() called but client was not initialized or already closed.")

    async def put(self, key: str, value: bytes) -> None:
        if not self.is_started or not self._stub:
            raise RuntimeError("KVClient not connected to server.")
        if not isinstance(value, bytes):
            raise TypeError("Value for put must be bytes.")
        try:
            logger.debug(f"KVClient: Sending Put - key='{key}', value_size={len(value)} bytes.")
            await asyncio.wait_for(
                self._stub.Put(kv_pb2.PutRequest(key=key, value=value)), timeout=REQUEST_TIMEOUT
            )
            logger.info(f"KVClient: Put successful for key='{key}'.")
        except TimeoutError:
            logger.error(f"KVClient: Put operation timed out for key='{key}'.")
            raise
        except Exception as e:
            logger.error(
                f"KVClient: Put failed for key='{key}'. Error: {type(e).__name__} - {e}",
                exc_info=True,
            )
            raise

    async def get(self, key: str) -> bytes | None:
        if not self.is_started or not self._stub:
            raise RuntimeError("KVClient not connected to server.")
        try:
            logger.debug(f"KVClient: Sending Get - key='{key}'.")
            response = await asyncio.wait_for(
                self._stub.Get(kv_pb2.GetRequest(key=key)), timeout=REQUEST_TIMEOUT
            )

            if response is not None:
                # In proto3, a bytes field defaults to empty bytes if not explicitly set.
                # The server's Get RPC implementation for a non-existent key returns a gRPC NOT_FOUND error,
                # which is caught by the AioRpcError handler below.
                # So, if we get here with a non-None response, the key was found.
                # response.value will be the bytes (could be empty if an empty value was stored).
                logger.info(
                    f"KVClient: Get successful for key='{key}', retrieved {len(response.value)} bytes."
                )
                return response.value
            else:
                # This path should ideally not be reached given gRPC behavior (either response or error).
                logger.warning(f"KVClient: Get for key='{key}' returned a None response object (unexpected).")
                return None
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                logger.info(f"KVClient: Key='{key}' not found on server (gRPC StatusCode.NOT_FOUND).")
                return None  # Correctly return None for not found
            logger.error(
                f"KVClient: Get for key='{key}' failed with gRPC error {e.code()}: {e.details()}",
                exc_info=True,
            )
            raise
        except TimeoutError:  # Keep specific timeout error handling
            logger.error(f"KVClient: Get operation timed out for key='{key}'.")
            raise
        except Exception as e:
            logger.error(
                f"KVClient: Get for key='{key}' failed. Error: {type(e).__name__} - {e}",
                exc_info=True,
            )
            raise


# 🍲🥄🖥️🪄
