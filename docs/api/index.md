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