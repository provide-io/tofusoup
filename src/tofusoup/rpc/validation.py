#!/usr/bin/env python3
"""
RPC connection validation utilities.

Provides validation for:
- Elliptic curve support by runtime
- Language pair compatibility
- TLS mode compatibility
"""

from pathlib import Path

from provide.foundation import logger


class CurveNotSupportedError(ValueError):
    """Raised when a curve is not supported by the runtime."""

    pass


class LanguagePairNotSupportedError(ValueError):
    """Raised when a language pair combination is not supported."""

    pass


def detect_server_language(server_path: Path | str) -> str:
    """
    Detect if server is Python or Go based on binary name.

    Args:
        server_path: Path to server binary

    Returns:
        "python" or "go"
    """
    server_path = Path(server_path)
    binary_name = server_path.name

    if binary_name in ["soup", "python", "python3"]:
        return "python"
    elif binary_name in ["soup-go", "go-harness"] or "go" in binary_name:
        return "go"
    else:
        logger.warning("Could not detect server language from binary name", binary=binary_name)
        return "unknown"


def validate_curve_for_runtime(curve: str, language: str) -> None:
    """
    Validate that a curve is supported by the runtime.

    Args:
        curve: Curve name (e.g., "secp256r1", "secp384r1", "secp521r1")
        language: Runtime language ("python" or "go")

    Raises:
        CurveNotSupportedError: If curve is not supported by the runtime
    """
    # Python (grpcio) doesn't support secp521r1
    if language == "python" and curve == "secp521r1":
        raise CurveNotSupportedError(
            f"Curve '{curve}' is not supported by Python's grpcio library. "
            "Use 'secp256r1' or 'secp384r1' instead."
        )

    # Go supports all curves via TLSProvider
    if language == "go" and curve not in ["secp256r1", "secp384r1", "secp521r1", "auto"]:
        logger.warning("Unknown curve for Go server", curve=curve)

    logger.debug("Curve validation passed", curve=curve, language=language)


def validate_language_pair(client_lang: str, server_path: Path | str) -> None:
    """
    Validate that a client-server language pair is supported.

    Args:
        client_lang: Client language ("python" or "go")
        server_path: Path to server binary

    Raises:
        LanguagePairNotSupportedError: If language pair is not supported
    """
    server_lang = detect_server_language(server_path)

    # Python → Go is not supported (known bug in pyvider-rpcplugin)
    if client_lang == "python" and server_lang == "go":
        raise LanguagePairNotSupportedError(
            "Python client → Go server connections are not currently supported "
            "(known issue in pyvider-rpcplugin). "
            "\n\nWorkarounds:\n"
            "  - Use Go client → Python server instead\n"
            "  - Use Python client → Python server\n"
            "  - Use Go client → Go server"
        )

    logger.debug("Language pair validation passed", client=client_lang, server=server_lang)


def get_supported_curves(language: str) -> list[str]:
    """
    Get list of supported curves for a runtime.

    Args:
        language: Runtime language ("python" or "go")

    Returns:
        List of supported curve names
    """
    if language == "python":
        return ["secp256r1", "secp384r1"]
    elif language == "go":
        return ["secp256r1", "secp384r1", "secp521r1"]
    else:
        logger.warning("Unknown language, returning common curves", language=language)
        return ["secp256r1", "secp384r1"]


def get_compatibility_matrix() -> dict[str, dict[str, bool]]:
    """
    Get the language pair compatibility matrix.

    Returns:
        Dict of {client_lang: {server_lang: is_supported}}
    """
    return {
        "python": {
            "python": True,
            "go": False,  # Known bug
        },
        "go": {
            "python": True,
            "go": True,
        },
    }


# 🍲🥄📋🪄
