
Feature: null_provider_delete

  Scenario: tests deleting a resource created by the null provider
    Given a resource of type "" named ""
    When the resource is created
    Then the resource should exist in the state
