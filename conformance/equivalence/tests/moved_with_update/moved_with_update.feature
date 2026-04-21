
Feature: moved_with_update

  Scenario: this test updates a resource that has also been moved
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

resource "tfcoremock_simple_resource" "moved" {
  string = "Hello, change!"
}

moved {
  from = tfcoremock_simple_resource.base
  to = tfcoremock_simple_resource.moved
}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
