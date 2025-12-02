"""Memory profiling tests for wire serialization (JSON/msgpack)."""

import pytest
from wrknv.memray.runner import run_memray_stress

pytestmark = [pytest.mark.memray, pytest.mark.slow]


def test_wire_serialization_allocations(memray_output_dir, memray_baseline, memray_baselines_path) -> None:
    """Profile memory allocations in wire serialization hot path."""
    run_memray_stress(
        script="scripts/memray/memray_wire_stress.py",
        baseline_key="wire_serialization_total_allocations",
        output_dir=memray_output_dir,
        baselines=memray_baseline,
        baselines_path=memray_baselines_path,
    )
