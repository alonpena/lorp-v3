"""Parse the C ``.dat`` instance format (``ReadData_sizing``).

Format (C audit §8), one value per logical line, blanks ignored::

    n_clients
    n_depots
    max_depots_open
    n_vehicles
    [depot coords: x y, one per depot]
    [client coords: x y, one per client]
    vehicle_capacity
    [depot base capacities, one per depot]
    [client demands, one per client]
    [depot fixed costs, one per depot]
    vehicle_fixed_cost
    trailing integer flag        # mandatory in C (0 or 1); optional here

IDs are implicit and 1-indexed: depots ``1..n_depots``, clients ``1..n_clients``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

from .geometry import Point

PathLike = Union[str, Path]

# Folders searched by :func:`resolve_dat_path`, in priority order. ``instances/``
# is the canonical dataset; the others are kept for robustness. (The plan listed
# ``instances_LRP`` which does not exist; the real folders are below.)
DEFAULT_INSTANCE_FOLDERS: Tuple[str, ...] = (
    "instances",
    "instances_old",
    "reference/LoRPSD/instances_LLRP",
)


@dataclass(frozen=True)
class DepotNode:
    id: int  # 1-based
    x: float
    y: float
    base_capacity: float  # QD_i: the .dat base capacity before facility sizing
    fixed_cost: float

    @property
    def xy(self) -> Point:
        return (self.x, self.y)


@dataclass(frozen=True)
class ClientNode:
    id: int  # 1-based
    x: float
    y: float
    demand: float

    @property
    def xy(self) -> Point:
        return (self.x, self.y)


@dataclass(frozen=True)
class ParsedInstance:
    name: str
    n_clients: int
    n_depots: int
    max_depots_open: int
    n_vehicles: int
    vehicle_capacity: float
    vehicle_fixed_cost: float
    trailing_flag: Optional[int]
    depots: Dict[int, DepotNode]
    clients: Dict[int, ClientNode]

    @property
    def total_demand(self) -> float:
        return sum(c.demand for c in self.clients.values())

    @property
    def total_fixed_cost(self) -> float:
        """Sum of depot fixed costs (``totalfix`` in the C sizing formula)."""
        return sum(d.fixed_cost for d in self.depots.values())

    def depot_xy(self, depot_id: int) -> Point:
        return self.depots[depot_id].xy

    def client_xy(self, client_id: int) -> Point:
        return self.clients[client_id].xy

    def all_points(self) -> List[Point]:
        return [d.xy for d in self.depots.values()] + [c.xy for c in self.clients.values()]


def _clean_lines(raw: Iterable[str]) -> List[str]:
    return [s.strip() for s in raw if s.strip()]


def _num(s: str) -> float:
    return float(s)


def _int(s: str) -> int:
    return int(float(s))


def _read_pairs(lines: List[str], count: int, start: int) -> Tuple[List[Point], int]:
    coords: List[Point] = []
    idx = start
    for _ in range(count):
        if idx >= len(lines):
            raise ValueError("unexpected end of file while reading coordinates")
        parts = lines[idx].split()
        if len(parts) != 2:
            raise ValueError(
                f"line {idx + 1} must contain two numbers 'x y'; found {lines[idx]!r}"
            )
        coords.append((float(parts[0]), float(parts[1])))
        idx += 1
    return coords, idx


def parse_dat(source: Union[PathLike, Iterable[str]], *, name: Optional[str] = None) -> ParsedInstance:
    """Parse a C ``.dat`` file (or iterable of lines) into a :class:`ParsedInstance`."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        raw = path.read_text(encoding="utf-8").splitlines()
        if name is None:
            name = path.name
    else:
        raw = list(source)
        if name is None:
            name = "<memory>"

    lines = _clean_lines(raw)
    idx = 0

    def take() -> str:
        nonlocal idx
        if idx >= len(lines):
            raise ValueError("unexpected end of file while parsing header")
        value = lines[idx]
        idx += 1
        return value

    n_clients = _int(take())
    n_depots = _int(take())
    max_depots_open = _int(take())
    n_vehicles = _int(take())

    if n_clients <= 0 or n_depots <= 0:
        raise ValueError("n_clients and n_depots must be positive")
    if not (1 <= max_depots_open <= n_depots):
        raise ValueError(
            f"max_depots_open ({max_depots_open}) must be in [1, n_depots={n_depots}]"
        )

    depot_xy, idx = _read_pairs(lines, n_depots, idx)
    client_xy, idx = _read_pairs(lines, n_clients, idx)

    vehicle_capacity = _num(lines[idx]); idx += 1
    if vehicle_capacity <= 0:
        raise ValueError("vehicle_capacity must be > 0")

    depot_caps = [_num(lines[idx + k]) for k in range(n_depots)]; idx += n_depots
    demands = [_num(lines[idx + k]) for k in range(n_clients)]; idx += n_clients
    depot_fixed = [_num(lines[idx + k]) for k in range(n_depots)]; idx += n_depots
    vehicle_fixed_cost = _num(lines[idx]); idx += 1

    trailing_flag: Optional[int] = None
    if idx < len(lines):
        trailing_flag = _int(lines[idx])
        if trailing_flag not in (0, 1):
            raise ValueError(
                f"trailing flag must be 0 or 1 (C requirement); found {trailing_flag}"
            )
        idx += 1

    depots = {
        k + 1: DepotNode(
            id=k + 1,
            x=depot_xy[k][0],
            y=depot_xy[k][1],
            base_capacity=depot_caps[k],
            fixed_cost=depot_fixed[k],
        )
        for k in range(n_depots)
    }
    clients = {
        k + 1: ClientNode(
            id=k + 1,
            x=client_xy[k][0],
            y=client_xy[k][1],
            demand=demands[k],
        )
        for k in range(n_clients)
    }

    return ParsedInstance(
        name=name,
        n_clients=n_clients,
        n_depots=n_depots,
        max_depots_open=max_depots_open,
        n_vehicles=n_vehicles,
        vehicle_capacity=vehicle_capacity,
        vehicle_fixed_cost=vehicle_fixed_cost,
        trailing_flag=trailing_flag,
        depots=depots,
        clients=clients,
    )


# --------------------------------------------------------------------------- #
# Instance-path resolution (do not silently drop rows on filename mismatch).   #
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class InstanceResolution:
    requested: str
    status: str  # EXACT | COORD_PREFIX | SUFFIX_GLOB | MISSING | AMBIGUOUS
    path: Optional[Path]
    candidates: Tuple[Path, ...]

    @property
    def ok(self) -> bool:
        return self.path is not None and self.status not in {"MISSING", "AMBIGUOUS"}


def resolve_dat_path(
    instance_name: str,
    folders: Iterable[PathLike] = DEFAULT_INSTANCE_FOLDERS,
    *,
    root: PathLike = ".",
) -> InstanceResolution:
    """Resolve an Excel instance name to a ``.dat`` path without renaming.

    Priority per folder: exact match, then ``coord``-prefixed, then ``*name``
    suffix glob. The first folder yielding a unique match wins. Ambiguous suffix
    matches are reported (status ``AMBIGUOUS``), never guessed.
    """
    requested = str(instance_name).strip()
    root_path = Path(root)
    all_candidates: List[Path] = []

    for folder in folders:
        base = root_path / folder
        if not base.exists():
            continue

        exact = base / requested
        if exact.exists():
            return InstanceResolution(requested, "EXACT", exact, (exact,))

        coord = base / f"coord{requested}"
        if coord.exists():
            return InstanceResolution(requested, "COORD_PREFIX", coord, (coord,))

        suffix = tuple(sorted(base.glob(f"*{requested}")))
        all_candidates.extend(suffix)
        if len(suffix) == 1:
            return InstanceResolution(requested, "SUFFIX_GLOB", suffix[0], suffix)

    if len(all_candidates) > 1:
        return InstanceResolution(requested, "AMBIGUOUS", None, tuple(all_candidates))
    return InstanceResolution(requested, "MISSING", None, ())


__all__ = [
    "PathLike",
    "DEFAULT_INSTANCE_FOLDERS",
    "DepotNode",
    "ClientNode",
    "ParsedInstance",
    "parse_dat",
    "InstanceResolution",
    "resolve_dat_path",
]
