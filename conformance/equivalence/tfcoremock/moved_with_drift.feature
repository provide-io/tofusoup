
Feature: moved_with_drift

  Scenario: tests using the moved block combined with simulated drift
    Given a resource of type "tfcoremock_simple_resource" named "base_after"
    And the resource has the following attributes:
      | string | "Hello, change!" |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
