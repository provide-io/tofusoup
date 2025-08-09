# Compare Pyvider's add function with Terraform's built-in + operator
locals {
  a = 5
  b = 7
  
  # Pyvider version
  pyvider_result = provider::pyvider::add(local.a, local.b)
  
  # Terraform built-in
  terraform_result = local.a + local.b
}

output "add_comparison" {
  value = {
    input_a          = local.a
    input_b          = local.b
    pyvider_result   = local.pyvider_result
    terraform_result = local.terraform_result
    results_match    = local.pyvider_result == local.terraform_result
  }
  
  description = "Comparison of Pyvider add() function with Terraform's + operator"
}

# Additional test cases
output "add_negative_numbers" {
  value = {
    test     = "add(-10, 25)"
    pyvider  = provider::pyvider::add(-10, 25)
    terraform = -10 + 25
    match    = provider::pyvider::add(-10, 25) == (-10 + 25)
  }
}

output "add_decimals" {
  value = {
    test     = "add(3.14, 2.86)"
    pyvider  = provider::pyvider::add(3.14, 2.86)
    terraform = 3.14 + 2.86
    match    = provider::pyvider::add(3.14, 2.86) == (3.14 + 2.86)
  }
}

# 🍲🥄🔧🪄
