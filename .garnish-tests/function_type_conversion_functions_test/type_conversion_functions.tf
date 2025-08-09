locals {
  example_result = tostring(
    # Function arguments here
  )
}

output "function_result" {
  description = "Result of tostring function"  
  value       = local.example_result
}

# 🍲🥄🔧🪄
