from __future__ import annotations

import pytest

from lorp_fsd.experiment_config import ExperimentConfig, SelectedDepot


def _cfg(**kw):
    base = dict(name="r40x5a-1.dat", F_R=1.0, F_A=0.0, R=30.0, Length=100.0)
    base.update(kw)
    return ExperimentConfig(**base)


def test_defaults_problem_id_zero_ok():
    cfg = _cfg()
    assert cfg.problem_id == 0
    assert cfg.original == 0
    assert cfg.VFX == 1


def test_unsupported_problem_id_raises():
    with pytest.raises(NotImplementedError):
        _cfg(problem_id=1)
    with pytest.raises(NotImplementedError):
        _cfg(problem_id=2)


def test_active_depot_ids_sorted():
    cfg = _cfg(
        selected_depots={
            5: SelectedDepot(5, 1, 875.0),
            1: SelectedDepot(1, 1, 875.0),
            3: SelectedDepot(3, 1, 875.0),
        }
    )
    assert cfg.active_depot_ids == (1, 3, 5)
