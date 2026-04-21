
Feature: simple_object_replace

  Scenario: tests updating an attribute that forces the overall resource to be replaced
    Given a resource of type "tfcoremock_object" named "object"
    And the resource has the following attributes:
      | id | "63A9E8E8-71BC-4DAE-A66C-48CE393CCBD3" |
      | object | {"string": "Hello, world!", "boolean": true, "number": 10} |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
