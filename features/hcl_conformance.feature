Feature: HCL Parsing Conformance
  As a developer,
  I want to ensure that both the Python and Go HCL parsers produce
  semantically equivalent CTY representations from the same HCL input.

  Background:
    Given a temporary directory for test artifacts

  Scenario: Parsing a valid HCL file with both Python and Go harness
    Given a valid HCL file "config.hcl" with content:
      """
      string_attr = "hello"
      number_attr = 123
      bool_attr   = true
      """
    When I run the Python command "soup hcl convert config.hcl python_output.json"
    And I run the Go harness command "go-hcl parse config.hcl --output-format cty-json" and save stdout to "go_output.json"
    Then both commands should succeed
    And the JSON file "python_output.json" should be semantically equivalent to "go_output.json"

  Scenario: Handling an HCL file with a syntax error
    Given an HCL file "syntax_error.hcl" with content:
      """
      attr = "missing quote
      """
    When I run the Python command "soup hcl convert syntax_error.hcl error_output.json"
    Then the command should fail
    And the stderr should contain a parsing error message

  Scenario: Go harness handles an HCL file with a syntax error
    Given an HCL file "syntax_error.hcl" with content:
      """
      attr = "missing quote
      """
    When I run the Go harness command "go-hcl parse syntax_error.hcl"
    Then the command should fail
    And the stderr should contain a parsing error message

