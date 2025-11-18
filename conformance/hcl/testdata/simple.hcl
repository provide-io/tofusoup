variable "name" {
  type    = string
  default = "Terraform"
}

output "greeting" {
  value = "Hello, ${var.name}!"
}

locals {
  is_enabled = true
  port_map = {
    http = 80
    https = 443
  }
}
