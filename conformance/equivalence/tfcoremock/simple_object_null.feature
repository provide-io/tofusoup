
Feature: simple_object_null

  Scenario: tests setting an object within a resource to null by removing it from the config
    Given a resource of type "tfcoremock_object" named "object"
    When the resource is created
    Then the resource should exist in the state
