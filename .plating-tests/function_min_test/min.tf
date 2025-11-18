# Compare Pyvider's min function with Terraform's built-in min() function
locals {
  numbers = [8, 3, 12, 5, 2]
  
  # Pyvider version
  pyvider_result = provider::pyvider::min(local.numbers)
  
  # Terraform built-in
  terraform_result = min(local.numbers...)
}

output "min_comparison" {
  value = {
    input_numbers    = local.numbers
    pyvider_result   = local.pyvider_result
    terraform_result = local.terraform_result
    results_match    = local.pyvider_result == local.terraform_result
  }
  
  description = "Comparison of Pyvider min() function with Terraform's built-in min()"
}

# Additional test cases
output "min_negative_numbers" {
  value = {
    test      = "min([-5, -10, 0, 3, -2])"
    pyvider   = provider::pyvider::min([-5, -10, 0, 3, -2])
    terraform = min(-5, -10, 0, 3, -2)
    match     = provider::pyvider::min([-5, -10, 0, 3, -2]) == min(-5, -10, 0, 3, -2)
  }
}

output "min_decimals" {
  value = {
    test      = "min([3.14, 2.718, 1.414, 2.236])"
    pyvider   = provider::pyvider::min([3.14, 2.718, 1.414, 2.236])
    terraform = min(3.14, 2.718, 1.414, 2.236)
    match     = provider::pyvider::min([3.14, 2.718, 1.414, 2.236]) == min(3.14, 2.718, 1.414, 2.236)
  }
}

output "min_single_value" {
  value = {
    test      = "min([42])"
    pyvider   = provider::pyvider::min([42])
    terraform = min(42)
    match     = provider::pyvider::min([42]) == min(42)
  }
}

# 🍲🥄🔧🪄
