
Feature: basic_map_empty

  Scenario: tests removing all elements from a simple map
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

resource "tfcoremock_map" "map" {
  id = "50E1A46E-E64A-4C1F-881C-BA85A5440964"
  map = {}
}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
