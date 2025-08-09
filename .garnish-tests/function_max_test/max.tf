# Compare Pyvider's max function with Terraform's built-in max() function
locals {
  numbers = [8, 3, 12, 5, 2]
  
  # Pyvider version
  pyvider_result = provider::pyvider::max(local.numbers)
  
  # Terraform built-in
  terraform_result = max(local.numbers...)
}

output "max_comparison" {
  value = {
    input_numbers    = local.numbers
    pyvider_result   = local.pyvider_result
    terraform_result = local.terraform_result
    results_match    = local.pyvider_result == local.terraform_result
  }
  
  description = "Comparison of Pyvider max() function with Terraform's built-in max()"
}

# Additional test cases
output "max_negative_numbers" {
  value = {
    test      = "max([-5, -10, 0, 3, -2])"
    pyvider   = provider::pyvider::max([-5, -10, 0, 3, -2])
    terraform = max(-5, -10, 0, 3, -2)
    match     = provider::pyvider::max([-5, -10, 0, 3, -2]) == max(-5, -10, 0, 3, -2)
  }
}

output "max_decimals" {
  value = {
    test      = "max([3.14, 2.718, 1.414, 2.236])"
    pyvider   = provider::pyvider::max([3.14, 2.718, 1.414, 2.236])
    terraform = max(3.14, 2.718, 1.414, 2.236)
    match     = provider::pyvider::max([3.14, 2.718, 1.414, 2.236]) == max(3.14, 2.718, 1.414, 2.236)
  }
}

output "max_single_value" {
  value = {
    test      = "max([42])"
    pyvider   = provider::pyvider::max([42])
    terraform = max(42)
    match     = provider::pyvider::max([42]) == max(42)
  }
}

# 🍲🥄🔧🪄
