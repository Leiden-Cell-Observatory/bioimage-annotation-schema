"""MIFA documents and the BioImage Archive bundle."""

import csv

import pytest
import yaml

from bioimage_annotation_schema import read_records, read_set
from bioimage_annotation_schema.mifa import compose_method, map_license, save_bia_package, save_mifa


class TestMifaDocuments:
    def test_three_documents_with_annotated_records_only(self, set_folder, tmp_path):
        paths = save_mifa(read_set(set_folder), read_records(set_folder), tmp_path)
        assert {p.name for p in paths.values()} == {
            "Study_idr0000.yaml", "Annotations_idr0000.yaml", "Version_idr0000.yaml"}
        annotations = yaml.safe_load(paths["annotations"].read_text())
        assert [f["annotation_id"] for f in annotations["file_metadata"]] == [
            "annotations/a1b2c3_mask.tif", "annotations/d4e5f6_mask.tif"]
        assert annotations["annotation_overview"].startswith("Instance masks of nuclei")
        assert annotations["file_metadata"][0]["annotation_type"] == ["segmentation_mask"]

    def test_uri_file_ids(self, set_folder, tmp_path):
        paths = save_mifa(read_set(set_folder), read_records(set_folder), tmp_path, file_ids="uri")
        first = yaml.safe_load(paths["annotations"].read_text())["file_metadata"][0]
        assert (first["annotation_id"], first["source_image_id"]) == ("a1b2c3", "omero:image:101")

    def test_method_text_holds_tool_model_and_split(self, set_folder):
        text = compose_method(read_set(set_folder), read_records(set_folder))
        assert "micro-sam 1.8.0" in text and "vit_b_lm" in text
        assert "1 training, 1 validation, assigned per well" in text

    def test_licence_outside_mifa_is_refused(self):
        assert map_license("CC0-1.0") == "CC0"
        with pytest.raises(ValueError):
            map_license("MIT")


class TestBiaBundle:
    def test_bundle_copies_annotated_files_and_lists_them(self, set_folder, tmp_path):
        result = save_bia_package(read_set(set_folder), read_records(set_folder), set_folder, tmp_path / "bia")
        bia = tmp_path / "bia"
        assert (result["copied"], result["missing"], result["n_annotations"]) == (4, 0, 2)
        assert (bia / "images/a1b2c3.tif").exists() and (bia / "annotations/d4e5f6_mask.tif").exists()
        assert (set_folder / "annotation_input/a1b2c3.tif").exists()  # copied, not moved
        with (bia / "file_list_annotations.tsv").open() as f:
            rows = list(csv.DictReader(f, delimiter="\t"))
        assert rows[0]["source_image"] == "images/a1b2c3.tif"
        assert "Channel" not in rows[0]  # same value everywhere, dropped
        assert rows[0]["pixel_sha256"].startswith("1a2b")

    def test_missing_file_is_skipped_with_a_warning(self, set_folder, tmp_path):
        (set_folder / "annotation_output/d4e5f6_mask.tif").unlink()
        with pytest.warns(UserWarning, match="1 file"):
            result = save_bia_package(read_set(set_folder), read_records(set_folder), set_folder, tmp_path / "bia")
        assert result["missing"] == 1
