"""Read, write and validate annotation-set and annotation-record documents.

An annotation set lives in a folder: ``annotation-set.yaml`` (one
:class:`AnnotationSet`), ``annotation-records.csv`` (one :class:`AnnotationRecord`
per row) and the files the records point to. Every read and write is checked
against the published JSON Schema, which also holds the cross-field rules the
Pydantic models do not check (an excluded record has no mask, a patch needs all
four coordinates, a volume needs z_start and z_end).
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Sequence
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any

import jsonschema
import yaml
from pydantic import ValidationError

from .datamodel import AnnotationRecord, AnnotationSet

SCHEMA_VERSION = "0.1"
SET_FILE = "annotation-set.yaml"
RECORDS_FILE = "annotation-records.csv"
RECORD_COLUMNS: tuple[str, ...] = tuple(AnnotationRecord.model_fields)


class SchemaError(ValueError):
    """A document does not follow the schema; ``problems`` lists every violation."""

    def __init__(self, what: str, problems: Sequence[str]) -> None:
        self.problems = list(problems)
        super().__init__(f"{what} does not follow the schema:\n- " + "\n- ".join(problems))


@cache
def _validator(name: str) -> jsonschema.Draft202012Validator:
    text = files(__package__).joinpath("schema", SCHEMA_VERSION, name).read_text("utf-8")
    return jsonschema.Draft202012Validator(
        json.loads(text), format_checker=jsonschema.FormatChecker()
    )


def _problems(name: str, data: dict[str, Any], where: str = "") -> list[str]:
    return [
        f"{where}{'.'.join(map(str, e.absolute_path)) or '(document)'}: {e.message}"
        for e in _validator(name).iter_errors(data)
    ]


def _plain(model: AnnotationSet | AnnotationRecord) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude_none=True)


def validate_set(annotation_set: AnnotationSet) -> list[str]:
    """Every way ``annotation_set`` breaks the schema (empty when it follows it)."""
    return _problems("annotation-set.schema.json", _plain(annotation_set))


def validate_records(records: Iterable[AnnotationRecord]) -> list[str]:
    """Every way the records break the schema, prefixed with their row number."""
    problems: list[str] = []
    seen: set[str] = set()
    for i, record in enumerate(records, start=1):
        problems += _problems("annotation-record.schema.json", _plain(record), f"row {i}: ")
        if record.annotation_id in seen:
            problems.append(f"row {i}: annotation_id {record.annotation_id!r} is not unique")
        seen.add(record.annotation_id)
    return problems


def check_documents(
    annotation_set: AnnotationSet, records: Iterable[AnnotationRecord]
) -> list[str]:
    """What the set and its records say about each other that does not hold: a
    record's session must be one of the set's sessions, and ISCC codes need the
    set's ``content_codes`` to say how they were made."""
    sessions = {s.id for s in annotation_set.sessions or []}
    codes = annotation_set.content_codes
    problems: list[str] = []
    for i, record in enumerate(records, start=1):
        if record.session is not None and record.session not in sessions:
            problems.append(f"row {i}: session {record.session} is not in the set's sessions")
        if (record.input_iscc or record.mask_iscc) and not (codes and codes.region):
            problems.append(f"row {i}: has region ISCC codes but content_codes.region is missing")
        if record.image_iscc and not (codes and codes.image):
            problems.append(f"row {i}: has image_iscc but content_codes.image is missing")
    return problems


def _pydantic_problems(error: ValidationError, where: str = "") -> list[str]:
    return [
        f"{where}{'.'.join(map(str, e['loc'])) or '(document)'}: {e['msg']}"
        for e in error.errors()
    ]


def parse_set(data: dict[str, Any]) -> AnnotationSet:
    """An :class:`AnnotationSet` from plain data; :class:`SchemaError` if invalid."""
    try:
        annotation_set = AnnotationSet.model_validate(data)
    except ValidationError as error:
        raise SchemaError("The annotation set", _pydantic_problems(error)) from None
    if problems := validate_set(annotation_set):
        raise SchemaError("The annotation set", problems)
    return annotation_set


def parse_records(rows: Iterable[dict[str, Any]]) -> list[AnnotationRecord]:
    """Records from plain rows (CSV cells as text, empty cells meaning "not set")."""
    records: list[AnnotationRecord] = []
    problems: list[str] = []
    for i, row in enumerate(rows, start=1):
        try:
            records.append(
                AnnotationRecord.model_validate(
                    {k: v for k, v in row.items() if v not in ("", None)}
                )
            )
        except ValidationError as error:
            problems += _pydantic_problems(error, f"row {i}: ")
    problems += validate_records(records) if not problems else []
    if problems:
        raise SchemaError("The annotation records", problems)
    return records


def read_set(path: str | Path) -> AnnotationSet:
    """Read and check an ``annotation-set.yaml`` (or a folder holding one)."""
    path = Path(path)
    path = path / SET_FILE if path.is_dir() else path
    return parse_set(yaml.safe_load(path.read_text(encoding="utf-8")))


def read_records(path: str | Path) -> list[AnnotationRecord]:
    """Read and check an ``annotation-records.csv`` (or a folder holding one)."""
    path = Path(path)
    path = path / RECORDS_FILE if path.is_dir() else path
    with path.open(newline="", encoding="utf-8") as f:
        return parse_records(csv.DictReader(f))


def write_set(annotation_set: AnnotationSet, path: str | Path) -> Path:
    """Check ``annotation_set`` and write it as YAML; returns the path written."""
    if problems := validate_set(annotation_set):
        raise SchemaError("The annotation set", problems)
    path = Path(path)
    path = path / SET_FILE if path.is_dir() else path
    path.write_text(
        yaml.safe_dump(_plain(annotation_set), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def write_records(records: Sequence[AnnotationRecord], path: str | Path) -> Path:
    """Check the records and write them as CSV; returns the path written.

    Columns follow the schema's order; columns no record uses are left out.
    """
    if problems := validate_records(records):
        raise SchemaError("The annotation records", problems)
    rows = [_plain(r) for r in records]
    columns = [c for c in RECORD_COLUMNS if any(c in row for row in rows)]
    path = Path(path)
    path = path / RECORDS_FILE if path.is_dir() else path
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path
