
Feature: basic_multiline_string_update

  Scenario: tests handling of multiline strings when updating
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

resource "tfcoremock_simple_resource" "multiline" {
  string = "one\nthree\ntwo\nfour\nsix\nseven"
}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
