#
# tofusoup/common/cty_type_parser.py
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
        elif (
            char == delimiter
            and balance_paren == 0
            and balance_bracket == 0
            and balance_brace == 0
        ):
            parts.append(text[current_part_start:i].strip())
            current_part_start = i + len(delimiter)
    parts.append(text[current_part_start:].strip())
    return [p for p in parts if p]


def parse_cty_type_string(type_str: str) -> CtyType:
    type_str = type_str.strip()
    if type_str == "string":
        return CtyString()
    if type_str == "number":
        return CtyNumber()
    if type_str == "bool":
        return CtyBool()
    if type_str == "dynamic":
        return CtyDynamic()
    if type_str.startswith("list(") and type_str.endswith(")"):
        return CtyList(element_type=parse_cty_type_string(type_str[len("list(") : -1]))
    if type_str.startswith("set(") and type_str.endswith(")"):
        return CtySet(element_type=parse_cty_type_string(type_str[len("set(") : -1]))
    if type_str.startswith("map(") and type_str.endswith(")"):
        return CtyMap(element_type=parse_cty_type_string(type_str[len("map(") : -1]))
    if type_str.startswith("tuple([") and type_str.endswith("])"):
        element_types_str = type_str[len("tuple([") : -2]
        if not element_types_str:
            return CtyTuple(element_types=())
        element_type_strs = _split_by_delimiter_respecting_nesting(
            element_types_str, ","
        )
        return CtyTuple(
            element_types=tuple(
                parse_cty_type_string(s.strip()) for s in element_type_strs
            )
        )
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
    raise CtyTypeParseError(f"Unsupported or malformed CTY type string: '{type_str}'")


# 🍲🥄📄🪄
