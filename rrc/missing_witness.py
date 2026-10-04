"""Subset-minimal target-retention witnesses for omitted reflection targets."""
from __future__ import annotations

from typing import Any

from .schema import strict_equal


def _contains(world: dict[str, Any], site: int, target: list[str]) -> bool:
    return any(strict_equal(candidate, target) for candidate in world["targets"][site])


def _matches(world: dict[str, Any], base: dict[str, Any], selected: set[int] | list[int]) -> bool:
    return all(world["external"][index] is base["external"][index] for index in selected)


def retains_target(worlds: list[dict[str, Any]], site: int, target: list[str], base: dict[str, Any],
                   selected: set[int]) -> bool:
    return all(_contains(world, site, target) for world in worlds if _matches(world, base, selected))


def produce_missing_target_witness(summary: dict[str, Any], site: int, target: list[str],
                                   claimed_targets: list[list[str]], base_index: int,
                                   reverse: bool = False) -> dict[str, Any]:
    worlds = summary["worlds"]
    base = next(world for world in worlds if world["index"] == base_index)
    if not _contains(base, site, target):
        raise ValueError("base does not contain target")
    if any(strict_equal(candidate, target) for candidate in claimed_targets):
        raise ValueError("target is not missing from the claimed set")
    selected = set(range(len(base["external"])))
    for index in sorted(tuple(selected), reverse=reverse):
        if retains_target(worlds, site, target, base, selected - {index}):
            selected.remove(index)
    necessity = []
    for index in sorted(selected):
        witness = next(
            world for world in worlds
            if _matches(world, base, selected - {index}) and not _contains(world, site, target)
        )
        necessity.append({"removed": index, "world": witness["index"]})
    return {
        "site": site,
        "claimed_targets": claimed_targets,
        "target": target,
        "base": base_index,
        "selected": sorted(selected),
        "necessity": necessity,
    }


def check_missing_target_witness(summary: dict[str, Any], evidence: Any) -> bool:
    """Compatibility entry point; the acceptance implementation is separate.

    ``summary`` must be obtained from a successful finite certificate check.
    Neither this wrapper nor the independent checker invokes production helpers.
    """
    from .witness_checker import check_missing_target_witness as independent_check
    return independent_check(summary, evidence)
