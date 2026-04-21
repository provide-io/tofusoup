
Feature: basic_set_empty

  Scenario: tests removing all elements from a simple set
    Given a resource of type "tfcoremock_set" named "set"
    And the resource has the following attributes:
      | id | "046952C9-B832-4106-82C0-C217F7C73E18" |
      | set | [] |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
