
Feature: simple_object_replace

  Scenario: tests updating an attribute that forces the overall resource to be replaced
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
  id = "63A9E8E8-71BC-4DAE-A66C-48CE393CCBD3"

  object = {
    string  = "Hello, world!"
    boolean = true
    number  = 10
  }
}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
