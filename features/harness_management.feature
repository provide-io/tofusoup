Feature: Harness Lifecycle Management
  As a developer working on TofuSoup,
  I need a reliable CLI to manage the lifecycle of test harnesses,
  so that I can easily build and verify them.

  Scenario: Listing available harnesses when none are built
    Given the harness binary directory is empty
    When I run the command "soup harness list"
    Then the command should succeed
    And the output should contain "go-cty"
    And the output should contain "go-wire"
    And the output should contain "go-hcl"
    And the status for all harnesses should be "Not Built"

  Scenario: Building a single harness
    Given the "go-cty" harness is not built
    When I run the command "soup harness build go-cty"
    Then the command should succeed
    And the executable for the "go-cty" harness should exist

  Scenario: Building all harness
    Given the harness binary directory is empty
    When I run the command "soup harness build"
    Then the command should succeed
    And the executable for the "go-cty" harness should exist
    And the executable for the "go-wire" harness should exist
    And the executable for the "go-hcl" harness should exist

