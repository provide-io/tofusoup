
Feature: moved_with_update

  Scenario: this test updates a resource that has also been moved
    Given a resource of type "tfcoremock_simple_resource" named "moved"
    And the resource has the following attributes:
      | string | "Hello, change!" |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
