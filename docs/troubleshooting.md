# Troubleshooting

Common issues and solutions when using TofuSoup.

## Installation Issues

### Command not found: soup

**Symptom**: `soup: command not found` after installation

**Solutions**:
1. Verify installation:
   ```bash
   uv pip list | grep tofusoup
   ```

2. Check Python bin is in PATH:
   ```bash
   python -m uv pip show tofusoup
   which soup
   ```

3. Try running via Python module:
   ```bash
   python -m tofusoup.cli --help
   ```

4. Add Python bin to PATH (macOS/Linux):
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

### Module import errors

**Symptom**: `ModuleNotFoundError` when running soup

**Solution**:
```bash
# For development installations
cd /path/to/tofusoup
uv sync

# For tool installations
uv tool install "tofusoup[all]"
```

## Harness Issues

### Go harness build failures

**Symptom**: `soup harness build` fails

**Solutions**:
1. Check Go installation:
   ```bash
   go version  # Should be 1.21+
   ```

2. Check GOPATH:
   ```bash
   go env GOPATH
   ```

3. Try building manually:
   ```bash
   cd src/tofusoup/harness/go/soup-go
   go build -o ../../../../harnesses/bin/soup-go
   ```

4. Check for Go module issues:
   ```bash
   go mod tidy
   go mod verify
   ```

### Harness binary not found

**Symptom**: `No such file or directory: 'harnesses/bin/soup-go'`

**Cause**: The `harnesses/bin/` directory is a build artifact and not included in version control.

**Solution**:
```bash
# Build harnesses (this creates the directory)
soup harness build --all

# Verify
ls harnesses/bin/
./harnesses/bin/soup-go --version
```

**Note**: You must build harnesses after cloning the repository or when switching branches that update harness code.

### Harness CLI verification fails

**Symptom**: `soup harness verify-cli` fails

**Solution**:
```bash
# Rebuild the harness
soup harness build soup-go

# Verify it runs
./harnesses/bin/soup-go --version

# Check logs
soup harness verify-cli soup-go --verbose
```

## Test Failures

### RPC connection timeouts

**Symptom**: Tests fail with "Connection timeout after 30s"

**Causes & Solutions**:

1. **Go server not starting**:
   ```bash
   # Check server logs
   cat /tmp/tofusoup_plugin_debug.log

   # Try starting server manually
   soup rpc server-start
   ```

2. **Firewall blocking**:
   - Check firewall settings
   - Allow Python and Go executables
   - Test on localhost without firewall

3. **Port already in use**:
   ```bash
   # Check for processes using gRPC ports
   lsof -i :50051
   ```

### Wire protocol binary mismatches

**Symptom**: "Binary mismatch for test 'X'"

**This is a real compatibility issue!** It means Python and Go are producing different binary output.

**Debug steps**:
1. View the specific test:
   ```bash
   pytest conformance/wire/souptest_wire_python_vs_go.py::test_X -vv
   ```

2. Compare binary outputs:
   ```bash
   # See wire protocol guide for debugging
   soup wire encode input.json python.out
   ./harnesses/bin/soup-go wire encode input.json go.out
   diff <(xxd python.out) <(xxd go.out)
   ```

3. Report the issue on GitHub with test details

### CTY type errors

**Symptom**: `'UnrefinedUnknownValue' object is not subscriptable`

**Solution**:
This is a known issue with unknown values. Update `pyvider-cty`:
```bash
uv add pyvider-cty
```

## Performance Issues

### Tests running slowly

**Solutions**:
1. Run tests in parallel:
   ```bash
   pytest -n auto
   ```

2. Run specific test suites:
   ```bash
   soup test cty  # Instead of 'soup test all'
   ```

3. Skip slow tests:
   ```bash
   pytest -m "not slow"
   ```

### Harness build taking too long

**Solution**:
```bash
# Use cached builds
soup harness build --cache

# Build only what's needed
soup harness build soup-go  # Instead of --all
```

## Configuration Issues

### soup.toml not found

**Symptom**: "Configuration not loaded" warnings

**Solution**:
TofuSoup searches for `soup.toml` in:
1. Path specified by `--config-file`
2. Current directory (`./soup.toml`)

Create one if needed:
```bash
cat > soup.toml <<EOF
[global_settings]
default_python_log_level = "INFO"
EOF
```

### Invalid configuration

**Symptom**: `TofuSoupConfigError`

**Solution**:
```bash
# Validate syntax
python -c "import tomllib; tomllib.load(open('soup.toml', 'rb'))"

# Check configuration
soup config show
```

## Matrix Testing Issues

### Matrix testing not available

**Symptom**: `Error: Matrix testing requires the 'wrknv' package`

**Cause**: Matrix testing is an optional feature that requires `wrknv`.

**Solution**:
```bash
# Install wrknv from local source
uv tool install /path/to/wrknv

# Or from PyPI
uv tool install wrknv
```

**Note**: Regular `soup stir` (without `--matrix`) works without this dependency.

### stir command not finding tests

**Symptom**: "No tests found"

**Solutions**:
1. Check directory structure:
   ```bash
   ls -la tests/
   ```

2. Verify test files have `main.tf`:
   ```bash
   find tests/ -name "main.tf"
   ```

3. Use correct path:
   ```bash
   soup stir tests/  # Not just 'tests'
   ```

### Matrix versions not working

**Symptom**: Tests only run against one version

**Solution**:
Configure matrix in `soup.toml`:
```toml
[workenv.matrix.versions]
terraform = ["1.5.7", "1.6.0"]
tofu = ["1.8.0"]
```

Then use `--matrix` flag:
```bash
soup stir tests/ --matrix
```

## Getting More Help

### Enable debug logging

```bash
# CLI debug mode
soup --log-level DEBUG command

# Python logging
export TOFUSOUP_LOG_LEVEL=DEBUG
soup command
```

### Check logs

```bash
# Plugin debug log
cat /tmp/tofusoup_plugin_debug.log

# Test output
soup/output/cli_verification/
```

### Report Issues

If you can't resolve the issue:

1. Check [FAQ](faq/)
2. Search [GitHub Issues](https://github.com/provide-io/tofusoup/issues)
3. Create a new issue with:
   - TofuSoup version (`soup --version`)
   - Python version (`python --version`)
   - Go version (`go version`)
   - Full error message
   - Steps to reproduce

## See Also

- [FAQ](faq/)
- [Installation Guide](getting-started/installation/)
- [Configuration Reference](reference/configuration/)
