# Compare Pyvider's join function with Terraform's built-in join() function
locals {
  separator = "-"
  list_items = ["app", "prod", "v1"]
  
  # Pyvider version
  pyvider_result = provider::pyvider::join(local.separator, local.list_items)
  
  # Terraform built-in
  terraform_result = join(local.separator, local.list_items)
}

output "join_comparison" {
  value = {
    separator        = local.separator
    list_items       = local.list_items
    pyvider_result   = local.pyvider_result
    terraform_result = local.terraform_result
    results_match    = local.pyvider_result == local.terraform_result
  }
  
  description = "Comparison of Pyvider join() function with Terraform's built-in join()"
}

# Additional test cases
output "join_empty_separator" {
  value = {
    test      = "join('', ['a', 'b', 'c'])"
    pyvider   = provider::pyvider::join("", ["a", "b", "c"])
    terraform = join("", ["a", "b", "c"])
    match     = provider::pyvider::join("", ["a", "b", "c"]) == join("", ["a", "b", "c"])
  }
}

output "join_single_element" {
  value = {
    test      = "join(',', ['solo'])"
    pyvider   = provider::pyvider::join(",", ["solo"])
    terraform = join(",", ["solo"])
    match     = provider::pyvider::join(",", ["solo"]) == join(",", ["solo"])
  }
}

output "join_with_spaces" {
  value = {
    test      = "join(' | ', ['first', 'second', 'third'])"
    pyvider   = provider::pyvider::join(" | ", ["first", "second", "third"])
    terraform = join(" | ", ["first", "second", "third"])
    match     = provider::pyvider::join(" | ", ["first", "second", "third"]) == join(" | ", ["first", "second", "third"])
  }
}

output "join_empty_list" {
  value = {
    test      = "join(',', [])"
    pyvider   = provider::pyvider::join(",", [])
    terraform = join(",", [])
    match     = provider::pyvider::join(",", []) == join(",", [])
  }
}

# 🍲🥄🔧🪄
