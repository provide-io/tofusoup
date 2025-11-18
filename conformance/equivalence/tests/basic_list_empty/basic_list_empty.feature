
Feature: basic_list_empty

  Scenario: tests removing all elements from a simple list
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

resource "tfcoremock_list" "list" {
  id = "985820B3-ACF9-4F00-94AD-F81C5EA33663"
  list = []
}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
