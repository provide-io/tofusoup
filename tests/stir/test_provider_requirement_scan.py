"""Regression tests for StirRuntime's provider-requirement scan.

The scan decides which providers the harness pre-downloads before any test runs.
A false positive there is not a single test failure -- `prepare_providers` raises
and the whole run aborts before the first `init`, so every suite is lost.

Two bugs are pinned here:

1. The scan read each .tf file on its own. Terraform merges every .tf in a
   directory into one configuration, so a `required_providers` block in
   provider.tf governs the sources used by its siblings; reading them separately
   hid that and let the legacy fallback fire on a file that was already covered.

2. The legacy-syntax pattern was unanchored, so it matched the `provider "name" {}`
   block *nested inside* a `state_store` block -- valid PSS configuration -- and
   invented a `hashicorp/<name>` requirement for a provider declared local.
"""

import asyncio
from pathlib import Path

import pytest

from tofusoup.stir.runtime import StirRuntime

LOCAL_PROVIDER_TF = """\
terraform {
  required_providers {
    pyvider = {
      source  = "local/providers/pyvider"
      version = ">= 0.0.5"
    }
  }
}

provider "pyvider" {}
"""

STATE_STORE_TF = """\
terraform {
  state_store "pyvider_filesystem_store" {
    provider "pyvider" {}

    path = "${path.module}/tfstate"
  }
}
"""


def _scan(runtime: StirRuntime, dirs: list[Path]) -> set[tuple[str, str]]:
    return asyncio.run(runtime._scan_provider_requirements(dirs))


@pytest.fixture
def runtime() -> StirRuntime:
    return StirRuntime()


def test_nested_provider_in_state_store_is_not_a_registry_requirement(
    runtime: StirRuntime, tmp_path: Path
) -> None:
    """A `provider` block inside `state_store` is PSS syntax, not a declaration."""
    (tmp_path / "provider.tf").write_text(LOCAL_PROVIDER_TF, encoding="utf-8")
    (tmp_path / "example.tf").write_text(STATE_STORE_TF, encoding="utf-8")

    assert _scan(runtime, [tmp_path]) == set()


def test_sibling_required_providers_suppresses_the_legacy_fallback(
    runtime: StirRuntime, tmp_path: Path
) -> None:
    """provider.tf declares the source; a bare block in a sibling is the same provider."""
    (tmp_path / "provider.tf").write_text(LOCAL_PROVIDER_TF, encoding="utf-8")
    (tmp_path / "main.tf").write_text('provider "pyvider" {}\n', encoding="utf-8")

    assert _scan(runtime, [tmp_path]) == set()


def test_registry_providers_are_still_collected(runtime: StirRuntime, tmp_path: Path) -> None:
    """The fix must not stop real registry sources from being pre-downloaded."""
    (tmp_path / "provider.tf").write_text(
        """\
terraform {
  required_providers {
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0.0"
    }
  }
}
""",
        encoding="utf-8",
    )

    assert _scan(runtime, [tmp_path]) == {("hashicorp/random", ">= 3.0.0")}


def test_legacy_top_level_block_without_any_source_still_falls_back(
    runtime: StirRuntime, tmp_path: Path
) -> None:
    """With nothing declaring a source, the hashicorp/ guess is the only option left."""
    (tmp_path / "main.tf").write_text('provider "random" {}\n', encoding="utf-8")

    assert _scan(runtime, [tmp_path]) == {("hashicorp/random", ">= 0.0.0")}


def test_local_sources_are_never_pre_downloaded(runtime: StirRuntime, tmp_path: Path) -> None:
    """`local/` providers come from the filesystem mirror; the registry has no such name."""
    (tmp_path / "provider.tf").write_text(LOCAL_PROVIDER_TF, encoding="utf-8")

    assert _scan(runtime, [tmp_path]) == set()


def test_a_directory_mixing_local_and_registry_keeps_only_the_registry_one(
    runtime: StirRuntime, tmp_path: Path
) -> None:
    (tmp_path / "provider.tf").write_text(
        """\
terraform {
  required_providers {
    pyvider = {
      source  = "local/providers/pyvider"
      version = ">= 0.0.5"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0.0"
    }
  }
}
""",
        encoding="utf-8",
    )

    assert _scan(runtime, [tmp_path]) == {("hashicorp/random", ">= 3.0.0")}
