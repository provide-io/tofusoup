#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from pyvider.cty import (
    CtyBool,
    CtyDynamic,
    CtyList,
    CtyMap,
    CtyNumber,
    CtyObject,
    CtySet,
    CtyString,
    CtyTuple,
    CtyType,
)
from tofusoup.common.exceptions import TofuSoupError


class CtyTypeParseError(TofuSoupError):
    """Custom exception for CTY type string parsing errors."""

    pass


def _split_by_delimiter_respecting_nesting(text: str, delimiter: str) -> list[str]:
    if not text:
        return []
    parts: list[str] = []
    balance_paren = balance_bracket = balance_brace = 0
    current_part_start = 0
    for i, char in enumerate(text):
        if char == "(":
            balance_paren += 1
        elif char == ")":
            balance_paren -= 1
        elif char == "[":
            balance_bracket += 1
        elif char == "]":
            balance_bracket -= 1
        elif char == "{":
            balance_brace += 1
        elif char == "}":
            balance_brace -= 1
        elif char == delimiter and balance_paren == 0 and balance_bracket == 0 and balance_brace == 0:
            parts.append(text[current_part_start:i].strip())
            current_part_start = i + len(delimiter)
    parts.append(text[current_part_start:].strip())
    return [p for p in parts if p]


def _parse_primitive_type(type_str: str) -> CtyType | None:
    """Parse primitive CTY types (string, number, bool, dynamic).

    Args:
        type_str: The type string to parse

    Returns:
        CtyType instance if the string represents a primitive type, None otherwise
    """
    primitives = {
        "string": CtyString,
        "number": CtyNumber,
        "bool": CtyBool,
        "dynamic": CtyDynamic,
    }
    if type_str in primitives:
        return primitives[type_str]()
    return None


def _parse_collection_type(type_str: str) -> CtyType | None:
    """Parse collection CTY types (list, set, map).

    Args:
        type_str: The type string to parse

    Returns:
        CtyType instance if the string represents a collection type, None otherwise
    """
    collections = {
        "list": (CtyList, "list(", ")"),
        "set": (CtySet, "set(", ")"),
        "map": (CtyMap, "map(", ")"),
    }

    for _name, (cty_class, prefix, suffix) in collections.items():
        if type_str.startswith(prefix) and type_str.endswith(suffix):
            element_type_str = type_str[len(prefix) : -len(suffix)]
            return cty_class(element_type=parse_cty_type_string(element_type_str))

    return None


def _parse_structural_type(type_str: str) -> CtyType | None:
    """Parse structural CTY types (tuple, object).

    Args:
        type_str: The type string to parse

    Returns:
        CtyType instance if the string represents a structural type, None otherwise

    Raises:
        CtyTypeParseError: If the structural type format is invalid
    """
    # Parse tuple type: tuple([type1, type2, ...])
    if type_str.startswith("tuple([") and type_str.endswith("])"):
        element_types_str = type_str[len("tuple([") : -2]
        if not element_types_str:
            return CtyTuple(element_types=())
        element_type_strs = _split_by_delimiter_respecting_nesting(element_types_str, ",")
        return CtyTuple(element_types=tuple(parse_cty_type_string(s.strip()) for s in element_type_strs))

    # Parse object type: object({attr1=type1, attr2=type2, ...})
    if type_str.startswith("object({") and type_str.endswith("})"):
        attrs_str = type_str[len("object({") : -2]
        if not attrs_str.strip():
            return CtyObject(attribute_types={})

        attr_pairs_strs = _split_by_delimiter_respecting_nesting(attrs_str, ",")
        attribute_types: dict[str, CtyType] = {}
        for pair_str in attr_pairs_strs:
            if "=" not in pair_str:
                raise CtyTypeParseError(f"Invalid attribute format '{pair_str}'")
            name, type_name_str = pair_str.split("=", 1)
            attribute_types[name.strip()] = parse_cty_type_string(type_name_str.strip())
        return CtyObject(attribute_types=attribute_types)

    return None


def parse_cty_type_string(type_str: str) -> CtyType:
    """Parse a CTY type string into a CtyType instance.

    Supports primitive types (string, number, bool, dynamic), collection types
    (list, set, map), and structural types (tuple, object).

    Args:
        type_str: String representation of a CTY type

    Returns:
        CtyType instance representing the parsed type

    Raises:
        CtyTypeParseError: If the type string is unsupported or malformed

    Examples:
        >>> parse_cty_type_string("string")
        CtyString()
        >>> parse_cty_type_string("list(number)")
        CtyList(element_type=CtyNumber())
        >>> parse_cty_type_string("object({name=string, count=number})")
        CtyObject(attribute_types={'name': CtyString(), 'count': CtyNumber()})
    """
    type_str = type_str.strip()

    # Try parsing as primitive type
    result = _parse_primitive_type(type_str)
    if result is not None:
        return result

    # Try parsing as collection type
    result = _parse_collection_type(type_str)
    if result is not None:
        return result

    # Try parsing as structural type
    result = _parse_structural_type(type_str)
    if result is not None:
        return result

    # No parser matched
    raise CtyTypeParseError(f"Unsupported or malformed CTY type string: '{type_str}'")


# 🥣🔬🔚
