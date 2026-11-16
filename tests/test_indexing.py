"""Snapshot API determinism, bounds and CLI domain semantics."""

import copy
import json
import sqlite3

import pytest
import yaml

from hxc.core.enums import EntityType
from hxc.core.operations.create import CreateOperation
from hxc.core.operations.init import InitOperation
from hxc.indexing import build_index


def fixture():
    return {
        "config.yml": b"{}\n",
        ".gitignore": b"index.db\n",
        "actions/act-11111111.yml": b'type: action\nuid: "11111111"\nid: example\ntitle: Example\n',
    }


def test_deterministic_no_mutation_or_database(monkeypatch):
    source = fixture()
    before = copy.deepcopy(source)
    monkeypatch.setattr(
        sqlite3, "connect", lambda *a, **k: pytest.fail("SQLite must not be used")
    )
    a = build_index(source)
    b = build_index(dict(reversed(list(source.items()))))
    assert a.valid and a.to_dict() == b.to_dict() and source == before
    json.dumps(a.to_dict(), allow_nan=False)
    assert a.entities[0]["uid"] == "11111111"


@pytest.mark.parametrize(
    "change,code",
    [
        ({"index.db": b"bad"}, "unsafe_path"),
        ({"../config.yml": b"{}"}, "unsafe_path"),
        ({"config.yml": b"a: 1\na: 2"}, "invalid_yaml"),
        ({"config.yml": b"a: &a [*a]"}, "invalid_yaml"),
        ({"config.yml": b"a: .nan"}, "invalid_yaml"),
        ({"config.yml": b"x" * (128 * 1024 + 1)}, "resource_limit"),
        ({"actions/act-11111111.yml": b"[]"}, "invalid_entity"),
        (
            {
                "actions/act-11111111.yml": b'type: action\nuid: "11111111"\nid: a\ntitle: A\nchildren: [missing]'
            },
            "domain_validation",
        ),
    ],
)
def test_invalid_snapshot(change, code):
    result = build_index(dict(fixture(), **change))
    assert not result.valid and not result.entities and not result.relationships
    assert result.diagnostics[0].code == code


def test_versions_delete_restore_and_related_policy():
    assert not build_index(fixture(), 99).valid
    assert not build_index(fixture(), format_version=99).valid
    files = fixture()
    saved = build_index(files).to_dict()
    files.pop("actions/act-11111111.yml")
    assert build_index(files).valid and not build_index(files).entities
    assert build_index(fixture()).to_dict() == saved
    files = fixture()
    files["actions/act-11111111.yml"] += b"related: [missing]\n"
    result = build_index(files)
    assert result.valid and result.diagnostics[0].severity == "warning"
    assert result.relationships[0]["target"] == "missing"


def test_diagnostic_bounds():
    files = fixture()
    for i in range(125):
        files["actions/act-%08x.yml" % i] = b"[]"
    result = build_index(files)
    assert not result.valid and len(result.diagnostics) <= 100
    assert all(len(d.message) <= 256 for d in result.diagnostics)


def test_native_operations_keep_isolated_sqlite(tmp_path):
    InitOperation(str(tmp_path)).initialize_registry(use_git=False)
    assert (tmp_path / "index.db").exists()
    CreateOperation(str(tmp_path)).create_entity(
        EntityType.ACTION, "Example", use_git=False
    )
    snapshot = {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file() and p.name != "index.db"
    }
    (tmp_path / "index.db").unlink()
    assert build_index(snapshot).valid


@pytest.mark.parametrize(
    "raw", [b"[" * 17 + b"0" + b"]" * 17, b"[" + b"0," * 11000 + b"0]"]
)
def test_yaml_complexity_bounds(raw):
    result = build_index(dict(fixture(), **{"config.yml": raw}))
    assert not result.valid and result.diagnostics[0].code == "invalid_yaml"


def test_file_count_bound():
    files = fixture()
    files.update({"actions/act-%08x.yml" % i: b"[]" for i in range(127)})
    result = build_index(files)
    assert not result.valid and result.diagnostics[0].code == "resource_limit"
