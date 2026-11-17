"""The examples validate against the generated schemas; broken records do not."""

import csv
import json
import subprocess
from pathlib import Path

import jsonschema
import pytest
import yaml

from bioimage_annotation_schema.datamodel import AnnotationSet

ROOT = Path(__file__).parent.parent
SCHEMA = ROOT / "src" / "bioimage_annotation_schema" / "schema" / "0.1"
EXAMPLES = ROOT / "examples" / "0.1"
LINKML = ROOT / "src" / "bioimage_annotation_schema" / "schema" / "bioimage_annotation_schema.yaml"


def _validator(name: str) -> jsonschema.Draft202012Validator:
    schema = json.loads((SCHEMA / name).read_text())
    return jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )


def _records() -> list[dict]:
    """CSV rows as JSON objects: empty cells dropped, numbers as integers."""
    ints = {"channel", "timepoint", "z_slice", "session", "level"}
    with (EXAMPLES / "annotation-records.csv").open(newline="") as f:
        return [
            {k: int(v) if k in ints else v for k, v in row.items() if v != ""}
            for row in csv.DictReader(f)
        ]


def _set() -> dict:
    return yaml.safe_load((EXAMPLES / "annotation-set.yaml").read_text())


class TestAnnotationSet:
    def test_example_matches_json_schema(self):
        _validator("annotation-set.schema.json").validate(_set())

    def test_example_loads_into_pydantic_model(self):
        assert AnnotationSet(**_set()).methodology.criteria

    def test_missing_methodology_is_rejected(self):
        data = _set()
        del data["methodology"]
        assert not _validator("annotation-set.schema.json").is_valid(data)

    def test_study_ontology_terms_are_optional(self):
        data = _set()
        assert data["study"]["organism_term"].endswith("NCBITaxon_9606")
        assert data["study"]["imaging_method_term"].endswith("FBbi_00100013")
        del data["study"]["organism_term"], data["study"]["imaging_method_term"]
        _validator("annotation-set.schema.json").validate(data)
        assert AnnotationSet(**data).study.organism_term is None

    @pytest.mark.parametrize("slot", ["organism_term", "imaging_method_term"])
    def test_study_term_that_is_no_iri_is_rejected(self, slot):
        data = _set()
        data["study"][slot] = "not an iri"
        assert not _validator("annotation-set.schema.json").is_valid(data)

    def test_example_passes_linkml_validate(self):
        result = subprocess.run(
            ["linkml-validate", "-s", str(LINKML), "-C", "AnnotationSet",
             str(EXAMPLES / "annotation-set.yaml")],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr


class TestAnnotationRecords:
    @pytest.mark.parametrize("record", _records(), ids=lambda r: r["annotation_id"])
    def test_example_rows_match_json_schema(self, record):
        _validator("annotation-record.schema.json").validate(record)

    def test_excluded_record_with_mask_is_rejected(self):
        record = {"annotation_id": "x", "image_uri": "omero:image:1",
                  "split": "training", "status": "excluded",
                  "mask_file": "annotation_output/x_mask.tif"}
        assert not _validator("annotation-record.schema.json").is_valid(record)

    def test_incomplete_patch_is_rejected(self):
        record = {"annotation_id": "x", "image_uri": "omero:image:1",
                  "split": "training", "status": "pending", "patch_x": 0}
        assert not _validator("annotation-record.schema.json").is_valid(record)
