"""Generate the parts of the documentation that come from the LinkML schema.

Writes, all ignored by git:

- ``docs/data/model.json``: classes, fields and enums for the model browser,
- ``docs/overview.md``: the containment tree and an ER diagram of the whole schema,
- ``docs/mifa.md``: the crosswalk from schema fields to MIFA,
- ``docs/reference/``: one page per class, field, enum and type (LinkML ``gen-doc``).

Run with ``pixi run -e docs docs-gen`` (``docs-serve`` and ``docs-build`` run it first).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from linkml_runtime.utils.schemaview import SchemaView

DOCS = Path(__file__).parent
SCHEMA = DOCS.parent / "src/bioimage_annotation_schema/schema/bioimage_annotation_schema.yaml"
ROOTS = ("AnnotationSet", "AnnotationRecord")
MIFA_DOCS = "https://bioimage-archive.github.io/bia-mifa-models/"


def _text(value: object) -> str:
    return " ".join(str(value).split()) if value else ""


def _field(view: SchemaView, cls: str, name: str) -> dict[str, object]:
    slot = view.induced_slot(name, cls)
    rng = slot.range or view.schema.default_range or "string"
    return {
        "name": name,
        "description": _text(slot.description),
        "range": rng,
        "kind": "class" if rng in view.all_classes() else "enum" if rng in view.all_enums() else "type",
        "required": bool(slot.required),
        "multivalued": bool(slot.multivalued),
        "pattern": slot.pattern,
        "minimum": slot.minimum_value,
        "maximum": slot.maximum_value,
        "uri": slot.slot_uri,
        "exact": list(slot.exact_mappings),
        "close": list(slot.close_mappings),
    }


def model(view: SchemaView) -> dict[str, object]:
    classes = {}
    for name, cls in view.all_classes().items():
        rules = [
            _text(r.description) for r in cls.rules or [] if r.description
        ]
        classes[name] = {
            "description": _text(cls.description),
            "uri": cls.class_uri,
            "exact": list(cls.exact_mappings),
            "close": list(cls.close_mappings),
            "rules": rules,
            "fields": [_field(view, name, s) for s in view.class_slots(name)],
        }
    enums = {
        name: {
            "description": _text(enum.description),
            "values": [
                {"value": value, "description": _text(pv.description), "meaning": pv.meaning}
                for value, pv in enum.permissible_values.items()
            ],
        }
        for name, enum in view.all_enums().items()
    }
    schema = view.schema
    return {
        "title": schema.title,
        "version": schema.version,
        "description": _text(schema.description),
        "roots": list(ROOTS),
        "classes": classes,
        "enums": enums,
    }


def tree(data: dict, cls: str, depth: int = 0, shown: set[str] | None = None) -> list[str]:
    """The fields of ``cls`` as a nested list, descending into the classes it holds;
    a class already listed once is marked "see above"."""
    shown = {cls} if shown is None else shown
    lines = []
    for f in data["classes"][cls]["fields"]:
        marks = ("*" if f["required"] else "") + ("[]" if f["multivalued"] else "")
        line = f"{'    ' * depth}{f['name']}{marks}: {f['range']}"
        expand = f["kind"] == "class" and f["range"] != "Any"
        if expand and f["range"] in shown:
            lines.append(line + "  (see above)")
            continue
        lines.append(line)
        if expand:
            shown.add(f["range"])
            lines += tree(data, f["range"], depth + 1, shown)
    return lines


def overview(data: dict) -> str:
    er = subprocess.run(
        ["gen-erdiagram", str(SCHEMA)], check=True, capture_output=True, text=True
    ).stdout
    parts = [
        "# Overview\n",
        "The schema has two documents. Each tree below lists every field; "
        "`*` marks a required field and `[]` a list. "
        "The [model browser](model.md) shows the same tree with each field's details.\n",
    ]
    for root in data["roots"]:
        parts += [f"## {root}\n", data["classes"][root]["description"] + "\n"]
        parts += ["```text", root, *("    " + line for line in tree(data, root)), "```\n"]
    parts += ["## How the classes connect\n", er]
    return "\n".join(parts)


def _mifa(targets: list[str]) -> str:
    return ", ".join(f"`{t.removeprefix('mifa:')}`" for t in targets if t.startswith("mifa:"))


def crosswalk(data: dict) -> str:
    rows = []
    for cls, spec in data["classes"].items():
        for kind in ("exact", "close"):
            if targets := _mifa(spec[kind]):
                rows.append(f"| `{cls}` | | {kind} | {targets} |")
        for f in spec["fields"]:
            for kind in ("exact", "close"):
                if targets := _mifa(f[kind]):
                    rows.append(f"| `{cls}` | `{f['name']}` | {kind} | {targets} |")
    return "\n".join(
        [
            "# MIFA crosswalk\n",
            f"Fields of this schema that correspond to [MIFA]({MIFA_DOCS}), the BioImage "
            "Archive's metadata for AI-ready datasets. *exact* means the same meaning and "
            "values; *close* means related, with the MIFA value composed from it (for "
            "example MIFA's free-text annotation method from the structured methodology).\n",
            "The MIFA export (`bas bia`, `save_bia_package`) follows this table. It is read "
            "from the `exact_mappings` and `close_mappings` in the schema source.\n",
            "| Class | Field | Match | MIFA |",
            "|---|---|---|---|",
            *rows,
            "",
        ]
    )


def main() -> None:
    view = SchemaView(str(SCHEMA))
    data = model(view)
    (DOCS / "data").mkdir(exist_ok=True)
    (DOCS / "data/model.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    (DOCS / "overview.md").write_text(overview(data), encoding="utf-8")
    (DOCS / "mifa.md").write_text(crosswalk(data), encoding="utf-8")
    reference = DOCS / "reference"
    shutil.rmtree(reference, ignore_errors=True)
    reference.mkdir()
    subprocess.run(
        [
            "gen-doc",
            "--subfolder-type-separation",
            "--no-metadata",
            "-d",
            str(reference),
            str(SCHEMA),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
