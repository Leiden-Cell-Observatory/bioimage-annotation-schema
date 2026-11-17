"""Checks that span the set and its records: sessions and ISCC code methods."""

from bioimage_annotation_schema import check_documents, read_records, read_set
from bioimage_annotation_schema.cli import main
from bioimage_annotation_schema.datamodel import CodeMethod, ContentCodes

CODE = "ISCC:EEA4GQZQTY6J5DTH"
REGION = CodeMethod(
    code_type="image_code",
    bits=64,
    pixels="the annotated region as saved in input_file, and the mask",
    preparation="max projection, 32 x 32 area average, min-max stretch",
    implementation="example-tool 1.0 (iscc-lib 0.7.1)",
)


def _with_codes(set_folder, **codes):
    records = read_records(set_folder)
    records[0] = records[0].model_copy(update=codes)
    return read_set(set_folder), records


class TestCheckDocuments:
    def test_example_is_consistent(self, set_folder):
        assert check_documents(read_set(set_folder), read_records(set_folder)) == []

    def test_unknown_session_is_reported(self, set_folder):
        records = read_records(set_folder)
        records[0] = records[0].model_copy(update={"session": 99})
        assert check_documents(read_set(set_folder), records) == [
            "row 1: session 99 is not in the set's sessions"
        ]

    def test_region_codes_need_their_method(self, set_folder):
        annotation_set, records = _with_codes(set_folder, input_iscc=CODE)
        assert check_documents(annotation_set, records) == [
            "row 1: has region ISCC codes but content_codes.region is missing"
        ]
        annotation_set.content_codes = ContentCodes(region=REGION)
        assert check_documents(annotation_set, records) == []

    def test_image_code_needs_its_own_method(self, set_folder):
        annotation_set, records = _with_codes(set_folder, image_iscc=CODE)
        annotation_set.content_codes = ContentCodes(region=REGION)
        assert check_documents(annotation_set, records) == [
            "row 1: has image_iscc but content_codes.image is missing"
        ]

    def test_cli_validate_fails_on_inconsistent_documents(self, set_folder, capsys):
        path = set_folder / "annotation-records.csv"
        path.write_text(path.read_text().replace(",1,annotation_input/a1b2c3", ",7,annotation_input/a1b2c3"))
        assert main(["validate", str(set_folder)]) == 1
        assert "session 7" in capsys.readouterr().err
