
Feature: drift_relevant_attributes

  Scenario: tests that relevant attributes are applied when dependent resources are updated by drift
    Given a resource of type "tfcoremock_simple_resource" named "base"
    And the resource has the following attributes:
      | string | "Hello, change!" |
      | number | 0 |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
