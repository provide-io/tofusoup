
Feature: basic_map_null

  Scenario: tests deleting a simple map from a resource
    Given a resource of type "tfcoremock_map" named "map"
    And the resource has the following attributes:
      | id | "50E1A46E-E64A-4C1F-881C-BA85A5440964" |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
