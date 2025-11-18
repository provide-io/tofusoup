
Feature: basic_json_string_update

  Scenario: tests updating a JSON compatible string
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

resource "tfcoremock_simple_resource" "json" {
  string = "{\"list-attribute\":[\"one\",\"four\",\"three\"],\"object-attribute\":{\"key_one\":\"value_one\",\"key_three\":\"value_two\", \"key_four\":\"value_three\"},\"string-attribute\":\"a new string\"}"
}

      """
    When the Terraform configuration is applied
    Then the resulting state should be equivalent to the upstream test case
