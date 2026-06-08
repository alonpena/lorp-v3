from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InstanceResolution:
    requested: str
    status: str  # EXACT | COORD_PREFIX | SUFFIX_GLOB | MISSING | AMBIGUOUS
    path: Path | None
    candidates: tuple[Path, ...]

    @property
    def ok(self) -> bool:
        return self.path is not None and self.status not in {"MISSING", "AMBIGUOUS"}


def resolve_instance_path(instance_name: str, instance_folder: str | Path) -> InstanceResolution:
    """Resolve Excel instance names against dataset files without renaming.

    Priority:
    1. exact: instances/foo.dat
    2. coord prefix: instances/coordfoo.dat
    3. suffix glob: instances/*foo.dat

    Ambiguous suffix matches are reported, not guessed.
    """
    folder = Path(instance_folder)
    requested = str(instance_name).strip()

    exact = folder / requested
    if exact.exists():
        return InstanceResolution(requested, "EXACT", exact, (exact,))

    coord = folder / f"coord{requested}"
    if coord.exists():
        return InstanceResolution(requested, "COORD_PREFIX", coord, (coord,))

    suffix_matches = tuple(sorted(folder.glob(f"*{requested}")))
    if len(suffix_matches) == 1:
        return InstanceResolution(requested, "SUFFIX_GLOB", suffix_matches[0], suffix_matches)
    if len(suffix_matches) > 1:
        return InstanceResolution(requested, "AMBIGUOUS", None, suffix_matches)

    return InstanceResolution(requested, "MISSING", None, ())


__all__ = ["InstanceResolution", "resolve_instance_path"]
