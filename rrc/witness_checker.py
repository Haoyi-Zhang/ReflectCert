"""Independent checking of retention/minimality against an accepted summary.

The summary is trusted *only after* the finite certificate checker has accepted
it. This module imports syntax utilities, never witness production or retention
helpers. It intentionally checks the quantified property with a separate loop.
"""
from __future__ import annotations
from typing import Any
from .schema import exact_keys, require


def check_missing_target_witness(summary: dict[str, Any], evidence: Any) -> bool:
    exact_keys(evidence, {"site", "claimed_targets", "target", "base", "selected", "necessity"},
               "missing-target witness")
    site = evidence["site"]
    require(type(site) is int and 0 <= site < len(summary["may"]), "missing-target site")
    target = evidence["target"]
    require(type(target) is list and len(target) == 4 and all(type(x) is str for x in target),
            "missing-target identity")
    target_key = tuple(target)
    claimed = evidence["claimed_targets"]
    require(type(claimed) is list and all(type(k) is list and len(k) == 4 and
            all(type(x) is str for x in k) for k in claimed), "claimed target identity")
    require(claimed == sorted(claimed) and len({tuple(k) for k in claimed}) == len(claimed),
            "claimed target canonical form")
    may = {tuple(k) for k in summary["may"][site]}
    require(all(tuple(k) in may for k in claimed), "claimed target outside exact set")
    require(target_key in may, "target is not possible")
    require(target_key not in {tuple(k) for k in claimed}, "target is not omitted")
    worlds = summary["worlds"]
    by_id = {w["index"]: w for w in worlds}
    base_id = evidence["base"]
    require(type(base_id) is int and base_id in by_id, "missing-target base")
    base = by_id[base_id]
    require(target_key in {tuple(k) for k in base["targets"][site]}, "base lacks missing target")
    selected = evidence["selected"]
    require(type(selected) is list, "selected coordinates")
    require(all(type(j) is int and 0 <= j < len(base["external"]) for j in selected),
            "selected coordinate bound")
    require(selected == sorted(set(selected)), "selected coordinates")
    # Universal sufficiency. No producer-side predicate is imported or called.
    for world in worlds:
        differs = False
        for j in selected:
            if world["external"][j] is not base["external"][j]:
                differs = True
                break
        if not differs:
            require(target_key in {tuple(k) for k in world["targets"][site]},
                    "slice does not retain target")
    necessity = evidence["necessity"]
    require(type(necessity) is list and len(necessity) == len(selected), "necessity coverage")
    for j, item in zip(selected, necessity):
        exact_keys(item, {"removed", "world"}, "missing-target necessity")
        require(type(item["removed"]) is int and item["removed"] == j and
                type(item["world"]) is int and item["world"] in by_id, "necessity identity")
        world = by_id[item["world"]]
        for other in selected:
            if other != j:
                require(world["external"][other] is base["external"][other],
                        "false missing-target necessity")
        require(target_key not in {tuple(k) for k in world["targets"][site]},
                "false missing-target necessity")
    return True
