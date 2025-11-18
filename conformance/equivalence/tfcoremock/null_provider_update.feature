
Feature: null_provider_update

  Scenario: tests creating a simple resource created by the null provider
    Given a resource of type "null_resource" named "null_resource"
    When the resource is created
    Then the resource should exist in the state
