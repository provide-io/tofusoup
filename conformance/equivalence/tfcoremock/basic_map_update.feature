
Feature: basic_map_update

  Scenario: basic test coverting updating a simple map
    Given a resource of type "tfcoremock_map" named "map"
    And the resource has the following attributes:
      | id | "50E1A46E-E64A-4C1F-881C-BA85A5440964" |
      | map | {"zero": "6B044AF7-172B-495B-BE11-B9546C12C3BD", "two": "212FFBF6-40FE-4862-B708-E6AA508E84E0", "four": "D820D482-7C2C-4EF3-8935-863168A193F9"} |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
