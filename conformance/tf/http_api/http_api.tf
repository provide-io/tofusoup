# Minimal test to verify systemic validation fix
terraform {
  required_providers {
    pyvider = {
      source = "registry.terraform.io/provide-io/pyvider"
      version = "0.1.0"
    }
  }
}

provider "pyvider" {
  api_token = "test"
}

# Minimal HTTP API test
data "pyvider_http_api" "minimal_test" {
  url = "https://httpbin.org/get"
  method = "GET"
  headers = {
    "User-Agent" = "Terraform/Pyvider-Test"
  }
  timeout = 10
}

# Test only the attributes that exist in the minimal schema
output "minimal_test_basic" {
  value = {
    status_code = data.pyvider_http_api.minimal_test.status_code
    response_time = data.pyvider_http_api.minimal_test.response_time_ms
    header_count = data.pyvider_http_api.minimal_test.header_count
    content_type = data.pyvider_http_api.minimal_test.content_type
    has_error = data.pyvider_http_api.minimal_test.error_message != null
  }
}

# Test header access (string map)
output "minimal_test_headers" {
  value = {
    all_headers = data.pyvider_http_api.minimal_test.response_headers
    content_type_header = try(data.pyvider_http_api.minimal_test.response_headers["Content-Type"], "not_found")
    server_header = try(data.pyvider_http_api.minimal_test.response_headers["Server"], "not_found")
    header_count = data.pyvider_http_api.minimal_test.header_count
  }
}

# Test response body parsing (manual JSON parsing)
output "minimal_test_json" {
  value = {
    response_body_length = length(data.pyvider_http_api.minimal_test.response_body)
    
    # Parse JSON manually in Terraform
    parsed_response = try(
      jsondecode(data.pyvider_http_api.minimal_test.response_body),
      {}
    )
    
    # Extract specific fields from parsed JSON
    request_url = try(
      jsondecode(data.pyvider_http_api.minimal_test.response_body).url,
      "not_found"
    )
    
    user_agent_from_json = try(
      jsondecode(data.pyvider_http_api.minimal_test.response_body).headers["User-Agent"],
      "not_found"
    )
  }
}

# Test conditional logic and error handling
output "test_summary" {
  value = {
    test_status = "Minimal HTTP API test"
    success = data.pyvider_http_api.minimal_test.status_code == 200
    has_error = data.pyvider_http_api.minimal_test.error_message != null
    error_message = data.pyvider_http_api.minimal_test.error_message
    
    response_summary = {
      status_code = data.pyvider_http_api.minimal_test.status_code
      response_time_ms = data.pyvider_http_api.minimal_test.response_time_ms
      header_count = data.pyvider_http_api.minimal_test.header_count
      has_content_type = data.pyvider_http_api.minimal_test.content_type != null
    }
    
    schema_validation_result = "SUCCESS - No 'unexpected keyword argument' errors"
  }
}

# 🍲🥄🔧🪄
