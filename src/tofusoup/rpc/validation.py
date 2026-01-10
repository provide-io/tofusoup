#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""RPC connection validation utilities.

Provides validation for:
- Elliptic curve support by runtime
- Language pair compatibility
- TLS mode compatibility"""

from pathlib import Path

from provide.foundation import logger

# Curve name mapping for normalization
CURVE_NAME_ALIASES = {
    # secp256r1 / P-256 / prime256v1
    "secp256r1": "secp256r1",
    "p-256": "secp256r1",
    "p256": "secp256r1",
    "prime256v1": "secp256r1",
    # secp384r1 / P-384
    "secp384r1": "secp384r1",
    "p-384": "secp384r1",
    "p384": "secp384r1",
    # secp521r1 / P-521
    "secp521r1": "secp521r1",
    "p-521": "secp521r1",
    "p521": "secp521r1",
    # Special case for auto
    "auto": "auto",
    "": "auto",
}


class CurveNotSupportedError(ValueError):
    """Raised when a curve is not supported by the runtime."""


class LanguagePairNotSupportedError(ValueError):
    """Raised when a language pair combination is not supported."""


def normalize_curve_name(curve: str) -> str:
    """
    Normalize curve name to standard format (secp256r1, secp384r1, secp521r1).

    Accepts various aliases like P-256, p256, etc. and converts them to the
    canonical secpXXXr1 format.

    Args:
        curve: Curve name in any supported format

    Returns:
        Normalized curve name (secp256r1, secp384r1, secp521r1, or auto)

    Raises:
        ValueError: If curve name is not recognized
    """
    normalized = CURVE_NAME_ALIASES.get(curve.lower())
    if normalized is None:
        raise ValueError(
            f"Unknown curve name: {curve}. "
            f"Supported formats: P-256/p256/secp256r1, P-384/p384/secp384r1, P-521/p521/secp521r1"
        )
    return normalized


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

    # All language pairs are now supported
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


# 🥣🔬🔚
