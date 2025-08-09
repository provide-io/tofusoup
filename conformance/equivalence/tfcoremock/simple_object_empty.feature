
Feature: simple_object_empty

  Scenario: tests removing all attributes from an object
    Given a resource of type "tfcoremock_object" named "object"
    And the resource has the following attributes:
      | object | {} |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
