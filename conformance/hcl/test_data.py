#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""HCL test data for cross-language interoperability tests.

This module provides HCL test cases for validating Python ↔ Go compatibility.
Tests cover primitives, collections, nested structures, and HCL-specific features.
"""

from decimal import Decimal

from pyvider.cty import CtyBool, CtyList, CtyNumber, CtyObject, CtyString

# HCL content strings for testing
HCL_TEST_CASES = {
    "simple_string": """
name = "hello world"
""",
    "simple_number": """
count = 42
""",
    "simple_bool": """
enabled = true
""",
    "simple_decimal": """
price = 3.14
""",
    "multiple_primitives": """
name = "webapp"
port = 8080
enabled = true
rate = 0.5
""",
    "list_of_strings": """
tags = ["web", "api", "production"]
""",
    "list_of_numbers": """
ports = [80, 443, 8080]
""",
    "list_of_bools": """
flags = [true, false, true]
""",
    "nested_object": """
config = {
    name = "app"
    timeout = 30
}
""",
    "deeply_nested": """
server = {
    name = "web-1"
    config = {
        port = 8080
        ssl = {
            enabled = true
            cert = "cert.pem"
        }
    }
}
""",
    "list_of_objects": """
servers = [
    {
        name = "web-1"
        ip = "10.0.1.1"
    },
    {
        name = "web-2"
        ip = "10.0.1.2"
    }
]
""",
    "mixed_types": """
name = "test"
count = 5
enabled = true
tags = ["a", "b"]
config = {
    timeout = 10
}
""",
}

# Expected CTY schemas for validation
HCL_EXPECTED_SCHEMAS = {
    "simple_string": CtyObject({"name": CtyString()}),
    "simple_number": CtyObject({"count": CtyNumber()}),
    "simple_bool": CtyObject({"enabled": CtyBool()}),
    "simple_decimal": CtyObject({"price": CtyNumber()}),
    "multiple_primitives": CtyObject(
        {
            "name": CtyString(),
            "port": CtyNumber(),
            "enabled": CtyBool(),
            "rate": CtyNumber(),
        }
    ),
    "list_of_strings": CtyObject({"tags": CtyList(element_type=CtyString())}),
    "list_of_numbers": CtyObject({"ports": CtyList(element_type=CtyNumber())}),
    "list_of_bools": CtyObject({"flags": CtyList(element_type=CtyBool())}),
    "nested_object": CtyObject(
        {
            "config": CtyObject(
                {
                    "name": CtyString(),
                    "timeout": CtyNumber(),
                }
            )
        }
    ),
    "deeply_nested": CtyObject(
        {
            "server": CtyObject(
                {
                    "name": CtyString(),
                    "config": CtyObject(
                        {
                            "port": CtyNumber(),
                            "ssl": CtyObject(
                                {
                                    "enabled": CtyBool(),
                                    "cert": CtyString(),
                                }
                            ),
                        }
                    ),
                }
            )
        }
    ),
    "list_of_objects": CtyObject(
        {
            "servers": CtyList(
                element_type=CtyObject(
                    {
                        "name": CtyString(),
                        "ip": CtyString(),
                    }
                )
            )
        }
    ),
    "mixed_types": CtyObject(
        {
            "name": CtyString(),
            "count": CtyNumber(),
            "enabled": CtyBool(),
            "tags": CtyList(element_type=CtyString()),
            "config": CtyObject(
                {
                    "timeout": CtyNumber(),
                }
            ),
        }
    ),
}

# Expected values for validation
HCL_EXPECTED_VALUES = {
    "simple_string": {"name": "hello world"},
    "simple_number": {"count": Decimal("42")},
    "simple_bool": {"enabled": True},
    "simple_decimal": {"price": Decimal("3.14")},
    "multiple_primitives": {
        "name": "webapp",
        "port": Decimal("8080"),
        "enabled": True,
        "rate": Decimal("0.5"),
    },
    "list_of_strings": {"tags": ["web", "api", "production"]},
    "list_of_numbers": {"ports": [Decimal("80"), Decimal("443"), Decimal("8080")]},
    "list_of_bools": {"flags": [True, False, True]},
    "nested_object": {
        "config": {
            "name": "app",
            "timeout": Decimal("30"),
        }
    },
    "deeply_nested": {
        "server": {
            "name": "web-1",
            "config": {
                "port": Decimal("8080"),
                "ssl": {
                    "enabled": True,
                    "cert": "cert.pem",
                },
            },
        }
    },
    "list_of_objects": {
        "servers": [
            {"name": "web-1", "ip": "10.0.1.1"},
            {"name": "web-2", "ip": "10.0.1.2"},
        ]
    },
    "mixed_types": {
        "name": "test",
        "count": Decimal("5"),
        "enabled": True,
        "tags": ["a", "b"],
        "config": {"timeout": Decimal("10")},
    },
}


# 🥣🔬🔚
