
Feature: basic_list_null

  Scenario: tests deleting a simple list from a resource
    Given a resource of type "tfcoremock_list" named "list"
    And the resource has the following attributes:
      | id | "985820B3-ACF9-4F00-94AD-F81C5EA33663" |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
