
Feature: multiple_block_types_update

  Scenario: basic test covering interaction between multiple blocks within a resource, while updating
    Given a resource of type "tfcoremock_multiple_blocks" named "multiple_blocks"
    And the resource has the following attributes:
      | id | "DA051126-BAD6-4EB2-92E5-F0250DAF0B92" |
      | first_block | [{"id": "B27FB8BE-52D4-4CEB-ACE9-5E7FB3968F2B"}, {"id": "E60148A2-04D1-4EF8-90A2-45CAFC02C60D"}, {"id": "717C64FB-6A93-4763-A1EF-FE4C5B341488"}] |
      | second_block | [{"id": "91640A80-A65F-4BEF-925B-684E4517A04D"}, {"id": "D080F298-2BA4-4DFA-A367-2C5FB0EA7BFE"}] |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
