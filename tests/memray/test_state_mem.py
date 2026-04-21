"""Memory profiling tests for Terraform state parsing."""

import pytest
from wrknv.memray.runner import run_memray_stress

pytestmark = [pytest.mark.memray, pytest.mark.slow]


def test_state_parsing_allocations(memray_output_dir, memray_baseline, memray_baselines_path):
    """Profile memory allocations in state parsing hot path."""
    run_memray_stress(
        script="scripts/memray/memray_state_stress.py",
        baseline_key="state_parsing_total_allocations",
        output_dir=memray_output_dir,
        baselines=memray_baseline,
        baselines_path=memray_baselines_path,
    )
