# Contributing to TofuSoup

We love your input! We want to make contributing to TofuSoup as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## We Develop with Github
We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## We Use [Github Flow](https://guides.github.com/introduction/flow/index.html)
Pull requests are the best way to propose changes to the codebase:

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Any contributions you make will be under the Apache 2.0 Software License
In short, when you submit code changes, your submissions are understood to be under the same [Apache 2.0 License](LICENSE) that covers the project.

## Report bugs using Github's [issues](https://github.com/provide-io/tofusoup/issues)
We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/provide-io/tofusoup/issues/new).

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Development Process

1. Clone the repository
```bash
git clone https://github.com/provide-io/tofusoup.git
cd tofusoup
```

2. Set up your development environment
```bash
uv sync  # This sets up the virtual environment
```

3. Run tests to ensure everything works
```bash
uv run pytest
```

4. Make your changes and add tests

5. Run the test suite
```bash
uv run pytest -v
```

6. Check code style
```bash
uv run ruff check .
uv run ruff format .
uv run mypy src/
```

## Testing Philosophy

TofuSoup is a conformance testing suite, so testing is especially important:

- Write tests for all new functionality
- Ensure cross-language compatibility tests pass
- Test harness generation should work for all supported languages
- Document any language-specific behavior

## License
By contributing, you agree that your contributions will be licensed under its Apache 2.0 License.

## References
This document was adapted from the open-source contribution guidelines for [Facebook's Draft](https://github.com/facebook/draft-js/blob/master/CONTRIBUTING.md)