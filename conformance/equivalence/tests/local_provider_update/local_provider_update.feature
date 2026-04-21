
Feature: local_provider_update

  Scenario: tests updating a file using the local provider
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

resource "local_file" "local_file" {
  filename = "output.json"
  content  = local.contents
}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
