"""Subset-minimal target-retention witnesses for omitted reflection targets."""
from __future__ import annotations

from typing import Any

from .schema import exact_keys, require, strict_equal


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
    exact_keys(evidence, {"site", "claimed_targets", "target", "base", "selected", "necessity"},
               "missing-target witness")
    worlds = summary["worlds"]
    site = evidence["site"]
    require(type(site) is int and 0 <= site < len(summary["may"]), "missing-target site")
    target = evidence["target"]
    require(type(target) is list and len(target) == 4 and all(type(field) is str for field in target),
            "missing-target identity")
    claimed = evidence["claimed_targets"]
    require(type(claimed) is list, "claimed target set")
    require(all(type(candidate) is list and len(candidate) == 4 and
                all(type(field) is str for field in candidate) for candidate in claimed),
            "claimed target identity")
    require(claimed == sorted(claimed) and len({tuple(candidate) for candidate in claimed}) == len(claimed),
            "claimed target canonical form")
    actual_may = {tuple(candidate) for candidate in summary["may"][site]}
    require(all(tuple(candidate) in actual_may for candidate in claimed), "claimed target outside exact set")
    require(not any(strict_equal(candidate, target) for candidate in claimed), "target is not omitted")
    require(tuple(target) in actual_may, "target is not possible")
    by_id = {world["index"]: world for world in worlds}
    base_index = evidence["base"]
    require(type(base_index) is int and base_index in by_id, "missing-target base")
    base = by_id[base_index]
    require(_contains(base, site, target), "base lacks missing target")
    selected = evidence["selected"]
    require(type(selected) is list and selected == sorted(set(selected)), "selected coordinates")
    require(all(type(index) is int and 0 <= index < len(base["external"]) for index in selected),
            "selected coordinate bound")
    require(retains_target(worlds, site, target, base, set(selected)), "slice does not retain target")
    necessity = evidence["necessity"]
    require(type(necessity) is list and len(necessity) == len(selected), "necessity coverage")
    for index, witness in zip(selected, necessity):
        exact_keys(witness, {"removed", "world"}, "missing-target necessity")
        require(witness["removed"] == index and type(witness["world"]) is int and witness["world"] in by_id,
                "necessity identity")
        world = by_id[witness["world"]]
        require(_matches(world, base, set(selected) - {index}) and not _contains(world, site, target),
                "false missing-target necessity")
    return True
