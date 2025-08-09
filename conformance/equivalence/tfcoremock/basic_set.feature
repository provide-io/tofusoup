
Feature: basic_set

  Scenario: basic test coverting creation of a simple set
    Given a resource of type "tfcoremock_set" named "set"
    And the resource has the following attributes:
      | id | "046952C9-B832-4106-82C0-C217F7C73E18" |
      | set | ["41471135-E14C-4946-BFA4-2626C7E2A94A", "C04762B9-D07B-40FE-A92B-B72AD342658D", "D8F7EA80-9E25-4DD7-8D97-797D2080952B"] |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
