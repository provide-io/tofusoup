
Feature: simple_object

  Scenario: tests creating a simple object with primitive attributes
    Given a resource of type "tfcoremock_object" named "object"
    And the resource has the following attributes:
      | id | "AF9833AE-3434-4D0B-8B69-F4B992565D9F" |
      | object | {"string": "Hello, world!", "boolean": true, "number": 10} |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
