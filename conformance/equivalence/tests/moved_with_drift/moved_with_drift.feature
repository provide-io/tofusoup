
Feature: moved_with_drift

  Scenario: tests using the moved block combined with simulated drift
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

resource "tfcoremock_simple_resource" "base_after" {
  string = "Hello, change!"
}

resource "tfcoremock_simple_resource" "dependent" {
  string = tfcoremock_simple_resource.base_after.string
}

moved {
  from = tfcoremock_simple_resource.base_before
  to = tfcoremock_simple_resource.base_after
}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
