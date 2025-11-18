
Feature: basic_set_null

  Scenario: tests deleting a simple set
    Given a resource of type "tfcoremock_set" named "set"
    And the resource has the following attributes:
      | id | "046952C9-B832-4106-82C0-C217F7C73E18" |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
