# Compare Pyvider's split function with Terraform's built-in split() function
locals {
  separator = ","
  input_string = "red,green,blue"
  
  # Pyvider version
  pyvider_result = provider::pyvider::split(local.separator, local.input_string)
  
  # Terraform built-in
  terraform_result = split(local.separator, local.input_string)
}

output "split_comparison" {
  value = {
    separator        = local.separator
    input_string     = local.input_string
    pyvider_result   = local.pyvider_result
    terraform_result = local.terraform_result
    results_match    = local.pyvider_result == local.terraform_result
  }
  
  description = "Comparison of Pyvider split() function with Terraform's built-in split()"
}

# Additional test cases
output "split_by_space" {
  value = {
    test      = "split(' ', 'hello world test')"
    pyvider   = provider::pyvider::split(" ", "hello world test")
    terraform = split(" ", "hello world test")
    match     = provider::pyvider::split(" ", "hello world test") == split(" ", "hello world test")
  }
}

output "split_multi_char_separator" {
  value = {
    test      = "split(' -> ', 'first -> second -> third')"
    pyvider   = provider::pyvider::split(" -> ", "first -> second -> third")
    terraform = split(" -> ", "first -> second -> third")
    match     = provider::pyvider::split(" -> ", "first -> second -> third") == split(" -> ", "first -> second -> third")
  }
}

output "split_no_separator_found" {
  value = {
    test      = "split(',', 'no-commas-here')"
    pyvider   = provider::pyvider::split(",", "no-commas-here")
    terraform = split(",", "no-commas-here")
    match     = provider::pyvider::split(",", "no-commas-here") == split(",", "no-commas-here")
  }
}

output "split_empty_string" {
  value = {
    test      = "split(',', '')"
    pyvider   = provider::pyvider::split(",", "")
    terraform = split(",", "")
    match     = provider::pyvider::split(",", "") == split(",", "")
  }
}

# 🍲🥄🔧🪄
