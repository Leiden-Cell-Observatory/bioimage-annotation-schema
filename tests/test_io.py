"""Reading, writing and validating set and record documents."""

import pytest

from bioimage_annotation_schema import (
    SchemaError,
    parse_records,
    read_records,
    read_set,
    write_records,
    write_set,
)


class TestRoundTrip:
    def test_set_and_records_survive_write_and_read(self, set_folder, tmp_path):
        annotation_set, records = read_set(set_folder), read_records(set_folder)
        out = tmp_path / "out"
        out.mkdir()
        write_set(annotation_set, out)
        write_records(records, out)
        assert read_set(out) == annotation_set
        assert read_records(out) == records

    def test_unused_columns_are_left_out(self, set_folder, tmp_path):
        write_records(read_records(set_folder), tmp_path / "r.csv")
        header = (tmp_path / "r.csv").read_text().splitlines()[0].split(",")
        assert "patch_x" not in header
        assert header[:2] == ["annotation_id", "image_uri"]


class TestRejection:
    def test_unknown_key_in_set_is_reported_with_its_place(self, set_folder):
        path = set_folder / "annotation-set.yaml"
        path.write_text(path.read_text().replace("  coverage: all", "  coverag: all"))
        with pytest.raises(SchemaError) as error:
            read_set(set_folder)
        assert any("methodology.coverag" in p for p in error.value.problems)

    def test_licence_outside_the_archive_is_rejected(self, set_folder):
        path = set_folder / "annotation-set.yaml"
        path.write_text(path.read_text().replace("license: CC-BY-4.0", "license: MIT"))
        with pytest.raises(SchemaError, match="license"):
            read_set(set_folder)

    def test_wrong_schema_version_is_rejected(self, set_folder):
        path = set_folder / "annotation-set.yaml"
        path.write_text(path.read_text().replace('"0.1.0"', '"0.2.0"'))
        with pytest.raises(SchemaError):
            read_set(set_folder)

    def test_record_rules_are_checked_with_row_numbers(self):
        rows = [
            {"annotation_id": "a", "image_uri": "omero:image:1", "split": "training",
             "status": "excluded", "mask_file": "annotation_output/a_mask.tif"},
            {"annotation_id": "a", "image_uri": "omero:image:2", "split": "test",
             "status": "pending"},
        ]
        with pytest.raises(SchemaError) as error:
            parse_records(rows)
        assert any(p.startswith("row 1: ") for p in error.value.problems)
        assert any("not unique" in p for p in error.value.problems)

    def test_text_in_a_number_column_is_rejected(self):
        with pytest.raises(SchemaError, match="row 1: channel"):
            parse_records([{"annotation_id": "a", "image_uri": "x", "split": "test",
                            "status": "pending", "channel": "one"}])
