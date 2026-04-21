Feature: CTY Value Conformance
  As a developer using TofuSoup,
  I want to ensure that both Python and Go tools can interpret and manipulate
  CTY data consistently, so that I can trust the conformance tests.

  Background:
    Given a temporary directory for test artifacts
    And a valid JSON file "simple_object.json" with content:
      """
      {
        "name": "test-server",
        "instance_count": 3,
        "is_enabled": true
      }
      """

  Scenario: Viewing a CTY value from a JSON file using the Python CLI
    When I run the Python command "soup cty view simple_object.json"
    Then the command should succeed
    And the output should contain the text "CTY Root"
    And the output should contain the text "name (string)"
    And the output should contain the text "instance_count (number)"
    And the output should contain the text "is_enabled (bool)"

  Scenario: Converting a CTY value from JSON to MessagePack using the Python CLI
    When I run the Python command "soup cty convert simple_object.json output.msgpack"
    Then the command should succeed
    And the file "output.msgpack" should exist
    And the file "output.msgpack" should be valid MessagePack representing the original object

  Scenario: Go harness decodes a Python-generated CTY value
    Given a JSON file "py_value.json" representing a CTY value with type "object({name=string,count=number})" and value '{"name": "test", "count": 123}'
    When I run the Go harness command "go-cty decode --input-file=py_value.json --input-format=json --type-string=object({name=string,count=number}) --stdout"
    Then the command should succeed
    And the JSON output should have a "type_name" of "object({count=number,name=string})"
    And the JSON output should have a "value" object with "name" equal to "test"

