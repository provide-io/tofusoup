#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import asyncio
import sys

import click
from provide.foundation import logger

from tofusoup.common.exceptions import TofuSoupError

from .logic import (
    TEST_SUITE_CONFIG,
    run_all_test_suites,
    run_test_suite,
)


def _print_results_report(results: list) -> None:
    """Prints a summary table and detailed failure report."""
    pass


@click.group("test")
@click.pass_context
def test_cli(ctx: click.Context) -> None:
    """A unified command to execute various conformance test suites."""
    if not ctx.obj:
        ctx.obj = {}


@test_cli.command("all")
@click.pass_context
def test_all_command(ctx: click.Context) -> None:
    """Runs all available conformance test suites (CTY, RPC, Wire, etc.)."""
    verbose = ctx.obj.get("VERBOSE", False)
    project_root = ctx.obj.get("PROJECT_ROOT")
    if not project_root:
        logger.error("Could not determine project root from context.")
        sys.exit(1)

    try:
        loaded_config = ctx.obj.get("TOFUSOUP_CONFIG", {})
        asyncio.run(run_all_test_suites(project_root, loaded_config, verbose))

    except TofuSoupError as e:
        logger.error(f"Error running all test suites: {e}", exc_info=verbose)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error running all test suites: {e}", exc_info=verbose)
        sys.exit(1)


# Dynamically create subcommands for each test suite
for suite_name_key in TEST_SUITE_CONFIG:
    suite_config_data = TEST_SUITE_CONFIG[suite_name_key]

    @test_cli.command(
        name=suite_name_key,
        help=f"Runs the {suite_config_data['description']}. Pass additional options after -- for pytest.",
        context_settings=dict(ignore_unknown_options=True),
    )
    @click.argument("pytest_options", nargs=-1, type=click.UNPROCESSED)
    @click.pass_context
    def _suite_command(ctx: click.Context, pytest_options: tuple[str, ...], snk: str = suite_name_key) -> None:
        verbose = ctx.obj.get("VERBOSE", False)
        project_root = ctx.obj.get("PROJECT_ROOT")
        if not project_root:
            logger.error("Could not determine project root from context.")
            sys.exit(1)

        try:
            loaded_config = ctx.obj.get("TOFUSOUP_CONFIG", {})
            asyncio.run(run_test_suite(snk, project_root, loaded_config, verbose, list(pytest_options)))
        except TofuSoupError as e:
            logger.error(f"Error running test suite '{snk}': {e}", exc_info=verbose)
            sys.exit(1)
        except Exception as e:
            logger.error(f"Unexpected error in test suite '{snk}': {e}", exc_info=verbose)
            sys.exit(1)

# 🥣🔬🔚
