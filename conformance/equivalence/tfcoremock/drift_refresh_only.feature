
Feature: drift_refresh_only

  Scenario: tests drift in a refresh only plan, so has a custom set of commands
    Given a resource of type "tfcoremock_simple_resource" named "drift"
    And the resource has the following attributes:
      | string | "Hello, world!" |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
