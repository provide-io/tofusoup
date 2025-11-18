
Feature: null_provider_delete

  Scenario: tests deleting a resource created by the null provider
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

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
