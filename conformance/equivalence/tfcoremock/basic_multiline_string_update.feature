
Feature: basic_multiline_string_update

  Scenario: tests handling of multiline strings when updating
    Given a resource of type "tfcoremock_simple_resource" named "multiline"
    And the resource has the following attributes:
      | string | "one\nthree\ntwo\nfour\nsix\nseven" |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
