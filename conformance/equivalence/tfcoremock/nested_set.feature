
Feature: nested_set

  Scenario: tests creating sets within sets
    Given a resource of type "tfcoremock_nested_set" named "nested_set"
    And the resource has the following attributes:
      | id | "510598F6-83FE-4090-8986-793293E90480" |
      | sets | [[], ["9373D62D-1BF0-4F17-B100-7C0FBE368ADE"], ["7E90963C-BE32-4411-B9DD-B02E7FE75766", "29B6824A-5CB6-4C25-A359-727BAFEF25EB"]] |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
