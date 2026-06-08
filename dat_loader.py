from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

PathLike = Union[str, Path]


def _clean_lines(lines: Iterable[str]) -> List[str]:
    out: List[str] = []
    for line in lines:
        s = line.strip()
        if s:
            out.append(s)
    return out


def _to_number(s: str) -> Union[int, float]:
    v = float(s)
    return int(v) if v.is_integer() else v


def _to_int(s: str) -> int:
    return int(float(s))


def _read_coords(block: List[str], count: int, start: int) -> Tuple[List[Tuple[float, float]], int]:
    coords: List[Tuple[float, float]] = []
    idx = start
    for _ in range(count):
        if idx >= len(block):
            raise ValueError("Unexpected EOF while reading coordinates")
        parts = block[idx].split()
        if len(parts) != 2:
            raise ValueError(f"Line {idx + 1} must have two numbers 'x y'. Found {block[idx]!r}")
        coords.append((float(parts[0]), float(parts[1])))
        idx += 1
    return coords, idx


@dataclass
class Instance:
    """LoR .dat instance.

    Structure:
    - n_clients
    - n_depots
    - max_depots_open
    - n_veh
    - depot coords (n_depots lines)
    - client coords (n_clients lines)
    - vehicle cap
    - depot caps (n_depots)
    - client demands (n_clients)
    - depot fixed costs (n_depots)
    - vehicle fixed cost
    - optional cola
    """

    depots: Dict[int, Dict[str, Any]]
    clients: Dict[int, Dict[str, Any]]
    data: Dict[str, Any]

    @staticmethod
    def from_dat(source: Union[PathLike, Iterable[str]]) -> "Instance":
        if isinstance(source, (str, Path)):
            raw = Path(source).read_text(encoding="utf-8").splitlines()
        else:
            raw = list(source)

        lines = _clean_lines(raw)
        idx = 0

        n_clients = _to_int(lines[idx]); idx += 1
        n_depots = _to_int(lines[idx]); idx += 1
        max_depots_open = _to_int(lines[idx]); idx += 1
        n_veh = _to_int(lines[idx]); idx += 1

        if not (1 <= max_depots_open <= n_depots):
            raise ValueError("max_depots_open must be between 1 and n_depots")

        depot_xy, idx = _read_coords(lines, n_depots, idx)
        client_xy, idx = _read_coords(lines, n_clients, idx)

        vehicle_cap = _to_number(lines[idx]); idx += 1
        if float(vehicle_cap) <= 0:
            raise ValueError("vehicle capacity must be > 0")

        depot_caps = [_to_number(lines[idx + k]) for k in range(n_depots)]
        idx += n_depots
        demands = [_to_number(lines[idx + k]) for k in range(n_clients)]
        idx += n_clients
        depot_fixed_costs = [_to_number(lines[idx + k]) for k in range(n_depots)]
        idx += n_depots
        veh_fixed_cost = _to_number(lines[idx]); idx += 1

        cola: Optional[Union[int, float]] = _to_number(lines[idx]) if idx < len(lines) else None

        depots: Dict[int, Dict[str, Any]] = {}
        for k in range(n_depots):
            x, y = depot_xy[k]
            depots[k + 1] = {
                "x": x,
                "y": y,
                "cap": depot_caps[k],
                "fixed_cost": depot_fixed_costs[k],
            }

        clients: Dict[int, Dict[str, Any]] = {}
        for k in range(n_clients):
            x, y = client_xy[k]
            clients[k + 1] = {
                "x": x,
                "y": y,
                "demand": demands[k],
            }

        data = {
            "n_clients": n_clients,
            "n_depots": n_depots,
            "max_depots_open": max_depots_open,
            "n_veh": n_veh,
            "veh_cap": vehicle_cap,
            "veh_fixed_cost": veh_fixed_cost,
            "cola": cola,
        }
        return Instance(depots=depots, clients=clients, data=data)

    def print_instancia(self) -> None:
        print("------ RESUMEN INSTANCIA ------")
        print(f"Depósitos totales   : {self.data['n_depots']}")
        print(f"Clientes totales    : {self.data['n_clients']}")
        print(f"Vehículos disponibles: {self.data['n_veh']}")
        print(f"Capacidad vehículos : {self.data['veh_cap']}")
        print(f"Max depots open     : {self.data['max_depots_open']}")
        if self.data.get("cola") is not None:
            print(f"(cola: {self.data['cola']})")
        print("-------------------------------")

    def preview(self, k_depots: Optional[int] = None, k_clients: int = 5) -> None:
        print("------ DEPÓSITOS ------")
        depot_ids = sorted(self.depots)
        if k_depots is not None:
            depot_ids = depot_ids[:k_depots]
        for i in depot_ids:
            d = self.depots[i]
            print(f"ID {i:<3} | x={d['x']}, y={d['y']} | cap={d['cap']} | fixed={d['fixed_cost']}")
        print("------------------------")
        print("------ CLIENTES ------")
        for j in sorted(self.clients)[:k_clients]:
            c = self.clients[j]
            print(f"ID {j:<3} | x={c['x']}, y={c['y']} | demand={c['demand']}")
        print("----------------------")


DatInstance = Instance


def load_dat(source: Union[PathLike, Iterable[str]]) -> Instance:
    return Instance.from_dat(source)


def load_dat_path(path: PathLike) -> Instance:
    return load_dat(path)


def load_dat_folder(folder: PathLike) -> Dict[str, Instance]:
    folder = Path(folder)
    return {path.name: load_dat(path) for path in sorted(folder.glob("*.dat"))}


def list_dat_files(folder: PathLike) -> List[Path]:
    return sorted(Path(folder).glob("*.dat"))


__all__ = [
    "DatInstance",
    "Instance",
    "list_dat_files",
    "load_dat",
    "load_dat_folder",
    "load_dat_path",
]
