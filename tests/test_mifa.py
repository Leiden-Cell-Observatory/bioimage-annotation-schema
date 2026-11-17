"""MIFA documents and the BioImage Archive bundle."""

import csv
import importlib.resources
import subprocess

import pytest
import yaml

from bioimage_annotation_schema import read_records, read_set
from bioimage_annotation_schema.mifa import (
    MifaNotReady,
    check_mifa,
    compose_method,
    compose_overview,
    save_bia_package,
    save_mifa,
)

MIFA_SCHEMA = importlib.resources.files("bia_mifa_models") / "schema" / "bia_mifa_models.yaml"


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

    @pytest.mark.parametrize("key,target", [("study", "Study"), ("annotations", "Annotations"),
                                            ("version", "Version")])
    def test_documents_pass_mifa_own_validator(self, set_folder, tmp_path, key, target):
        path = save_mifa(read_set(set_folder), read_records(set_folder), tmp_path)[key]
        result = subprocess.run(
            ["linkml-validate", "-s", str(MIFA_SCHEMA), "-C", target, str(path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    def test_every_recorded_fact_reaches_mifa(self, set_folder, tmp_path):
        paths = save_mifa(read_set(set_folder), read_records(set_folder), tmp_path)
        study = yaml.safe_load(paths["study"].read_text())
        author = study["authors"][0]
        assert (author["author_first_name"], author["author_last_name"]) == ("Jane", "van Example")
        assert author["organisation"][0]["ror_id"] == "https://ror.org/027bh9e22"
        assert study["grants"] == [{"grant_id": "ERC-123", "funder": "Example Research Council"}]
        # LinkML writes publications keyed by their DOI; MIFA's year is text
        publication = study["publications"]["https://doi.org/10.1000/example"]
        assert (publication["publication_title"], publication["publication_year"]) == (
            "An example study of nuclear morphology", "2026")
        assert study["license"] == "CC_BY"
        assert study["link_url"][0] == "https://github.com/example/u2os-nuclei"
        assert study["ai_models_trained"] == ["https://doi.org/10.5281/zenodo.0000000"]
        version = yaml.safe_load(paths["version"].read_text())
        assert version["version"] == "1"
        assert version["timestamp"].startswith("2026-11-10T15:20")  # session end

    def test_missing_mifa_fields_are_named_not_invented(self, set_folder, tmp_path):
        path = set_folder / "annotation-set.yaml"
        data = yaml.safe_load(path.read_text())
        del data["study"]["funding_statement"], data["keywords"], data["version"]
        path.write_text(yaml.safe_dump(data))
        annotation_set = read_set(set_folder)  # still a valid set
        assert check_mifa(annotation_set) == ["study.funding_statement", "keywords", "version"]
        with pytest.raises(MifaNotReady) as error:
            save_mifa(annotation_set, read_records(set_folder), tmp_path / "mifa")
        assert "keywords" in error.value.missing
        with pytest.raises(MifaNotReady):
            save_bia_package(annotation_set, read_records(set_folder), set_folder, tmp_path / "bia")
        assert not (tmp_path / "mifa").exists() and not (tmp_path / "bia").exists()

    def test_composed_overview_names_ontology_terms_when_given(self, set_folder):
        annotation_set = read_set(set_folder)
        annotation_set.methodology.overview = None
        overview = compose_overview(annotation_set)
        assert "Organism: Homo sapiens (http://purl.obolibrary.org/obo/NCBITaxon_9606)." in overview
        assert (
            "Imaging method: widefield fluorescence microscopy"
            " (http://purl.obolibrary.org/obo/FBbi_00100013)." in overview
        )
        annotation_set.study.organism_term = annotation_set.study.imaging_method_term = None
        overview = compose_overview(annotation_set)
        assert "Organism: Homo sapiens. Imaging method: widefield fluorescence microscopy." in overview


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
