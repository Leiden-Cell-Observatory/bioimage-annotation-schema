"""bioimage.io dataset description (``rdf.yaml``) of a set's folder."""

import pytest
import yaml

from bioimage_annotation_schema import read_records, read_set
from bioimage_annotation_schema.bioimageio import (
    CONFIG_KEY,
    FORMAT_VERSION,
    METADATA_FILE,
    BioimageioNotReady,
    check_bioimageio,
    write_bioimageio_dataset,
)
from bioimage_annotation_schema.cli import main


def _rdf(folder):
    path = write_bioimageio_dataset(read_set(folder), read_records(folder), folder)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _edit_set(folder, change):
    path = folder / "annotation-set.yaml"
    data = yaml.safe_load(path.read_text())
    change(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


class TestBioimageioDataset:
    def test_fields_of_the_dataset_description(self, set_folder):
        rdf = _rdf(set_folder)
        assert (rdf["type"], rdf["format_version"]) == ("dataset", FORMAT_VERSION)
        assert rdf["name"] == "u2os-nuclei-hcs"
        assert rdf["description"].startswith("Nuclei in a U2OS")
        assert rdf["license"] == "CC-BY-4.0"
        assert rdf["tags"] == ["nuclei", "segmentation", "high-content screening"]
        assert rdf["version"] == "1"
        assert rdf["source"] == "https://github.com/example/u2os-nuclei"
        assert rdf["authors"] == [{
            "name": "Jane van Example",
            "orcid": "0000-0002-1825-0097",
            "affiliation": "Example University",
        }]
        assert rdf["cite"] == [{
            "text": "J. van Example, A. Colleague (2026). An example study of nuclear morphology.",
            "doi": "10.1000/example",
        }]

    def test_the_documents_are_attached_with_their_checksums(self, set_folder):
        attachments = _rdf(set_folder)["attachments"]
        assert [a["source"] for a in attachments] == ["annotation-set.yaml", "annotation-records.csv"]
        assert all(len(a["sha256"]) == 64 for a in attachments)

    def test_the_whole_set_is_kept_under_config(self, set_folder):
        config = _rdf(set_folder)["config"][CONFIG_KEY]
        kept = config["annotation_set"]
        assert kept == yaml.safe_load((set_folder / "annotation-set.yaml").read_text())
        assert kept["split"]["unit"] == "well"
        assert (kept["sampling"]["label_channel"], kept["sampling"]["input_channels"]) == (0, [1])
        assert kept["normalization"]["percentile_high"] == 99.8
        assert kept["sessions"][0]["note"] == "first pass, control wells"
        assert config["annotated_records"] == {"training": 1, "validation": 1}

    def test_changes_are_the_version_comment(self, set_folder):
        _edit_set(set_folder, lambda data: data.update(changes="Added the validation wells."))
        assert _rdf(set_folder)["version_comment"] == "Added the validation wells."

    @pytest.mark.parametrize("key,named", [
        ("description", "description"),
        ("authors", "authors"),
        ("keywords", "keywords"),
        ("links", "links"),
        ("study", "study.publications (with a doi)"),
    ])
    def test_a_set_missing_a_required_field_is_refused(self, set_folder, key, named):
        _edit_set(set_folder, lambda data: data.pop(key))
        annotation_set = read_set(set_folder)
        assert check_bioimageio(annotation_set) == [named]
        with pytest.raises(BioimageioNotReady, match="missing") as error:
            write_bioimageio_dataset(annotation_set, read_records(set_folder), set_folder)
        assert error.value.missing == [named]
        assert not (set_folder / METADATA_FILE).exists()

    def test_a_name_bioimageio_does_not_accept_is_refused(self, set_folder):
        _edit_set(set_folder, lambda data: data.update(name="u2os/nuclei"))
        assert check_bioimageio(read_set(set_folder)) == [
            "name (5 to 128 letters, digits, spaces and _ + - ( ))"]

    def test_command_line(self, set_folder, capsys):
        assert main(["bioimageio", str(set_folder)]) == 0
        assert capsys.readouterr().out.strip().endswith(METADATA_FILE)
        _edit_set(set_folder, lambda data: data.pop("keywords"))
        assert main(["bioimageio", str(set_folder)]) == 1
        assert "keywords" in capsys.readouterr().err


class TestOfficialValidator:
    """The description validates with bioimageio.spec, the format's own library."""

    def test_valid_dataset_description(self, set_folder):
        spec = pytest.importorskip("bioimageio.spec", reason="bioimageio.spec is not installed")
        path = write_bioimageio_dataset(read_set(set_folder), read_records(set_folder), set_folder)
        description = spec.load_description(path)
        summary = description.validation_summary
        assert summary.status == "valid-format", summary.display()
        assert type(description).__name__ == "DatasetDescr"
        assert description.format_version == FORMAT_VERSION
        assert not [error for detail in summary.details for error in detail.errors]
        # the one thing bioimage.io recommends that a set cannot record
        warned = {warning.loc for detail in summary.details for warning in detail.warnings}
        assert warned == {("documentation",)}
