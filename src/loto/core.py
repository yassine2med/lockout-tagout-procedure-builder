"""Validate a lockout tagout (LOTO) definition and render a procedure sheet."""
from __future__ import annotations

from pathlib import Path

import yaml

REQUIRED_SOURCE_FIELDS = ("type", "location", "isolation", "lock_id")
ENERGY_TYPES = {"electrical", "hydraulic", "pneumatic", "thermal", "gravity", "chemical", "stored"}


class ProcedureError(ValueError):
    """Raised when a procedure file is invalid."""


def load_procedure(path: str | Path) -> dict:
    """Load and validate a YAML procedure. Raises ProcedureError listing every problem."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ProcedureError(f"invalid YAML: {exc}") from exc
    problems = validate(data)
    if problems:
        raise ProcedureError("; ".join(problems))
    return data


def validate(data: object) -> list[str]:
    """Return a list of problems; an empty list means the procedure is valid."""
    if not isinstance(data, dict):
        return ["file must contain a mapping"]
    problems = []
    for key in ("equipment", "building", "authorized_employees"):
        if not data.get(key):
            problems.append(f"missing '{key}'")
    sources = data.get("energy_sources")
    if not isinstance(sources, list) or not sources:
        problems.append("at least one energy source is required")
        return problems
    seen_locks: set[str] = set()
    for i, src in enumerate(sources, start=1):
        if not isinstance(src, dict):
            problems.append(f"source {i}: must be a mapping")
            continue
        for field in REQUIRED_SOURCE_FIELDS:
            if not src.get(field):
                problems.append(f"source {i}: missing '{field}'")
        kind = str(src.get("type", "")).lower()
        if kind and kind not in ENERGY_TYPES:
            problems.append(f"source {i}: unknown energy type '{kind}'")
        lock = src.get("lock_id")
        if lock in seen_locks:
            problems.append(f"source {i}: lock '{lock}' is used twice")
        if lock:
            seen_locks.add(lock)
        if kind in {"stored", "hydraulic", "pneumatic", "gravity"} and not src.get("release"):
            problems.append(f"source {i}: stored energy needs a 'release' step")
    return problems


def render(data: dict) -> str:
    """Render a validated procedure as a Markdown sheet."""
    src = data["energy_sources"]
    lines = [
        f"# LOTO procedure: {data['equipment']}",
        "",
        f"Building: {data['building']}",
        f"Authorized employees: {', '.join(data['authorized_employees'])}",
        "",
        "## Energy sources",
        "",
        "| # | Type | Location | Isolation | Lock |",
        "|---|------|----------|-----------|------|",
    ]
    for i, s in enumerate(src, start=1):
        lines.append(f"| {i} | {s['type']} | {s['location']} | {s['isolation']} | {s['lock_id']} |")
    lines += ["", "## Steps", ""]
    steps = ["Notify affected employees that the equipment will be shut down.", "Shut down the equipment by its normal stop procedure."]
    for i, s in enumerate(src, start=1):
        steps.append(f"Isolate source {i}: {s['isolation']} at {s['location']}.")
    for i, s in enumerate(src, start=1):
        steps.append(f"Apply lock {s['lock_id']} and tag to source {i}.")
    for i, s in enumerate(src, start=1):
        if s.get("release"):
            steps.append(f"Release stored energy at source {i}: {s['release']}.")
    steps.append("Verify zero energy: try to start the equipment, then return controls to off.")
    for n, text in enumerate(steps, start=1):
        lines.append(f"{n}. {text}")
    lines += ["", "## Return to service", "",
              "1. Remove tools and check that guards are in place.",
              "2. Each authorized employee removes only their own lock and tag.",
              "3. Notify affected employees and restore energy."]
    return "\n".join(lines) + "\n"
