#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner
import msgpack
from provide.testkit.mocking import MagicMock

from tofusoup.wire.cli import to_json, to_msgpack


def test_to_msgpack_command(monkeypatch: MonkeyPatch) -> None:
    """Verify the to-msgpack CLI command calls the logic layer correctly."""
    mock_convert = MagicMock()
    monkeypatch.setattr("tofusoup.wire.cli.convert_json_to_msgpack", mock_convert)

    runner = CliRunner()
    with runner.isolated_filesystem() as fs:
        input_file = Path(fs) / "test.json"
        input_file.write_text('{"valid": "json"}')

        result = runner.invoke(to_msgpack, [str(input_file.resolve())])
        assert result.exit_code == 0, result.output
        mock_convert.assert_called_once()


def test_to_json_command(monkeypatch: MonkeyPatch) -> None:
    """Verify the to-json CLI command calls the logic layer correctly."""
    mock_convert = MagicMock()
    monkeypatch.setattr("tofusoup.wire.cli.convert_msgpack_to_json", mock_convert)

    runner = CliRunner()
    with runner.isolated_filesystem() as fs:
        fs_path = Path(fs)
        input_file = fs_path / "test.msgpack"
        input_file.write_bytes(msgpack.packb({"valid": "msgpack"}))

        # FIX: The mock must return a Path object that exists *within* the isolated filesystem.
        output_file_in_fs = fs_path / "output.json"
        mock_convert.return_value = output_file_in_fs
        # FIX: The CLI reads this file for pretty-printing, so it must exist.
        output_file_in_fs.write_text('{"key": "value"}')

        result = runner.invoke(to_json, [str(input_file.resolve())])
        assert result.exit_code == 0, result.output
        mock_convert.assert_called_once()


def test_cli_handles_logic_errors(monkeypatch: MonkeyPatch) -> None:
    """Verify the CLI reports errors from the logic layer gracefully."""
    mock_convert = MagicMock(side_effect=msgpack.exceptions.PackException("Packing failed"))
    monkeypatch.setattr("tofusoup.wire.cli.convert_json_to_msgpack", mock_convert)

    runner = CliRunner()
    with runner.isolated_filesystem() as fs:
        input_file = Path(fs) / "test.json"
        input_file.write_text('{"valid": "json"}')

        result = runner.invoke(to_msgpack, [str(input_file.resolve())])
        assert result.exit_code == 1
        # FIX: Assert against the actual, more specific error message.
        assert "Error: Error during conversion: Packing failed" in result.output


# 🥣🔬🔚
