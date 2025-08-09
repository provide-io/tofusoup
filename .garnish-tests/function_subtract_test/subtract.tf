# Pyvider's subtract function (no Terraform built-in equivalent)
locals {
  a = 10
  b = 3
  
  # Pyvider version
  pyvider_result = provider::pyvider::subtract(local.a, local.b)
  
  # Terraform equivalent using arithmetic
  terraform_equivalent = local.a - local.b
}

output "subtract_basic" {
  value = {
    input_a              = local.a
    input_b              = local.b
    pyvider_result       = local.pyvider_result
    terraform_equivalent = local.terraform_equivalent
    results_match        = local.pyvider_result == local.terraform_equivalent
  }
  
  description = "Basic subtraction example"
}

# Additional test cases
output "subtract_negative_result" {
  value = {
    test                 = "subtract(5, 10)"
    pyvider              = provider::pyvider::subtract(5, 10)
    terraform_equivalent = 5 - 10
    match                = provider::pyvider::subtract(5, 10) == (5 - 10)
  }
}

output "subtract_with_negatives" {
  value = {
    test                 = "subtract(-10, -25)"
    pyvider              = provider::pyvider::subtract(-10, -25)
    terraform_equivalent = -10 - (-25)
    match                = provider::pyvider::subtract(-10, -25) == (-10 - (-25))
  }
}

output "subtract_decimals" {
  value = {
    test                 = "subtract(10.5, 3.2)"
    pyvider              = provider::pyvider::subtract(10.5, 3.2)
    terraform_equivalent = 10.5 - 3.2
    match                = provider::pyvider::subtract(10.5, 3.2) == (10.5 - 3.2)
  }
}

# 🍲🥄🔧🪄
