
Feature: drift_simple

  Scenario: a simple test that models drift in a single resource by updating an existing resource outside of Terraform
    Given a resource of type "tfcoremock_simple_resource" named "drift"
    And the resource has the following attributes:
      | string | "Hello, world!" |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
