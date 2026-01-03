#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Script to verify the Command Line Interface (CLI) of TofuSoup's Go harnesses.

It runs a predefined set of commands for each harness and captures their
stdout and stderr into log files. This helps ensure that the harnesses
can be invoked correctly and that their basic CLI operations (like --help)
are functional.

Output logs are stored in: tofusoup/soup/logs/harness/
Dummy data files are created in: tofusoup/soup/data/"""

import base64
import json
import pathlib
import subprocess

# Define project root assuming the script is in tofusoup/scripts/
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.resolve()
SOUP_DIR = PROJECT_ROOT / "soup"
LOG_DIR = SOUP_DIR / "logs" / "harnesses"
DATA_DIR = SOUP_DIR / "data"
HARNESS_BIN_DIR = PROJECT_ROOT / "harnesses" / "bin"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Define dummy data content
DUMMY_DATA = {
    "dummy_cty_encoded.json": {"type": "string", "value": "decoded_from_file"},
    "dummy_for_wire_encode.json": {"type": "string", "value": "wire_this_string"},
    "dummy_b64_msgpack.tfwire": base64.b64encode(b"\xa2\x00\xb0wire_this_string").decode(
        "utf-8"
    ),  # msgpack for {"": "wire_this_string"} then b64
    # Corrected msgpack for "wire_this_string" (simple string) then b64.
    # msgpack.packb("wire_this_string") -> b'\xb0wire_this_string'
    # base64.b64encode(b'\xb0wire_this_string').decode('utf-8') -> 'sHdpcmVfdGhpc19zdHJpbmc='
}
DUMMY_DATA["dummy_b64_msgpack.tfwire"] = base64.b64encode(b"\xb0wire_this_string").decode("utf-8")


HARNESS_INVOCATIONS = {
    "go-cty": [
        {"args": ["--help"], "log_summary": "help", "stdin": None},
        {
            "args": ["--operation", "get-type-schema", "--type-string", "string"],
            "log_summary": "gettypeschema-string",
            "stdin": None,
        },
        {
            "args": ["--operation", "get-type-schema", "--type-string", "object({name=string,age=number})"],
            "log_summary": "gettypeschema-object",
            "stdin": None,
        },
        {
            "args": ["--operation", "validate", "--type-string", "number", "--value-json", "123"],
            "log_summary": "validate-number-valid",
            "stdin": None,
        },
        {
            "args": ["--operation", "validate", "--type-string", "number", "--value-json", '"abc"'],
            "log_summary": "validate-number-invalid",
            "stdin": None,
        },
        {
            "args": [
                "--operation",
                "encode",
                "--type-string",
                "string",
                "--value-json",
                '"hello"',
                "--output-format",
                "cty-json",
            ],
            "log_summary": "encode-string-ctyjson",
            "stdin": None,
        },
        {
            "args": [
                "--operation",
                "decode",
                "--input-file",
                str(DATA_DIR / "dummy_cty_encoded.json"),
                "--input-format",
                "cty-json",
                "--output-format",
                "cty-json",
            ],
            "log_summary": "decode-ctyjson-ctyjson",
            "stdin": None,
        },
    ],
    "go-rpc": [  # This is currently the KV server
        {"args": ["--help"], "log_summary": "help", "stdin": None},
        {"args": [], "log_summary": "noargs", "stdin": None},  # To see how it behaves when run directly
    ],
    "go-wire": [
        {"args": ["--help"], "log_summary": "help", "stdin": None},
        {
            "args": ["encode", str(DATA_DIR / "dummy_for_wire_encode.json")],
            "log_summary": "encode-string",
            "stdin": None,
        },  # Cobra style
        {
            "args": ["decode", "--type", "string", str(DATA_DIR / "dummy_b64_msgpack.tfwire")],
            "log_summary": "decode-string-withtype",
            "stdin": None,
        },  # Cobra style
    ],
}


def create_dummy_files() -> None:
    """Creates dummy data files needed for some harness invocations."""
    print("Creating dummy data files...")
    for filename, content in DUMMY_DATA.items():
        filepath = DATA_DIR / filename
        if isinstance(content, (dict, list)):
            filepath.write_text(json.dumps(content, indent=2))
        else:
            filepath.write_text(str(content))
        print(f"  Created: {filepath}")


def run_verification() -> None:
    """Runs the CLI verification for all defined harnesses."""
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Harness Bin Dir: {HARNESS_BIN_DIR}")
    print(f"Log Dir: {LOG_DIR}")
    print(f"Data Dir: {DATA_DIR}")

    create_dummy_files()
    print("\nStarting CLI verification for harness...")

    for harness_name, invocations in HARNESS_INVOCATIONS.items():
        harness_executable = HARNESS_BIN_DIR / harness_name
        lang = "go"  # Assuming all are Go for now

        if not harness_executable.exists():
            print(f"  SKIPPING {harness_name}: Executable not found at {harness_executable}")
            continue

        print(f"\n  Verifying: {harness_name} (at {harness_executable})")

        for invocation_details in invocations:
            args = invocation_details["args"]
            log_summary = invocation_details["log_summary"]
            stdin_content = invocation_details["stdin"]

            command = [str(harness_executable), *args]
            print(f"    Running: {' '.join(command)}")

            try:
                process = subprocess.run(
                    command,
                    input=stdin_content.encode("utf-8") if stdin_content else None,
                    capture_output=True,
                    text=False,  # Capture raw bytes
                    timeout=15,  # Generous timeout for CLI tools
                )

                stdout_bytes = process.stdout
                stderr_bytes = process.stderr

                # Try decoding as UTF-8, replace errors
                stdout_content = stdout_bytes.decode("utf-8", errors="replace")
                stderr_content = stderr_bytes.decode("utf-8", errors="replace")

                log_file_base = LOG_DIR / f"{lang}-{harness_name}-{log_summary}"

                stdout_log_file = log_file_base.with_suffix(".stdout.log")
                stderr_log_file = log_file_base.with_suffix(".stderr.log")

                stdout_log_file.write_text(stdout_content)
                stderr_log_file.write_text(stderr_content)

                print(f"      Logged stdout to: {stdout_log_file}")
                print(f"      Logged stderr to: {stderr_log_file}")
                if process.returncode != 0:
                    print(f"      WARNING: Command exited with code {process.returncode}")

            except subprocess.TimeoutExpired:
                print(f"      ERROR: Command timed out: {' '.join(command)}")
                log_file_base = LOG_DIR / f"{lang}-{harness_name}-{log_summary}"
                timeout_log_file = log_file_base.with_suffix(".timeout.log")
                timeout_log_file.write_text("Command timed out after 15 seconds.")
            except Exception as e:
                print(f"      ERROR: Failed to run command {' '.join(command)}: {e}")
                log_file_base = LOG_DIR / f"{lang}-{harness_name}-{log_summary}"
                error_log_file = log_file_base.with_suffix(".exception.log")
                error_log_file.write_text(f"Exception during execution: {type(e).__name__}: {e}")

    print("\nCLI verification complete.")


if __name__ == "__main__":
    run_verification()

# 🥣🔬🔚
