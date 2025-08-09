
Feature: variables_and_outputs

  Scenario: tests a set of basic variables and outputs
    Given a resource of type "" named ""
    When the resource is created
    Then the resource should exist in the state
