---
page_title: "Data Source: tofusoup_provider_info"
description: |-
  Query provider details from Terraform or OpenTofu registry
---
# tofusoup_provider_info (Data Source)

Query provider details from Terraform or OpenTofu registry.

Returns detailed information about a specific provider including its latest version,
description, source URL, download count, and publication date.

## Example Usage

```terraform
# Query AWS provider information from Terraform registry
data "tofusoup_provider_info" "aws" {
  namespace = "hashicorp"
  name      = "aws"
  registry  = "terraform"
}

# Query Google provider information from Terraform registry
data "tofusoup_provider_info" "google" {
  namespace = "hashicorp"
  name      = "google"
  registry  = "terraform"
}

output "aws_latest_version" {
  description = "Latest version of the AWS provider"
  value       = data.tofusoup_provider_info.aws.latest_version
}

output "aws_downloads" {
  description = "Total downloads of the AWS provider"
  value       = data.tofusoup_provider_info.aws.downloads
}

output "google_source_url" {
  description = "Source URL for the Google provider"
  value       = data.tofusoup_provider_info.google.source_url
}

```

## Argument Reference



## Related Components

- `tofusoup_provider_versions` (Data Source) - Query all versions of a provider
- `tofusoup_module_info` (Data Source) - Query module details from registry