
Feature: simple_object_update

  Scenario: tests updating objects when they are nested in other objects
    Given a resource of type "tfcoremock_object" named "object"
    And the resource has the following attributes:
      | object | {"string": "Hello, a totally different world!", "boolean": false, "number": 2} |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
