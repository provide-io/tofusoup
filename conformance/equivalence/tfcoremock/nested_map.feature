
Feature: nested_map

  Scenario: tests creating maps within maps
    Given a resource of type "tfcoremock_nested_map" named "nested_map"
    And the resource has the following attributes:
      | id | "502B0348-B796-4F6A-8694-A5A397237B85" |
      | maps | {"first_nested_map": {"first_key": "9E858021-953F-4DD3-8842-F2C782780422", "second_key": "D55D0E1E-51D9-4BCE-9021-7D201906D3C0"}, "second_nested_map": {"first_key": "6E80C701-A823-43FE-A520-699851EF9052", "second_key": "79CBEBB1-1192-480A-B4A8-E816A1A9D2FC"}} |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
