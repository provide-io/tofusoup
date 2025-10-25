# API Documentation

This directory is reserved for detailed API documentation.

## Current API Documentation

API reference documentation is available at:

- **[API Reference](../reference/api/index.md)** - Auto-generated API documentation using mkdocstrings

## Using TofuSoup as a Library

While TofuSoup is primarily a CLI tool, you can use its components programmatically:

```python
from tofusoup.cty.logic import convert_cty_file, view_cty_file
from tofusoup.hcl.logic import parse_hcl_file, convert_hcl_file
from tofusoup.wire.logic import encode_wire, decode_wire
from tofusoup.common.config import load_tofusoup_config
```

See the [API Reference](../reference/api/index.md) for complete module documentation.

## Planned Content

We plan to add:
- Detailed module-by-module API guides
- Integration patterns and best practices
- Library usage examples
- Advanced customization guides

## Contributing

Want to help improve API documentation? See CONTRIBUTING.md in the project root or visit the [GitHub repository](https://github.com/provide-io/tofusoup).
