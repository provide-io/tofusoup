
Feature: replace_within_map

  Scenario: tests the behaviour of an attribute within a map causing a resource to be replaced
    Given a resource of type "tfcoremock_map" named "map"
    And the resource has the following attributes:
      | id | "F40F2AB4-100C-4AE8-BFD0-BF332A158415" |
      | map | {"key_one": {"id": "3BFC1A84-023F-44FA-A8EE-EFD88E18B8F7"}, "key_two": {"id": "07F887E2-FDFF-4B2E-9BFB-B6AA4A05EDB9"}, "key_three": {"id": "4B7178A8-AB9D-4FF4-8B3D-48B754DE537B"}} |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
