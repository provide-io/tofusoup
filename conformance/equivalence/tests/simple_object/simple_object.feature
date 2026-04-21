
Feature: simple_object

  Scenario: tests creating a simple object with primitive attributes
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

resource "tfcoremock_object" "object" {
  id = "AF9833AE-3434-4D0B-8B69-F4B992565D9F"
  object = {
    string  = "Hello, world!"
    boolean = true
    number  = 10
  }
}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
