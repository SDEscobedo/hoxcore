"""Deterministic full-snapshot domain extraction, independent of Git/SQL/filesystems.

SaaS authorization and stricter relationship policy belong to the caller.
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

import yaml
from yaml.events import AliasEvent, CollectionEndEvent, CollectionStartEvent

from hxc.core.operations.validate import ValidateOperation

INDEX_MODEL_VERSION = 1
FORMAT_VERSION = 1
MAX_FILES = 128
MAX_FILE_BYTES = 128 * 1024
MAX_TOTAL_BYTES = 1024 * 1024
MAX_DIAGNOSTICS = 100
FOLDERS = {
    "programs": ("program", "prog"),
    "projects": ("project", "proj"),
    "missions": ("mission", "miss"),
    "actions": ("action", "act"),
}


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    message: str
    path: str = ""


@dataclass(frozen=True)
class IndexSnapshot:
    index_model_version: int
    format_version: int
    entities: Tuple[Dict[str, Any], ...]
    relationships: Tuple[Dict[str, str], ...]
    diagnostics: Tuple[Diagnostic, ...]

    @property
    def valid(self) -> bool:
        return not any(item.severity == "error" for item in self.diagnostics)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index_model_version": self.index_model_version,
            "format_version": self.format_version,
            "entities": list(self.entities),
            "relationships": list(self.relationships),
            "diagnostics": [vars(item).copy() for item in self.diagnostics],
            "valid": self.valid,
        }


class _Loader(yaml.SafeLoader):
    def construct_mapping(self, node: Any, deep: bool = False) -> Dict[str, Any]:
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise ValueError("Duplicate or non-string mapping key")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def _parse(raw: bytes) -> Any:
    depth = 0
    for index, event in enumerate(yaml.parse(raw, Loader=yaml.SafeLoader)):
        if isinstance(event, AliasEvent):
            raise ValueError("Aliases are unsupported")
        if isinstance(event, CollectionStartEvent):
            depth += 1
        if isinstance(event, CollectionEndEvent):
            depth -= 1
        if depth > 16 or index >= 10000:
            raise ValueError("YAML complexity limit")
    value = yaml.load(raw, Loader=_Loader)
    # Canonical JSON-compatible types; dates, binary, sets and NaN are unsupported.
    return json.loads(json.dumps(value, allow_nan=False, sort_keys=True))


def build_index(
    snapshot: Mapping[str, bytes],
    index_model_version: int = 1,
    *,
    format_version: int = 1,
) -> IndexSnapshot:
    """Extract a complete immutable-input snapshot with bounded diagnostics.

    Unsupported versions never silently select a model. Invalid snapshots expose
    diagnostics but no partial entity/relationship index. Related-link warnings
    preserve core behavior; hosted closed-reference policy must be applied outside.
    Native ``index.db`` is not a canonical snapshot file and is rejected.
    """
    diagnostics = []  # type: List[Diagnostic]

    def fail(code: str, message: str, path: str = "") -> None:
        if len(diagnostics) < MAX_DIAGNOSTICS:
            diagnostics.append(Diagnostic(code, "error", message[:256], path))

    def result(entities: Any = (), links: Any = ()) -> IndexSnapshot:
        if any(d.severity == "error" for d in diagnostics):
            entities, links = (), ()
        return IndexSnapshot(
            index_model_version,
            format_version,
            tuple(entities),
            tuple(links),
            tuple(diagnostics),
        )

    if (
        type(index_model_version) is not int
        or index_model_version != INDEX_MODEL_VERSION
    ):
        fail("unsupported_model", "Unsupported index model version")
        return result()
    if type(format_version) is not int or format_version != FORMAT_VERSION:
        fail("unsupported_format", "Unsupported snapshot format version")
        return result()
    if len(snapshot) > MAX_FILES:
        fail("resource_limit", "Too many files")
        return result()
    if any(
        not isinstance(k, str) or not isinstance(v, bytes) for k, v in snapshot.items()
    ):
        fail("invalid_snapshot", "Expected relative path to bytes mapping")
        return result()
    if sum(len(v) for v in snapshot.values()) > MAX_TOTAL_BYTES:
        fail("resource_limit", "Snapshot byte limit")
        return result()
    if "config.yml" not in snapshot or ".gitignore" not in snapshot:
        fail("missing_config", "Missing native configuration")
        return result()
    entities = []
    validated = []
    for path, raw in sorted(snapshot.items()):
        if len(path) > 128 or (
            path not in ("config.yml", ".gitignore")
            and not re.fullmatch(
                r"(programs/prog|projects/proj|missions/miss|actions/act)-[a-f0-9]{8}\.yml",
                path,
            )
        ):
            fail("unsafe_path", "Unsupported canonical path")
            continue
        if len(raw) > MAX_FILE_BYTES:
            fail("resource_limit", "File byte limit", path)
            continue
        if path == ".gitignore":
            if raw != b"index.db\n":
                fail("invalid_ignore", "Unsupported ignore rules", path)
            continue
        try:
            value = _parse(raw)
        except (ValueError, TypeError, UnicodeError, RecursionError, yaml.YAMLError):
            fail("invalid_yaml", "Invalid or unsupported YAML", path)
            continue
        if path == "config.yml":
            if value is not None and not isinstance(value, dict):
                fail("invalid_config", "Config must be a mapping", path)
            continue
        if not isinstance(value, dict):
            fail("invalid_entity", "Entity must be a mapping", path)
            continue
        folder, filename = path.split("/")
        kind, prefix = FOLDERS[folder]
        if (
            value.get("type") != kind
            or filename != prefix + "-" + str(value.get("uid")) + ".yml"
        ):
            fail("path_mismatch", "Entity path/type/UID mismatch", path)
            continue
        if not isinstance(value.get("id"), str) or not value["id"]:
            fail("invalid_id", "Entity ID required", path)
            continue
        # Bound shapes before shared rules perform hashing/enumeration.
        if any(not isinstance(value.get(k, ""), str) for k in ("uid", "type")) or (
            value.get("status") and not isinstance(value.get("status"), str)
        ):
            fail("invalid_entity", "Invalid scalar field type", path)
            continue
        if value.get("parent") is not None and not isinstance(value["parent"], str):
            fail("invalid_relationship", "Parent must be a UID", path)
            continue
        if any(
            not isinstance(value.get(k, []), list)
            or any(not isinstance(v, str) for v in value.get(k, []))
            for k in ("children", "related")
        ):
            fail("invalid_relationship", "Relationships must be UID lists", path)
            continue
        entities.append(value)
        validated.append(dict(value, _file={"name": filename, "type": kind}))
    if diagnostics:
        return result()
    validation = ValidateOperation("").validate_entities(validated)
    for severity, messages in (
        ("error", validation.errors),
        ("warning", validation.warnings),
    ):
        for message in messages:
            if len(diagnostics) < MAX_DIAGNOSTICS:
                diagnostics.append(
                    Diagnostic("domain_validation", severity, message[:256])
                )
    links = []
    for entity in entities:
        for kind in ("parent", "children", "related"):
            targets = (
                entity.get(kind, [])
                if kind != "parent"
                else ([entity["parent"]] if entity.get("parent") else [])
            )
            links.extend(
                {"source": entity["uid"], "kind": kind, "target": target}
                for target in targets
            )
    return result(
        entities,
        sorted(links, key=lambda link: (link["source"], link["kind"], link["target"])),
    )
