
Feature: moved_simple

  Scenario: tests an unchanged resource being moved
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


resource "tfcoremock_simple_resource" "second" {
  string = "Hello, world!"
}

moved {
  from = tfcoremock_simple_resource.first
  to = tfcoremock_simple_resource.second
}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
