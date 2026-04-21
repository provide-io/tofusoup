# pyvider/components/tf/nested_data_test/nested_data_test.tf
# Systematic test of nested data handling across component types

terraform {
  required_providers {
    pyvider = {
      source = "registry.terraform.io/provide-io/pyvider"
      version = "0.1.0"
    }
  }
}

provider "pyvider" {
}

# =============================================================================
# Level 1: Simple Map Test (should work)
# =============================================================================

data "pyvider_simple_map_test" "level1" {
  input_data = {
    "key1" = "value1"
    "key2" = "value2"
    "key3" = "value3"
  }
}

output "level1_simple_map" {
  value = {
    input = data.pyvider_simple_map_test.level1.input_data
    processed = data.pyvider_simple_map_test.level1.processed_data
    hash = data.pyvider_simple_map_test.level1.data_hash
  }
}

# =============================================================================
# Level 2: Mixed Type Map Test
# =============================================================================

data "pyvider_mixed_map_test" "level2_complex" {
  input_data = {
    "string_val" = "terraform"
    "number_val" = 123
    "bool_val" = true
    "list_val" = ["item1", "item2", "item3"]
    "nested_map" = {
      "inner_key" = "inner_value"
      "inner_num" = 456
    }
  }
}

output "level2_complex_result" {
  value = {
    status = "attempting complex mixed types"
    input_summary = try(keys(data.pyvider_mixed_map_test.level2_complex.input_data), "FAILED")
    processed_summary = try(keys(data.pyvider_mixed_map_test.level2_complex.processed_data), "FAILED")
  }
}

# =============================================================================
# Level 3: Structured Object Test (well-defined nesting)
# =============================================================================

data "pyvider_structured_object_test" "level3" {
  config_name = "test_config"
  metadata = {
    "env" = "development"
    "owner" = "terraform"
    "version" = "1.0"
  }
}

output "level3_structured_result" {
  value = {
    config_name = data.pyvider_structured_object_test.level3.config_name
    generated_config = data.pyvider_structured_object_test.level3.generated_config
    summary = data.pyvider_structured_object_test.level3.summary
  }
}

# =============================================================================
# Level 4: Nested Resource Test (state management with nesting)
# =============================================================================

resource "pyvider_nested_resource_test" "level4" {
  resource_name = "test_nested_resource"
  
  configuration = {
    "app_name" = "my_app"
    "replicas" = 3
    "enabled" = true
    "tags" = ["web", "api", "production"]
  }
  
  nested_configs {
    service  = "web"
    port     = 80
    protocol = "http"
  }

  nested_configs {
    service     = "api" 
    port        = 443
    protocol    = "https"
    ssl_enabled = true
  }
}

output "level4_resource_result" {
  value = pyvider_nested_resource_test.level4
}

# =============================================================================
# Level 5: Complex Function Test (returns nested data)
# =============================================================================

output "level5_function_simple" {
  # FIX: Use jsondecode() and jsonencode() for a stable contract.
  value = jsondecode(provider::pyvider::pyvider_nested_data_processor(jsonencode({
    "simple_key" = "simple_value"
    "number" = 42
  }), "analyze"))
}

output "level5_function_complex" {
  # FIX: Use jsondecode() and jsonencode()
  value = jsondecode(provider::pyvider::pyvider_nested_data_processor(jsonencode({
    "app_config" = {
      "name" = "my_app"
      "version" = "1.0.0"
      "features" = ["auth", "api", "web"]
    }
    "deployment" = {
      "replicas" = 3
      "resources" = {
        "cpu" = "500m"
        "memory" = "1Gi"
      }
      "env_vars" = ["ENV=prod", "DEBUG=false"]
    }
    "metadata" = {
      "created_by" = "terraform"
      "managed" = true
    }
  }), "expand"))
}

# 🍲🥄🔧🪄
