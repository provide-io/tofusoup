
Feature: null_provider_update

  Scenario: tests creating a simple resource created by the null provider
    Given a Terraform configuration with the following content:
      """
      terraform {
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "3.1.1"
    }
  }
}

provider "null" {}

resource "null_resource" "null_resource" {}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
