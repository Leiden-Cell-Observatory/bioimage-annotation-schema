"""RO-Crate description of a set's folder."""

import json

from bioimage_annotation_schema import read_records, read_set
from bioimage_annotation_schema.crate import METADATA_FILE, PROFILE, SPEC, build_ro_crate, write_ro_crate
from bioimage_annotation_schema.datamodel import CodeMethod, ContentCodes


def _crate(folder):
    path = write_ro_crate(read_set(folder), read_records(folder), folder)
    crate = json.loads(path.read_text(encoding="utf-8"))
    return crate, {e["@id"]: e for e in crate["@graph"]}


def _many(value):
    return value if isinstance(value, list) else [value]


def _refs(value):
    if isinstance(value, dict):
        return [value["@id"]] if set(value) == {"@id"} else []
    if isinstance(value, list):
        return [ref for item in value for ref in _refs(item)]
    return []


class TestRoCrate:
    def test_descriptor_and_root_follow_the_spec(self, set_folder):
        crate, by_id = _crate(set_folder)
        assert crate["@context"] == f"{SPEC}/context"
        assert by_id[METADATA_FILE]["conformsTo"] == {"@id": SPEC}
        root = by_id["./"]
        assert root["name"] == "u2os-nuclei-hcs"
        assert root["conformsTo"] == {"@id": PROFILE}
        assert root["license"] == {"@id": "https://spdx.org/licenses/CC-BY-4.0"}
        author = by_id["https://orcid.org/0000-0002-1825-0097"]
        assert author["name"] == "Jane van Example"
        assert author["affiliation"] == {"@id": "https://ror.org/027bh9e22"}

    def test_every_reference_is_defined(self, set_folder):
        _, by_id = _crate(set_folder)
        for entity in by_id.values():
            for key, value in entity.items():
                if key != "conformsTo" or entity["@id"] != METADATA_FILE:
                    assert all(ref in by_id for ref in _refs(value)), (entity["@id"], key)

    def test_masks_point_to_their_images_and_carry_digests(self, set_folder):
        _, by_id = _crate(set_folder)
        mask = by_id["annotation_output/a1b2c3_mask.tif"]
        assert {"@id": "annotation_input/a1b2c3.tif"} in _many(mask["isBasedOn"])
        assert {"@id": "omero:image:101"} in _many(mask["isBasedOn"])
        digest = by_id[mask["identifier"]["@id"]]
        assert digest["propertyID"] == "pixel-sha256"

    def test_split_is_in_the_graph_with_its_files_and_how_it_was_made(self, set_folder):
        crate, by_id = _crate(set_folder)
        split = by_id["#split"]
        assert {"@id": "#split"} in _many(by_id["./"]["mentions"])
        assert split["description"] == (
            "Assigned per well; fields within a well show the same cells' neighbourhood; "
            "strategy random_split; balanced on treatment; seed 42."
        )
        assert _many(split["hasPart"]) == [{"@id": "#split-training"}, {"@id": "#split-validation"}]
        assert _many(by_id["#split-training"]["hasPart"]) == [
            {"@id": "annotation_input/a1b2c3.tif"},
            {"@id": "annotation_output/a1b2c3_mask.tif"},
        ]
        assert {"@id": "annotation_output/d4e5f6_mask.tif"} in by_id["#split-validation"]["hasPart"]

    def test_excluded_and_pending_units_list_no_mask(self, set_folder):
        _, by_id = _crate(set_folder)
        assert not any("g7h8i9" in i or "j0k1l2" in i for i in by_id if i.endswith(".tif"))

    def test_sessions_are_actions_with_agent_note_and_results(self, set_folder):
        _, by_id = _crate(set_folder)
        action = by_id["#session-1"]
        assert action["@type"] == "CreateAction"
        assert action["description"] == "first pass, control wells"
        assert by_id[action["agent"]["@id"]]["name"] == "jexample"
        assert len(_many(action["result"])) == 2

    def test_files_outside_the_folder_are_never_listed(self, set_folder, tmp_path):
        outside = tmp_path / "secret.tif"
        outside.write_bytes(b"x")
        path = set_folder / "annotation-records.csv"
        path.write_text(path.read_text().replace("annotation_input/a1b2c3.tif", "../secret.tif"))
        _, by_id = _crate(set_folder)
        assert not any("secret" in i for i in by_id)

    def test_local_source_paths_are_replaced_by_an_id(self, set_folder):
        path = set_folder / "annotation-records.csv"
        path.write_text(path.read_text().replace("omero:image:101", "/home/jane/plate.zarr/B/2/0"))
        _, by_id = _crate(set_folder)
        assert not any("/home/jane" in json.dumps(e) for e in by_id.values())

    def test_omero_sources_name_their_server(self, set_folder):
        by_id = {
            e["@id"]: e
            for e in build_ro_crate(read_set(set_folder), read_records(set_folder), set_folder)["@graph"]
        }
        assert by_id["omero:image:101"]["isPartOf"] == {"@id": "#omero-server"}
        assert by_id["#omero-server"]["url"] == "https://idr.openmicroscopy.org/webclient/"

    def test_iscc_codes_say_how_they_were_made(self, set_folder):
        annotation_set, records = read_set(set_folder), read_records(set_folder)
        annotation_set.content_codes = ContentCodes(
            region=CodeMethod(
                code_type="image_code", pixels="the region", preparation="none", implementation="tool 1"
            )
        )
        records[0] = records[0].model_copy(
            update={"input_iscc": "ISCC:EEA4GQZQTY6J5DTH", "image_iscc": "ISCC:KAA4GQZQTY6J5DTH"}
        )
        by_id = {e["@id"]: e for e in build_ro_crate(annotation_set, records, set_folder)["@graph"]}
        code = by_id["#a1b2c3-input-iscc"]
        assert code["name"] == "ISCC image_code of the region; none (tool 1)"
        assert by_id["omero:image:101"]["identifier"] == "ISCC:KAA4GQZQTY6J5DTH"

