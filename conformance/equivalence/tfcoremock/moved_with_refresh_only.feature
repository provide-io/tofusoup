
Feature: moved_with_refresh_only

  Scenario: tests displaying a moved resource within a refresh only plan
    Given a resource of type "tfcoremock_simple_resource" named "second"
    And the resource has the following attributes:
      | string | "Hello, world!" |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
