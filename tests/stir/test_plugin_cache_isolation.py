"""Each example gets its own Terraform plugin cache.

`MAX_CONCURRENT_TESTS` defaults to `os.cpu_count()`, so on a 4-CPU runner four
examples run `terraform init` at the same moment. Every one of them installs the
provider under test, and they all installed it into a single shared directory --
`~/.tofusoup/plugin-cache`.

On POSIX a concurrent install is survivable: a file can be replaced while another
process holds it open. Windows refuses, and the losers die inside
`providercache.Dir.InstallPackage`. A conformance run on windows_amd64 showed
exactly that shape: four examples started within 3ms of each other, three were
dead 84ms later having produced no output at all, and the wave that followed --
running alone -- passed.

`prepare_providers` looks like it should have covered this, but it skips any
source beginning with `local/`, and the provider under test is
`local/providers/tofusoup`. Pre-warming covered every provider except the one
every example installs.

Giving each example its own cache directory removes the shared write entirely.
"""

from pathlib import Path

from tofusoup.stir.runtime import StirRuntime


def _env_for(runtime: StirRuntime, example: Path) -> dict[str, str]:
    return runtime.get_terraform_env({}, example_dir=example)


def test_two_examples_never_share_a_plugin_cache(tmp_path: Path) -> None:
    """The whole point: concurrent inits must not write the same directory."""
    runtime = StirRuntime(plugin_cache_dir=tmp_path / "shared")
    first = tmp_path / "module_search"
    second = tmp_path / "module_versions"
    first.mkdir()
    second.mkdir()

    one = _env_for(runtime, first)["TF_PLUGIN_CACHE_DIR"]
    two = _env_for(runtime, second)["TF_PLUGIN_CACHE_DIR"]

    assert one != two


def test_the_cache_lives_under_the_example_soup_dir(tmp_path: Path) -> None:
    """Alongside tfdata and logs, so it is gitignored and cleaned with `.soup`."""
    runtime = StirRuntime(plugin_cache_dir=tmp_path / "shared")
    example = tmp_path / "provider_info"
    example.mkdir()

    cache = Path(_env_for(runtime, example)["TF_PLUGIN_CACHE_DIR"])

    assert cache.parent == example / ".soup"


def test_the_cache_directory_exists_before_terraform_runs(tmp_path: Path) -> None:
    """Terraform silently ignores TF_PLUGIN_CACHE_DIR if it does not exist."""
    runtime = StirRuntime(plugin_cache_dir=tmp_path / "shared")
    example = tmp_path / "module_info"
    example.mkdir()

    cache = Path(_env_for(runtime, example)["TF_PLUGIN_CACHE_DIR"])

    assert cache.is_dir()


def test_the_lock_file_escape_hatch_is_still_set(tmp_path: Path) -> None:
    """A per-example cache is still a cache; the same caveat applies."""
    runtime = StirRuntime(plugin_cache_dir=tmp_path / "shared")
    example = tmp_path / "registry_search"
    example.mkdir()

    env = _env_for(runtime, example)

    assert env["TF_PLUGIN_CACHE_MAY_BREAK_DEPENDENCY_LOCK_FILE"] == "1"


def test_provider_preparation_still_uses_the_shared_cache(tmp_path: Path) -> None:
    """`prepare_providers` downloads once, for every example, on purpose.

    It runs before any test starts, so nothing is racing it.
    """
    shared = tmp_path / "shared"
    shared.mkdir()
    runtime = StirRuntime(plugin_cache_dir=shared)

    env = runtime.get_terraform_env({})

    assert env["TF_PLUGIN_CACHE_DIR"] == str(shared)


# 🥣🔬🔚
