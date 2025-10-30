#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from tofusoup import stir


def test_generate_status_table() -> None:
    """Verify the Rich table is generated correctly from the status dict."""
    stir.test_statuses = {
        "test_fail": {"text": "❌ FAIL", "style": "bold red", "active": False, "thread_id": "2"},
        "test_active": {
            "text": "APPLYING",
            "style": "blue",
            "active": True,
            "thread_id": "3",
            "last_log": "Still working...",
        },
    }

    table = stir.generate_status_table()

    assert len(table.rows) == 3
    # FIX: `table.columns[...].cells` is a generator. Convert it to a list to access by index.
    fail_row_index = 1  # The second row in the table
    test_suite_cell = list(table.columns[1].cells)[fail_row_index]
    status_cell = list(table.columns[2].cells)[fail_row_index]

    assert "test_fail" in str(test_suite_cell)
    assert "FAIL" in str(status_cell)


# 🥣🔬🔚
