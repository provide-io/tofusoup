# TofuSoup API Reference

This page provides auto-generated API documentation for the `tofusoup` Python package.

## Using TofuSoup as a Library

While TofuSoup is primarily a CLI tool, you can also use its components programmatically:

```python
# CTY operations
from tofusoup.cty.logic import convert_cty_file, view_cty_file

# HCL operations
from tofusoup.hcl.logic import parse_hcl_file, convert_hcl_file

# Wire protocol operations
from tofusoup.wire.logic import encode_wire, decode_wire

# Configuration
from tofusoup.common.config import load_tofusoup_config
```

## Quick Examples

### CTY Operations

Convert CTY files between formats:

```python
from pathlib import Path
from tofusoup.cty.logic import convert_cty_file

# Convert JSON to MessagePack
success = convert_cty_file(
    input_path=Path("data.json"),
    output_path=Path("data.msgpack"),
    input_format="json",
    output_format="msgpack"
)

if success:
    print("Conversion successful!")
```

View CTY structure:

```python
from pathlib import Path
from tofusoup.cty.logic import view_cty_file

# Display CTY structure as rich tree
view_cty_file(
    file_path=Path("data.json"),
    file_format="json"
)
```

### HCL Operations

Parse HCL files:

```python
from pathlib import Path
from tofusoup.hcl.logic import parse_hcl_file

# Parse HCL file and get CTY representation
cty_value = parse_hcl_file(Path("main.tf"))
print(f"Parsed HCL: {cty_value}")
```

Convert HCL to other formats:

```python
from pathlib import Path
from tofusoup.hcl.logic import convert_hcl_file

# Convert HCL to JSON
convert_hcl_file(
    input_path=Path("config.hcl"),
    output_path=Path("config.json"),
    output_format="json"
)
```

### Wire Protocol

Encode and decode wire protocol messages:

```python
from pathlib import Path
from tofusoup.wire.logic import encode_wire, decode_wire

# Encode JSON to wire format
encode_wire(
    input_json_path=Path("value.json"),
    output_tfw_b64_path=Path("value.tfw.b64")
)

# Decode wire format to JSON
decode_wire(
    input_tfw_b64_path=Path("value.tfw.b64"),
    output_json_path=Path("decoded.json")
)
```

### Configuration

Load TofuSoup configuration:

```python
from pathlib import Path
from tofusoup.common.config import load_tofusoup_config

# Load from project root
config = load_tofusoup_config(
    project_root=Path.cwd(),
    explicit_config_file=None
)

# Access configuration
log_level = config.get("global_settings", {}).get("default_python_log_level", "INFO")
print(f"Log level: {log_level}")
```

## Common Integration Patterns

### Validation Pipeline

Build a validation pipeline using TofuSoup components:

```python
from pathlib import Path
from tofusoup.cty.logic import convert_cty_file
from tofusoup.wire.logic import encode_wire, decode_wire

def validate_cty_roundtrip(input_file: Path) -> bool:
    """Validate CTY data through full encode/decode cycle."""
    temp_msgpack = Path("temp.msgpack")
    temp_wire = Path("temp.tfw.b64")
    temp_decoded = Path("temp_decoded.json")

    try:
        # Convert to msgpack
        convert_cty_file(input_file, temp_msgpack, "json", "msgpack")

        # Encode to wire format
        encode_wire(input_file, temp_wire)

        # Decode back
        decode_wire(temp_wire, temp_decoded)

        return True
    except Exception as e:
        print(f"Validation failed: {e}")
        return False
    finally:
        # Cleanup
        for f in [temp_msgpack, temp_wire, temp_decoded]:
            if f.exists():
                f.unlink()
```

### Custom Test Harness

Use TofuSoup components to build custom test harnesses:

```python
from pathlib import Path
from tofusoup.common.config import load_tofusoup_config
from tofusoup.cty.logic import convert_cty_file

class CustomTestHarness:
    def __init__(self, config_path: Path):
        self.config = load_tofusoup_config(config_path.parent)
        self.test_data_dir = config_path.parent / "test_data"

    def run_conversion_tests(self):
        """Run all CTY conversion tests."""
        test_files = self.test_data_dir.glob("*.json")

        for test_file in test_files:
            output_file = test_file.with_suffix(".msgpack")
            success = convert_cty_file(
                test_file,
                output_file,
                "json",
                "msgpack"
            )
            print(f"Test {test_file.name}: {'PASS' if success else 'FAIL'}")

# Usage
harness = CustomTestHarness(Path("soup.toml"))
harness.run_conversion_tests()
```

### Batch Processing

Process multiple files with TofuSoup:

```python
from pathlib import Path
from tofusoup.hcl.logic import convert_hcl_file

def batch_convert_hcl(source_dir: Path, output_dir: Path):
    """Convert all HCL files in a directory to JSON."""
    output_dir.mkdir(exist_ok=True)

    for hcl_file in source_dir.glob("**/*.hcl"):
        output_file = output_dir / hcl_file.relative_to(source_dir).with_suffix(".json")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            convert_hcl_file(hcl_file, output_file, "json")
            print(f"✓ Converted {hcl_file.name}")
        except Exception as e:
            print(f"✗ Failed {hcl_file.name}: {e}")

# Usage
batch_convert_hcl(Path("terraform_configs"), Path("converted_json"))
```

## Error Handling

TofuSoup components raise exceptions for errors. Always wrap calls in try-except blocks:

```python
from pathlib import Path
from tofusoup.cty.logic import convert_cty_file
from tofusoup.common.exceptions import TofuSoupError

try:
    convert_cty_file(
        Path("input.json"),
        Path("output.msgpack"),
        "json",
        "msgpack"
    )
except TofuSoupError as e:
    print(f"TofuSoup error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Logging

TofuSoup uses structured logging via `provide.foundation`:

```python
from provide.foundation import logger

# TofuSoup functions log automatically
from tofusoup.cty.logic import convert_cty_file

# Configure logging if needed
import logging
logging.basicConfig(level=logging.DEBUG)

# Now CTY operations will log debug information
convert_cty_file(...)
```

## Module Documentation

::: tofusoup
    options:
      show_root_heading: true
      members_order: source
      show_signature_annotations: true
      show_category_heading: true
      show_bases: true
      merge_init_into_class: true
      separate_signature: true
      show_if_no_docstring: false
      heading_level: 2
      filters:
        - "!^_"