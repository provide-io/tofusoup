
Feature: simple_object_null

  Scenario: tests setting an object within a resource to null by removing it from the config
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

resource "tfcoremock_object" "object" {}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
