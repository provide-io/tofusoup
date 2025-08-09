locals {
  data = {
    items = [
      { "name" : "Laptop", "stock" : 15 },
      { "name" : "Mouse", "stock" : 150 }
    ]
  }
}

output "item_names" {
  value = provider::pyvider::lens_jq(local.data, "[.items[].name]")
}

# 🍲🥄🔧🪄
