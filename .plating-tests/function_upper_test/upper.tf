# Compare Pyvider's upper function with Terraform's built-in upper() function
locals {
  input_string = "hello world"
  
  # Pyvider version
  pyvider_result = provider::pyvider::upper(local.input_string)
  
  # Terraform built-in
  terraform_result = upper(local.input_string)
}

output "upper_comparison" {
  value = {
    input            = local.input_string
    pyvider_result   = local.pyvider_result
    terraform_result = local.terraform_result
    results_match    = local.pyvider_result == local.terraform_result
  }
  
  description = "Comparison of Pyvider upper() function with Terraform's built-in upper()"
}

# Additional test cases
output "upper_mixed_case" {
  value = {
    test      = "upper('Hello WORLD 123!')"
    pyvider   = provider::pyvider::upper("Hello WORLD 123!")
    terraform = upper("Hello WORLD 123!")
    match     = provider::pyvider::upper("Hello WORLD 123!") == upper("Hello WORLD 123!")
  }
}

output "upper_with_numbers" {
  value = {
    test      = "upper('abc123def')"
    pyvider   = provider::pyvider::upper("abc123def")
    terraform = upper("abc123def")
    match     = provider::pyvider::upper("abc123def") == upper("abc123def")
  }
}

output "upper_unicode" {
  value = {
    test      = "upper('café')"
    pyvider   = provider::pyvider::upper("café")
    terraform = upper("café")
    match     = provider::pyvider::upper("café") == upper("café")
  }
}

# 🍲🥄🔧🪄
