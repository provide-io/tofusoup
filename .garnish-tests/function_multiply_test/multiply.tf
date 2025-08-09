# Pyvider's multiply function (no Terraform built-in function, but has * operator)
locals {
  a = 4
  b = 6
  
  # Pyvider version
  pyvider_result = provider::pyvider::multiply(local.a, local.b)
  
  # Terraform equivalent using arithmetic
  terraform_equivalent = local.a * local.b
}

output "multiply_basic" {
  value = {
    input_a              = local.a
    input_b              = local.b
    pyvider_result       = local.pyvider_result
    terraform_equivalent = local.terraform_equivalent
    results_match        = local.pyvider_result == local.terraform_equivalent
  }
  
  description = "Basic multiplication example"
}

# Additional test cases
output "multiply_by_zero" {
  value = {
    test                 = "multiply(100, 0)"
    pyvider              = provider::pyvider::multiply(100, 0)
    terraform_equivalent = 100 * 0
    match                = provider::pyvider::multiply(100, 0) == (100 * 0)
  }
}

output "multiply_negatives" {
  value = {
    test                 = "multiply(-5, -8)"
    pyvider              = provider::pyvider::multiply(-5, -8)
    terraform_equivalent = -5 * (-8)
    match                = provider::pyvider::multiply(-5, -8) == (-5 * (-8))
  }
}

output "multiply_decimals" {
  value = {
    test                 = "multiply(2.5, 4.0)"
    pyvider              = provider::pyvider::multiply(2.5, 4.0)
    terraform_equivalent = 2.5 * 4.0
    match                = provider::pyvider::multiply(2.5, 4.0) == (2.5 * 4.0)
  }
}

# 🍲🥄🔧🪄
