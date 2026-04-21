
Feature: drift_simple

  Scenario: a simple test that models drift in a single resource by updating an existing resource outside of Terraform
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
