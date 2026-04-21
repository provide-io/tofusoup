
Feature: basic_set_null

  Scenario: tests deleting a simple set
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

resource "tfcoremock_set" "set" {
  id = "046952C9-B832-4106-82C0-C217F7C73E18"
}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
