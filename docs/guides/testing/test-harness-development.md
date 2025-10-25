# Guide: Managing Language-Specific CLIs

The `soup harness` command is used to manage the lifecycle of language-specific implementations of the TofuSoup CLI, such as `soup-go`. These binaries provide feature parity with the main Python CLI and serve as the canonical reference for conformance tests.

## Listing CLIs

To see a list of available language-specific CLIs and their current build status, use the `list` command.

```bash
soup harness list
```
This will display a table showing each CLI, its expected binary path, and whether it is currently built.

## Building CLIs

The `build` command compiles the source code for the language-specific CLIs and places the executables in a standardized location (`tofusoup/src/tofusoup/harness/go/bin/`).

```bash
# Build all available CLIs
soup harness build --all

# Build a specific CLI, for example soup-go
soup harness build soup-go

# Force a rebuild even if the binary already exists
soup harness build soup-go --force-rebuild
```

Build behavior, such as Go build flags and environment variables, can be customized in `soup.toml`.

## Verifying CLIs

After building, you can run a basic verification check to ensure the CLI is functional.

```bash
soup harness verify-cli soup-go
```

## Cleaning CLIs

The `clean` command removes the compiled binary artifacts for one or more CLIs.

```bash
# Clean a specific CLI
soup harness clean soup-go

# Clean all built CLIs
soup harness clean --all
```
