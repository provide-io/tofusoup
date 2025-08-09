# Terraform Object Wire Protocol: Dynamic Type Encoding

This document details how CTY Dynamic Values (`cty.DynamicPseudoType`) are encoded and decoded in the TofuSoup project, ensuring compatibility between the Go reference harness and the Python `pyvider` libraries.

## Dynamic Value Wire Format

When a `cty.DynamicVal` is transmitted using the Terraform Object Wire Protocol (which uses MessagePack), it is encoded as a 2-element MessagePack array:

```
[ <type_specification_bytes>, <value_bytes> ]
```

1.  **`<type_specification_bytes>` (First Element):**
    -   This element represents the **concrete type** of the value that the dynamic value actually holds.
    -   **Encoding Process:**
        1.  The concrete `cty.Type` of the value is determined (e.g., `cty.String`).
        2.  This type is marshalled into its **JSON string representation** (e.g., `"string"` or `["list","number"]`).
        3.  The UTF-8 bytes of this JSON string are then encoded as a **MessagePack binary data type (`bin` family)**.

2.  **`<value_bytes>` (Second Element):**
    -   This element is the standard MessagePack encoding of the **concrete `cty.Value`** itself.

## Example

Consider a dynamic value holding `cty.StringVal("hello")`.

1.  **Concrete Type:** `cty.String`
2.  **JSON Type String:** The literal string `"string"`.
3.  **`<type_specification_bytes>`:** The MessagePack `bin` encoding of the UTF-8 bytes for `"string"`.
    -   Hex: `c40822737472696e6722`
4.  **Concrete Value:** `cty.StringVal("hello")`
5.  **`<value_bytes>`:** The MessagePack `str` encoding of "hello".
    -   Hex: `a568656c6c6f`
6.  **Final 2-Element Msgpack Array:**
    -   Hex: `92c40822737472696e6722a568656c6c6f`
7.  **Base64 Representation:** `ksQIInN0cmluZyKlaGVsbG8=`

This method ensures that the type constraint of the dynamic value is clearly and unambiguously encoded in the wire format, allowing the decoding side to correctly interpret the subsequent value bytes.
