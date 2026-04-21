Feature: Wire Protocol Encoding and Decoding Conformance
  As a developer building a Terraform provider,
  I need to ensure that the Python implementation of the wire protocol
  produces and consumes MessagePack payloads that are bit-for-bit compatible
  with the Go implementation.

  Background:
    Given a temporary directory for test artifacts
    And a JSON file "cty_string.json" representing a CTY string with content:
      """
      {
        "type": "string",
        "value": "test"
      }
      """

  Scenario: Python and Go encoders produce identical MessagePack output
    When the Python tool encodes "cty_string.json" to "py_output.msgpack"
    And the Go harness encodes "cty_string.json" to "go_output.msgpack"
    Then the file "py_output.msgpack" should be identical to "go_output.msgpack"

  Scenario: Python decodes a value encoded by the Go harness
    Given a MessagePack file "go_encoded.msgpack" created by the Go harness from "cty_string.json"
    When the Python tool decodes "go_encoded.msgpack" to "py_decoded.json"
    Then the command should succeed
    And the JSON content of "py_decoded.json" should match the value from "cty_string.json"

  Scenario: Go harness decodes a value encoded by the Python tool
    Given a MessagePack file "py_encoded.msgpack" created by the Python tool from "cty_string.json"
    When the Go harness decodes "py_encoded.msgpack" with type "string" to "go_decoded.json"
    Then the command should succeed
    And the JSON content of "go_decoded.json" should match the value from "cty_string.json"

