from __future__ import annotations

import math
import textwrap

import pytest

from dat_loader import Instance, list_dat_files, load_dat, load_dat_folder, load_dat_path
from tests.conftest import MINIMAL_DAT, MINIMAL_DAT_WITH_COLA


# ── parse: structural counts ─────────────────────────────────────────────────

def test_parse_depot_count(minimal_instance):
    assert len(minimal_instance.depots) == 2


def test_parse_client_count(minimal_instance):
    assert len(minimal_instance.clients) == 3


def test_parse_n_clients_in_data(minimal_instance):
    assert minimal_instance.data["n_clients"] == 3


def test_parse_n_depots_in_data(minimal_instance):
    assert minimal_instance.data["n_depots"] == 2


def test_parse_max_depots_open(minimal_instance):
    assert minimal_instance.data["max_depots_open"] == 2


def test_parse_n_veh(minimal_instance):
    assert minimal_instance.data["n_veh"] == 4


# ── parse: coords ────────────────────────────────────────────────────────────

def test_depot1_coords(minimal_instance):
    d = minimal_instance.depots[1]
    assert d["x"] == 0.0 and d["y"] == 0.0


def test_depot2_coords(minimal_instance):
    d = minimal_instance.depots[2]
    assert d["x"] == 10.0 and d["y"] == 0.0


def test_client1_coords(minimal_instance):
    c = minimal_instance.clients[1]
    assert c["x"] == 0.0 and c["y"] == 5.0


# ── parse: scalar fields ─────────────────────────────────────────────────────

def test_vehicle_cap(minimal_instance):
    assert minimal_instance.data["veh_cap"] == 10


def test_veh_fixed_cost(minimal_instance):
    assert minimal_instance.data["veh_fixed_cost"] == 20.0


def test_depot1_capacity(minimal_instance):
    assert minimal_instance.depots[1]["cap"] == 200


def test_depot2_capacity(minimal_instance):
    assert minimal_instance.depots[2]["cap"] == 150


def test_client_demands(minimal_instance):
    assert minimal_instance.clients[1]["demand"] == 6
    assert minimal_instance.clients[2]["demand"] == 5
    assert minimal_instance.clients[3]["demand"] == 4


def test_depot1_fixed_cost(minimal_instance):
    assert minimal_instance.depots[1]["fixed_cost"] == 100.0


def test_depot2_fixed_cost(minimal_instance):
    assert minimal_instance.depots[2]["fixed_cost"] == 50.0


# ── parse: cola ───────────────────────────────────────────────────────────────

def test_cola_absent(minimal_instance):
    assert minimal_instance.data["cola"] is None


def test_cola_present():
    inst = Instance.from_dat(MINIMAL_DAT_WITH_COLA.splitlines())
    assert inst.data["cola"] == 99


# ── parse: index keys are 1-based ints ───────────────────────────────────────

def test_depot_keys_one_based(minimal_instance):
    assert set(minimal_instance.depots.keys()) == {1, 2}


def test_client_keys_one_based(minimal_instance):
    assert set(minimal_instance.clients.keys()) == {1, 2, 3}


# ── guards ────────────────────────────────────────────────────────────────────

def test_invalid_vehicle_cap_zero():
    bad = MINIMAL_DAT.replace("\n10\n", "\n0\n")
    with pytest.raises(ValueError, match="vehicle capacity"):
        Instance.from_dat(bad.splitlines())


def test_invalid_max_depots_open_exceeds_n_depots():
    # set max_depots_open=5 but n_depots=2
    lines = MINIMAL_DAT.splitlines()
    lines[2] = "5"
    with pytest.raises(ValueError, match="max_depots_open"):
        Instance.from_dat(lines)


def test_eof_truncated_depot_coords():
    truncated = "\n".join(MINIMAL_DAT.splitlines()[:5])  # cut after header
    with pytest.raises((ValueError, IndexError)):
        Instance.from_dat(truncated.splitlines())


def test_bad_coord_single_number():
    bad = MINIMAL_DAT.replace("0.0 0.0", "0.0")
    with pytest.raises(ValueError, match="two numbers"):
        Instance.from_dat(bad.splitlines())


# ── loaders ───────────────────────────────────────────────────────────────────

def test_load_dat_from_string_lines():
    inst = load_dat(MINIMAL_DAT.splitlines())
    assert len(inst.depots) == 2


def test_load_dat_path(tmp_path):
    p = tmp_path / "test.dat"
    p.write_text(MINIMAL_DAT)
    inst = load_dat_path(p)
    assert inst.data["n_clients"] == 3


def test_load_dat_from_real_file():
    inst = load_dat("instances/Exp5x3-a.dat")
    assert inst.data["n_clients"] == 5
    assert inst.data["n_depots"] == 3


def test_load_dat_folder(tmp_path):
    for name in ("a.dat", "b.dat"):
        (tmp_path / name).write_text(MINIMAL_DAT)
    result = load_dat_folder(tmp_path)
    assert set(result.keys()) == {"a.dat", "b.dat"}
    assert all(isinstance(v, Instance) for v in result.values())


def test_list_dat_files(tmp_path):
    for name in ("b.dat", "a.dat"):
        (tmp_path / name).write_text(MINIMAL_DAT)
    files = list_dat_files(tmp_path)
    assert [f.name for f in files] == ["a.dat", "b.dat"]  # sorted
