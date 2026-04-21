
Feature: replace_within_object

  Scenario: tests the behaviour of an attribute within an object causing a resource to be replaced
    Given a resource of type "tfcoremock_object" named "object"
    And the resource has the following attributes:
      | id | "F40F2AB4-100C-4AE8-BFD0-BF332A158415" |
      | object | {"id": "07F887E2-FDFF-4B2E-9BFB-B6AA4A05EDB9"} |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
