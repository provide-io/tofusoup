
Feature: local_provider_delete

  Scenario: test deleting a file created by the local provider
    Given a Terraform configuration with the following content:
      """
      terraform {
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "2.2.3"
    }
  }
}

locals {
  contents = jsonencode({
    "goodbye" = "world"
  })
}

provider "local" {}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
