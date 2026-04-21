
Feature: local_provider_delete

  Scenario: test deleting a file created by the local provider
    Given a resource of type "" named ""
    When the resource is created
    Then the resource should exist in the state
