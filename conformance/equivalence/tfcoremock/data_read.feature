
Feature: data_read

  Scenario: tests reading data from data sources using only a plan
    Given a resource of type "tfcoremock_simple_resource" named "create"
    And the resource has the following attributes:
      | string | "${data.tfcoremock_simple_resource.read.string}" |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
