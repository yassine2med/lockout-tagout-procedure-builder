import copy

import pytest

from loto.__main__ import main
from loto.core import ProcedureError, load_procedure, render, validate

GOOD = {
    "equipment": "Pump P-1",
    "building": "Building B",
    "authorized_employees": ["Tech 1"],
    "energy_sources": [
        {"type": "electrical", "location": "Panel 1", "isolation": "Open breaker", "lock_id": "L1"},
        {"type": "hydraulic", "location": "Line A", "isolation": "Close valve", "lock_id": "L2", "release": "Bleed line"},
    ],
}


def test_valid_has_no_problems():
    assert validate(GOOD) == []


def test_not_a_mapping():
    assert validate(["x"]) == ["file must contain a mapping"]


def test_missing_equipment():
    d = copy.deepcopy(GOOD)
    del d["equipment"]
    assert "missing 'equipment'" in validate(d)


def test_no_sources():
    d = copy.deepcopy(GOOD)
    d["energy_sources"] = []
    assert any("at least one" in p for p in validate(d))


def test_missing_lock():
    d = copy.deepcopy(GOOD)
    del d["energy_sources"][0]["lock_id"]
    assert any("missing 'lock_id'" in p for p in validate(d))


def test_duplicate_lock():
    d = copy.deepcopy(GOOD)
    d["energy_sources"][1]["lock_id"] = "L1"
    assert any("used twice" in p for p in validate(d))


def test_unknown_energy_type():
    d = copy.deepcopy(GOOD)
    d["energy_sources"][0]["type"] = "magic"
    assert any("unknown energy type" in p for p in validate(d))


def test_stored_energy_needs_release():
    d = copy.deepcopy(GOOD)
    del d["energy_sources"][1]["release"]
    assert any("needs a 'release'" in p for p in validate(d))


def test_render_contains_steps_in_order():
    text = render(GOOD)
    assert text.index("Isolate source 1") < text.index("Apply lock L1") < text.index("Release stored energy") < text.index("Verify zero energy")
    assert "| 2 | hydraulic | Line A | Close valve | L2 |" in text


def test_load_example():
    data = load_procedure("examples/air-handler.yaml")
    assert len(data["energy_sources"]) == 3


def test_load_bad_yaml(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("a: [unclosed\n")
    with pytest.raises(ProcedureError, match="invalid YAML"):
        load_procedure(f)


def test_cli_writes_file(tmp_path):
    out = tmp_path / "sheet.md"
    assert main(["build", "examples/air-handler.yaml", "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("# LOTO procedure: Air Handler AHU-3")


def test_cli_invalid_returns_2(tmp_path):
    f = tmp_path / "x.yaml"
    f.write_text("equipment: X\n")
    assert main(["build", str(f)]) == 2
