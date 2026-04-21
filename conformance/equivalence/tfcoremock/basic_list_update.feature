
Feature: basic_list_update

  Scenario: tests adding and removing elements from a simple list
    Given a resource of type "tfcoremock_list" named "list"
    And the resource has the following attributes:
      | id | "985820B3-ACF9-4F00-94AD-F81C5EA33663" |
      | list | ["9C2BE420-042D-440A-96E9-75565341C994", "D01290F6-2D3A-45FA-B006-DAA80F6D31F6", "9B9F3ADF-8AD4-4E8C-AFE4-7BC2413E9AC0"] |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
