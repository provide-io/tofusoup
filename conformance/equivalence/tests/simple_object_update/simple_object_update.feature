
Feature: simple_object_update

  Scenario: tests updating objects when they are nested in other objects
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
  object = {
    string  = "Hello, a totally different world!"
    boolean = false
    number  = 2
  }
}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
