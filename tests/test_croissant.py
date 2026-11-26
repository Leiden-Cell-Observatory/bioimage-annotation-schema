"""Croissant (MLCommons) description of a set's folder."""

import json

import pytest
import yaml

from bioimage_annotation_schema import read_records, read_set
from bioimage_annotation_schema.cli import main
from bioimage_annotation_schema.crate import PROFILE
from bioimage_annotation_schema.croissant import (
    METADATA_FILE,
    RAI_SPEC,
    SPEC,
    CroissantNotReady,
    check_croissant,
    write_croissant,
)


def _croissant(folder):
    path = write_croissant(read_set(folder), read_records(folder), folder)
    return json.loads(path.read_text(encoding="utf-8"))


def _by_id(items):
    return {item["@id"]: item for item in items}


def _edit_set(folder, change):
    path = folder / "annotation-set.yaml"
    data = yaml.safe_load(path.read_text())
    change(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


class TestCroissant:
    def test_dataset_level_metadata(self, set_folder):
        doc = _croissant(set_folder)
        assert doc["@type"] == "sc:Dataset"
        assert {SPEC, RAI_SPEC} <= set(doc["conformsTo"])
        assert doc["name"] == "u2os-nuclei-hcs"
        assert doc["description"].startswith("Nuclei in a U2OS")
        assert doc["license"] == "https://spdx.org/licenses/CC-BY-4.0"
        assert doc["url"] == "https://doi.org/10.5281/zenodo.0000001"
        assert (doc["version"], doc["keywords"][0]) == ("1", "nuclei")
        assert doc["dateCreated"] == "2026-11-10T14:02:00+01:00"
        creator = doc["creator"][0]
        assert creator["@id"] == "https://orcid.org/0000-0002-1825-0097"
        assert (creator["givenName"], creator["familyName"]) == ("Jane", "van Example")
        assert creator["affiliation"][0]["@id"] == "https://ror.org/027bh9e22"
        assert doc["citation"][0]["@id"] == "https://doi.org/10.1000/example"
        assert doc["citeAs"].startswith("@misc{vanExample2026,\n")
        assert "  author = {van Example, Jane}" in doc["citeAs"]
        assert "  doi = {10.5281/zenodo.0000001}" in doc["citeAs"]
        assert doc["funding"][0]["identifier"] == "ERC-123"
        assert doc["prov:wasDerivedFrom"]["identifier"] == "idr0000"

    def test_distribution_lists_the_documents_and_the_paired_files(self, set_folder):
        files = _by_id(_croissant(set_folder)["distribution"])
        assert files["records-file"]["contentUrl"] == "annotation-records.csv"
        assert len(files["records-file"]["sha256"]) == 64
        assert files["set-file"]["contentUrl"] == "annotation-set.yaml"
        assert files["set-file"]["conformsTo"] == PROFILE
        assert files["mask-files"]["@type"] == "cr:FileSet"
        assert files["mask-files"]["encodingFormat"] == "image/tiff"

    def test_records_without_a_mask_are_left_out_of_the_pairing(self, set_folder):
        files = _by_id(_croissant(set_folder)["distribution"])
        assert files["mask-files"]["includes"] == [
            "annotation_output/a1b2c3_mask.tif", "annotation_output/d4e5f6_mask.tif"]
        assert files["image-files"]["includes"] == [
            "annotation_input/a1b2c3.tif", "annotation_input/d4e5f6.tif"]

    def test_a_mask_file_that_is_not_in_the_folder_is_left_out(self, set_folder):
        (set_folder / "annotation_output/d4e5f6_mask.tif").unlink()
        files = _by_id(_croissant(set_folder)["distribution"])
        assert files["mask-files"]["includes"] == ["annotation_output/a1b2c3_mask.tif"]
        assert files["image-files"]["includes"] == ["annotation_input/a1b2c3.tif"]

    def test_annotations_pair_each_mask_with_the_record_columns(self, set_folder):
        record_sets = _by_id(_croissant(set_folder)["recordSet"])
        fields = _by_id(record_sets["annotations"]["field"])
        mask = fields["annotations/mask"]
        assert mask["dataType"] == ["sc:ImageObject", "cr:Label", "cr:SegmentationMask"]
        assert mask["source"] == {
            "fileSet": {"@id": "mask-files"}, "extract": {"fileProperty": "content"}}
        assert "Instance mask" in mask["description"]
        # the mask's path joins the mask files to the rows of the records table
        assert fields["annotations/mask_file"]["references"] == {
            "fileObject": {"@id": "records-file"}, "extract": {"column": "mask_file"}}
        for column in ("well", "field", "well_metadata", "channel", "timepoint", "z_slice",
                       "image_uri", "input_file"):
            assert fields[f"annotations/{column}"]["source"]["extract"] == {"column": column}
        assert fields["annotations/timepoint"]["dataType"] == "sc:Integer"
        assert fields["annotations/created_at"]["dataType"] == "sc:DateTime"
        assert "annotations/z_start" not in fields  # a column the records do not use

    def test_images_are_a_record_set_keyed_like_the_annotations(self, set_folder):
        images = _by_id(_croissant(set_folder)["recordSet"])["images"]
        fields = _by_id(images["field"])
        assert fields["images/image"]["dataType"] == "sc:ImageObject"
        assert fields["images/input_file"]["references"]["extract"] == {"column": "input_file"}
        assert fields["images/annotation_id"]["source"]["extract"] == {"column": "annotation_id"}

    def test_masks_without_a_local_image_still_pair_with_the_source_image(self, set_folder):
        for image in (set_folder / "annotation_input").iterdir():
            image.unlink()
        doc = _croissant(set_folder)
        assert "image-files" not in _by_id(doc["distribution"])
        record_sets = _by_id(doc["recordSet"])
        assert "images" not in record_sets
        assert "annotations/image_uri" in _by_id(record_sets["annotations"]["field"])

    def test_split_follows_the_croissant_recommendation(self, set_folder):
        record_sets = _by_id(_croissant(set_folder)["recordSet"])
        splits = record_sets["splits"]
        assert splits["dataType"] == "cr:Split"
        assert splits["key"] == {"@id": "splits/name"}
        assert {"splits/name": "validation", "splits/url": "cr:ValidationSplit"} in splits["data"]
        split = _by_id(record_sets["annotations"]["field"])["annotations/split"]
        assert split["references"] == {"field": {"@id": "splits/name"}}

    def test_fields_without_a_croissant_property_are_not_dropped(self, set_folder):
        doc = _croissant(set_folder)
        record_sets = _by_id(doc["recordSet"])
        # split unit and rationale: in words on the splits, and as data
        assert "assigned per well" in record_sets["splits"]["description"]
        assert doc["bas:split"]["bas:unit"] == "well"
        assert doc["bas:split"]["bas:rationale"].startswith("fields within a well")
        assert doc["bas:split"]["bas:seed"] == 42
        # label channel and model input channels
        assert doc["bas:sampling"]["bas:label_channel"] == 0
        assert doc["bas:sampling"]["bas:input_channels"] == [1]
        # normalisation: RAI text and data
        assert "percentiles 1.0-99.8" in doc["rai:dataPreprocessingProtocol"][0]
        assert doc["bas:normalization"]["bas:percentile_high"] == 99.8
        # methodology: RAI text and data
        assert "Every in-focus nucleus" in doc["rai:dataAnnotationProtocol"]
        assert doc["rai:dataAnnotationPlatform"] == ["micro-sam 1.8.0"]
        assert doc["rai:machineAnnotationTools"] == ["vit_b_lm"]
        assert doc["bas:methodology"]["bas:tools"][0]["sc:name"] == "micro-sam"
        # tool-specific metadata, as a JSON literal
        assert doc["bas:extensions"]["@value"]["omero-annotate-ai"]["table_id"] == 1234

    def test_sessions_are_a_record_set_the_annotations_refer_to(self, set_folder):
        record_sets = _by_id(_croissant(set_folder)["recordSet"])
        sessions = record_sets["sessions"]
        assert sessions["dataType"] == "prov:Activity"
        row = sessions["data"][0]
        assert (row["sessions/id"], row["sessions/annotator"]) == (1, "jexample")
        assert row["sessions/note"] == "first pass, control wells"
        fields = _by_id(sessions["field"])
        assert fields["sessions/started"]["equivalentProperty"] == "prov:startedAtTime"
        session = _by_id(record_sets["annotations"]["field"])["annotations/session"]
        assert session["references"] == {"field": {"@id": "sessions/id"}}

    def test_classes_are_an_enumeration(self, set_folder):
        classes = _by_id(_croissant(set_folder)["recordSet"])["classes"]
        assert classes["dataType"] == "sc:Enumeration"
        assert classes["data"] == [{
            "classes/name": "nucleus",
            "classes/color": "#0FA3B1",
            "classes/url": "http://purl.obolibrary.org/obo/GO_0005634",
        }]

    @pytest.mark.parametrize("key,named", [("description", "description"), ("authors", "authors"),
                                           ("url", "url")])
    def test_a_set_missing_a_required_field_is_refused(self, set_folder, key, named):
        _edit_set(set_folder, lambda data: data.pop(key))
        annotation_set = read_set(set_folder)
        assert check_croissant(annotation_set) == [named]
        with pytest.raises(CroissantNotReady, match=named) as error:
            write_croissant(annotation_set, read_records(set_folder), set_folder)
        assert error.value.missing == [named]
        assert not (set_folder / METADATA_FILE).exists()

    def test_a_folder_without_mask_files_is_refused(self, set_folder):
        for mask in (set_folder / "annotation_output").iterdir():
            mask.unlink()
        with pytest.raises(CroissantNotReady, match="mask files"):
            write_croissant(read_set(set_folder), read_records(set_folder), set_folder)

    def test_command_line(self, set_folder, capsys):
        assert main(["croissant", str(set_folder)]) == 0
        assert capsys.readouterr().out.strip().endswith(METADATA_FILE)
        _edit_set(set_folder, lambda data: data.pop("authors"))
        assert main(["croissant", str(set_folder)]) == 1
        assert "authors" in capsys.readouterr().err


class TestOfficialValidator:
    """The file loads in mlcroissant, MLCommons' reference implementation."""

    @pytest.fixture
    def dataset(self, set_folder):
        mlc = pytest.importorskip("mlcroissant", reason="mlcroissant is not installed")
        image = pytest.importorskip("PIL.Image", reason="Pillow is not installed")
        for path in sorted(set_folder.glob("annotation_*/*.tif")):  # real, tiny TIFFs
            image.new("L", (4, 4), 1 if "mask" in path.name else 0).save(path)
        path = write_croissant(read_set(set_folder), read_records(set_folder), set_folder)
        return mlc.Dataset(jsonld=str(path))

    def test_sessions_and_classes_with_different_fields_still_load(self, set_folder):
        mlc = pytest.importorskip("mlcroissant", reason="mlcroissant is not installed")

        def add(data):
            data["sessions"].append(
                {"id": 2, "kind": "review", "started": "2026-11-11T10:00:00+01:00"})
            data["classes"].append({"name": "cell", "label_value": 2})

        _edit_set(set_folder, add)
        path = write_croissant(read_set(set_folder), read_records(set_folder), set_folder)
        dataset = mlc.Dataset(jsonld=str(path))
        assert not dataset.metadata.ctx.issues.errors
        assert [row["sessions/id"] for row in dataset.records("sessions")] == [1, 2]
        assert [row["classes/name"] for row in dataset.records("classes")] == ["nucleus", "cell"]

    def test_no_errors(self, dataset):
        assert not dataset.metadata.ctx.issues.errors
        assert not dataset.metadata.ctx.issues.warnings

    def test_annotations_load_with_mask_split_and_metadata(self, dataset):
        rows = list(dataset.records("annotations"))
        assert [row["annotations/annotation_id"] for row in rows] == [b"a1b2c3", b"d4e5f6"]
        assert [row["annotations/split"] for row in rows] == [b"training", b"validation"]
        assert rows[0]["annotations/well"] == b"B2" and rows[0]["annotations/timepoint"] == 0
        assert rows[0]["annotations/mask"].size == (4, 4)
        assert rows[0]["annotations/input_file"] == b"annotation_input/a1b2c3.tif"

    def test_images_load_with_the_id_of_their_annotation(self, dataset):
        rows = list(dataset.records("images"))
        assert [row["images/input_file"] for row in rows] == [
            b"annotation_input/a1b2c3.tif", b"annotation_input/d4e5f6.tif"]
        assert rows[0]["images/image"].size == (4, 4)
        assert rows[0]["images/annotation_id"] == b"a1b2c3"

    def test_splits_sessions_and_classes_load(self, dataset):
        assert [row["splits/name"] for row in dataset.records("splits")] == [
            "training", "validation", "test"]
        assert next(iter(dataset.records("sessions")))["sessions/annotator"] == "jexample"
        assert next(iter(dataset.records("classes")))["classes/name"] == "nucleus"
