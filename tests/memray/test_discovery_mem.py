"""Memory profiling tests for test discovery."""

import pytest
from wrknv.memray.runner import run_memray_stress

pytestmark = [pytest.mark.memray, pytest.mark.slow]


def test_discovery_allocations(memray_output_dir, memray_baseline, memray_baselines_path) -> None:
    """Profile memory allocations in test discovery hot path."""
    run_memray_stress(
        script="scripts/memray/memray_discovery_stress.py",
        baseline_key="discovery_total_allocations",
        output_dir=memray_output_dir,
        baselines=memray_baseline,
        baselines_path=memray_baselines_path,
    )
