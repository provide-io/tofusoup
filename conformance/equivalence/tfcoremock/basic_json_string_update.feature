
Feature: basic_json_string_update

  Scenario: tests updating a JSON compatible string
    Given a resource of type "tfcoremock_simple_resource" named "json"
    And the resource has the following attributes:
      | string | "{\"list-attribute\":[\"one\",\"four\",\"three\"],\"object-attribute\":{\"key_one\":\"value_one\",\"key_three\":\"value_two\", \"key_four\":\"value_three\"},\"string-attribute\":\"a new string\"}" |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
