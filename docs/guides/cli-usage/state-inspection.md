# Guide: Terraform State Inspection

TofuSoup provides tools for inspecting Terraform state files, including support for decrypting private state data stored by Pyvider providers.

## What is Private State?

Terraform providers can store sensitive data in "private state" - encrypted attributes that aren't visible in regular Terraform state inspection tools. Pyvider providers use this feature to securely store credentials, tokens, and other sensitive data.

TofuSoup's `soup state` commands can decrypt and display this private state data when you have the appropriate decryption key.

## Prerequisites

To decrypt private state, you need:

1. **Shared Secret**: Set via environment variable
   ```bash
   export PYVIDER_PRIVATE_STATE_SHARED_SECRET="your-secret-key"
   ```

2. **State File**: A Terraform state file (typically `terraform.tfstate`)

## Commands

### Show State Overview

Display an overview of all resources in a state file:

```bash
soup state show
```

By default, this reads `terraform.tfstate` in the current directory.

You can specify a different state file:

```bash
soup state show path/to/terraform.tfstate
```

### Show Only Resources with Private State

Filter to only resources that contain private state:

```bash
soup state show --private-only
```

### Show Specific Resource

Display detailed information about a specific resource:

```bash
soup state show --resource pyvider_timed_token.example
```

Format: `<resource_type>.<resource_name>`

### Include Encrypted Data

Show both decrypted and encrypted versions of private state:

```bash
soup state show --show-encrypted
```

This is useful for debugging encryption issues or verifying that decryption is working correctly.

## Decrypting Individual Values

Decrypt a single base64-encoded private state string:

```bash
soup state decrypt "PaDuMfrlCnnhZsKb..."
```

### Output Formats

```bash
# JSON output (default)
soup state decrypt "PaDuMfrlCnnhZsKb..." --format json

# Raw output
soup state decrypt "PaDuMfrlCnnhZsKb..." --format raw
```

## Validating State File

Check that all private state in a state file can be successfully decrypted:

```bash
soup state validate
soup state validate path/to/terraform.tfstate
```

This command:
- Scans all resources in the state file
- Attempts to decrypt any private state data
- Reports any decryption failures
- Returns exit code 0 if all validations pass

## Example Workflow

### 1. Set Your Shared Secret

```bash
export PYVIDER_PRIVATE_STATE_SHARED_SECRET="$(cat .secrets/private-state-key)"
```

### 2. View State Overview

```bash
soup state show
```

Output:
```
📋 Terraform State: terraform.tfstate

Resources with Private State:
├── pyvider_timed_token.api_token
├── pyvider_credential.database
└── pyvider_secret.api_key

Total Resources: 15
Resources with Private State: 3
```

### 3. Inspect Specific Resource

```bash
soup state show --resource pyvider_timed_token.api_token
```

Output:
```
🔍 Resource: pyvider_timed_token.api_token

Public Attributes:
├── id: "token-12345"
├── expiry: "2025-12-31T23:59:59Z"
└── created_at: "2025-01-01T00:00:00Z"

Private State (Decrypted):
├── token_value: "sk-proj-abc123..."
├── refresh_token: "rt-xyz789..."
└── encryption_metadata:
    ├── algorithm: "AES-256-GCM"
    └── key_id: "key-001"
```

### 4. Validate All Private State

```bash
soup state validate
```

Output:
```
✅ All private state validated successfully
- pyvider_timed_token.api_token: OK
- pyvider_credential.database: OK
- pyvider_secret.api_key: OK
```

## Common Use Cases

### Debugging Provider Issues

When troubleshooting provider problems, inspect the state to verify what's stored:

```bash
# See all private state
soup state show --private-only

# Check specific resource
soup state show --resource pyvider_credential.db_creds
```

### Rotating Encryption Keys

When rotating private state encryption keys:

```bash
# Validate with old key
export PYVIDER_PRIVATE_STATE_SHARED_SECRET="old-key"
soup state validate

# After rotation, validate with new key
export PYVIDER_PRIVATE_STATE_SHARED_SECRET="new-key"
soup state validate
```

### CI/CD State Verification

In CI/CD pipelines, verify state file integrity:

```bash
#!/bin/bash
set -e

# Load secret from CI secrets
export PYVIDER_PRIVATE_STATE_SHARED_SECRET="$CI_PRIVATE_STATE_KEY"

# Validate state
soup state validate terraform.tfstate

# Show summary
soup state show --private-only
```

### Manual Decryption

Decrypt individual values from logs or debug output:

```bash
# From provider logs
soup state decrypt "eyJhbGciOiJkaXIi..."

# Save to file
soup state decrypt "eyJhbGciOiJkaXIi..." --format raw > decrypted.txt
```

## Troubleshooting

### Missing Shared Secret

**Error**: `PYVIDER_PRIVATE_STATE_SHARED_SECRET not set`

**Solution**:
```bash
export PYVIDER_PRIVATE_STATE_SHARED_SECRET="your-key"
```

### Decryption Failure

**Error**: `Failed to decrypt private state`

**Possible causes**:
1. Wrong shared secret
2. Corrupted encrypted data
3. Incompatible encryption version

**Debug steps**:
```bash
# Try showing encrypted data
soup state show --show-encrypted

# Validate state file
soup state validate

# Check provider logs
terraform plan
```

### State File Not Found

**Error**: `State file not found: terraform.tfstate`

**Solution**:
```bash
# Specify full path
soup state show /path/to/terraform.tfstate

# Or change directory
cd /path/to/terraform/project
soup state show
```

## Security Considerations

1. **Protect Your Shared Secret**: Never commit `PYVIDER_PRIVATE_STATE_SHARED_SECRET` to version control

2. **Secure State Files**: Terraform state files contain sensitive data, even without private state

3. **Use Remote State**: Consider using remote state backends with encryption at rest

4. **Rotate Keys Regularly**: Periodically rotate your private state encryption keys

5. **Limit Access**: Restrict who can decrypt private state in production environments

## Integration with Terraform

TofuSoup's state inspection works alongside standard Terraform commands:

```bash
# Standard Terraform state inspection
terraform state list
terraform state show pyvider_timed_token.example

# TofuSoup private state inspection
soup state show --resource pyvider_timed_token.example
```

Use `terraform state` for public attributes and `soup state` for private state data.

## See Also

- [Pyvider Documentation](https://github.com/provide-io/pyvider) - Provider framework with private state support
- [Terraform State](https://www.terraform.io/docs/language/state/index.html) - Official Terraform state documentation
- [Troubleshooting](../../troubleshooting.md) - Common issues and solutions
