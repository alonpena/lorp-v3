from __future__ import annotations

import pandas as pd
import pytest

from xlsx_loader import (
    DepotSlot,
    _extract_depot_slots,
    _maybe_num,
    _maybe_str,
    _row_to_depots,
    infer_sheet_spec,
    load_lorp_fsd_mapping,
    normalize_sheet,
    sheet_to_records,
    workbook_sheets,
    SheetResult,
)


# ── infer_sheet_spec ──────────────────────────────────────────────────────────

def test_spec_lorp_fsd():
    s = infer_sheet_spec("LoRP-FSD")
    assert s["kind"] == "lorp-fsd"
    assert s["depot_slots"] == 4
    assert s["has_size"] is True


def test_spec_lorp_fixedcost():
    s = infer_sheet_spec("LoRP+FixedCost")
    assert s["kind"] == "lorp-fixedcost"
    assert s["depot_slots"] == 5


def test_spec_itor():
    s = infer_sheet_spec("LRP_ITOR")
    assert s["kind"] == "itor"
    assert s["depot_slots"] == 5
    assert s["has_size"] is True


def test_spec_unknown():
    s = infer_sheet_spec("SomethingRandom")
    assert s["kind"] == "unknown"
    assert s["depot_slots"] == 0


# ── _maybe_num ────────────────────────────────────────────────────────────────

def test_maybe_num_nan():
    assert _maybe_num(float("nan")) is None


def test_maybe_num_pd_na():
    assert _maybe_num(pd.NA) is None


def test_maybe_num_valid_float():
    assert _maybe_num(3.14) == pytest.approx(3.14)


def test_maybe_num_int_string():
    assert _maybe_num("42") == 42.0


def test_maybe_num_non_numeric_string():
    assert _maybe_num("abc") is None


# ── _maybe_str ────────────────────────────────────────────────────────────────

def test_maybe_str_nan():
    assert _maybe_str(float("nan")) is None


def test_maybe_str_pd_na():
    assert _maybe_str(pd.NA) is None


def test_maybe_str_empty_whitespace():
    assert _maybe_str("   ") is None


def test_maybe_str_valid():
    assert _maybe_str("  d1  ") == "d1"


# ── _row_to_depots ────────────────────────────────────────────────────────────

def _depot_row(**kwargs):
    defaults = {
        "Depot1": "d1", "CapD1": 200.0,
        "DemandD1": 80.0, "%UsageD1": 0.4, "VehiclesD1": 2.0,
        "Depot2": "d2", "CapD2": 150.0,
        "DemandD2": 60.0, "%UsageD2": 0.4, "VehiclesD2": 1.0,
        "Depot3": float("nan"), "CapD3": float("nan"),
        "Depot4": float("nan"), "CapD4": float("nan"),
    }
    defaults.update(kwargs)
    return pd.Series(defaults)


def test_row_to_depots_two_depots():
    row = _depot_row()
    depots, depots_milp = _row_to_depots(row, row.index)
    assert set(depots.keys()) == {1, 2}


def test_row_to_depots_capacity_values():
    row = _depot_row()
    depots, _ = _row_to_depots(row, row.index)
    assert depots[1]["capacity"] == 200.0
    assert depots[2]["capacity"] == 150.0


def test_row_to_depots_milp_demand():
    row = _depot_row()
    _, depots_milp = _row_to_depots(row, row.index)
    assert depots_milp[1]["demand"] == 80.0
    assert depots_milp[2]["demand"] == 60.0


def test_row_to_depots_nan_depot_skipped():
    row = _depot_row()
    depots, _ = _row_to_depots(row, row.index)
    assert 3 not in depots and 4 not in depots


def test_row_to_depots_missing_cap_col():
    row = _depot_row()
    row = row.drop("CapD1")
    depots, _ = _row_to_depots(row, row.index)
    assert depots[1]["capacity"] is None


# ── normalize_sheet ───────────────────────────────────────────────────────────

def test_normalize_strips_column_whitespace():
    df = pd.DataFrame({"  name  ": ["test"], "  F_R  ": [1.0]})
    result = normalize_sheet(df, "LoRP-FSD")
    assert "name" in result.columns
    assert "F_R" in result.columns


def test_normalize_attaches_sheet_spec():
    df = pd.DataFrame({"name": ["test"]})
    result = normalize_sheet(df, "LoRP-FSD")
    assert result.attrs.get("spec", {}).get("kind") == "lorp-fsd"


def test_normalize_attaches_depot_slots_attr():
    df = pd.DataFrame({
        "Depot1": ["d1"], "CapD1": [200.0],
        "DemandD1": [80.0], "%UsageD1": [0.4], "VehiclesD1": [2.0],
    })
    result = normalize_sheet(df, "LoRP-FSD")
    assert "depot_slots" in result.attrs


# ── sheet_to_records ──────────────────────────────────────────────────────────

def test_sheet_to_records_row_count():
    df = normalize_sheet(pd.DataFrame({"name": ["a", "b"]}), "LoRP-FSD")
    records = sheet_to_records(SheetResult(sheet_name="LoRP-FSD", raw=df, data=df))
    assert len(records) == 2


def test_sheet_to_records_has_row_index():
    df = normalize_sheet(pd.DataFrame({"name": ["a"]}), "LoRP-FSD")
    records = sheet_to_records(SheetResult(sheet_name="LoRP-FSD", raw=df, data=df))
    assert "_row_index" in records[0]


# ── integration (requires results_MILP.xlsx) ─────────────────────────────────

XLSX_PATH = "results_MILP.xlsx"
INST_FOLDER = "instances"


@pytest.mark.integration
def test_load_lorp_fsd_mapping_row_count():
    df = load_lorp_fsd_mapping(XLSX_PATH, instance_folder=INST_FOLDER)
    assert len(df) > 0


@pytest.mark.integration
def test_load_lorp_fsd_mapping_required_columns():
    df = load_lorp_fsd_mapping(XLSX_PATH, instance_folder=INST_FOLDER)
    for col in ("instance", "F_R", "F_A", "R", "UB", "depots", "depots_milp"):
        assert col in df.columns, f"missing column: {col}"


@pytest.mark.integration
def test_load_lorp_fsd_mapping_depots_dict_per_row():
    df = load_lorp_fsd_mapping(XLSX_PATH, instance_folder=INST_FOLDER)
    for _, row in df.head(5).iterrows():
        assert isinstance(row["depots"], dict)


@pytest.mark.integration
def test_load_lorp_fsd_mapping_missing_required_col(monkeypatch):
    import xlsx_loader

    def _fake_read(path, sheet_name=None):
        return pd.DataFrame({"name": ["test.dat"]})  # missing required cols

    monkeypatch.setattr(xlsx_loader.pd, "read_excel", _fake_read)
    with pytest.raises(KeyError, match="Missing required columns"):
        load_lorp_fsd_mapping(XLSX_PATH)
