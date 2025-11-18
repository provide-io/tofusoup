
Feature: drift_relevant_attributes

  Scenario: tests that relevant attributes are applied when dependent resources are updated by drift
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

resource "tfcoremock_simple_resource" "base" {
  string = "Hello, change!"
  number = 0
}

resource "tfcoremock_simple_resource" "dependent" {
  string = tfcoremock_simple_resource.base.string
}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
