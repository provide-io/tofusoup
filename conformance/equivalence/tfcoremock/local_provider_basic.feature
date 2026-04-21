
Feature: local_provider_basic

  Scenario: tests creating a local file using the local provider
    Given a resource of type "local_file" named "local_file"
    And the resource has the following attributes:
      | filename | "output.json" |
      | content | "${local.contents}" |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
