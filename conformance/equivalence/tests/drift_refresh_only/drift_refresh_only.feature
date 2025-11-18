
Feature: drift_refresh_only

  Scenario: tests drift in a refresh only plan, so has a custom set of commands
    Given a Terraform configuration with the following content:
      """
      terraform {
  required_providers {
    tfcoremock = {
      source  = "hashicorp/tfcoremock"
      version = "0.1.1"
    }
  }
}

provider "tfcoremock" {}

resource "tfcoremock_simple_resource" "drift" {
  string = "Hello, world!"
}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
