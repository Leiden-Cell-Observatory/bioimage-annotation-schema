import marimo

__generated_with = "0.17.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import json
    import shutil
    import subprocess
    import tempfile
    from datetime import datetime, timezone
    from pathlib import Path

    import marimo as mo
    import polars as pl
    import yaml

    import bioimage_annotation_schema as bas
    from bioimage_annotation_schema import datamodel
    from bioimage_annotation_schema.crate import write_ro_crate
    from bioimage_annotation_schema.mifa import compose_method, save_bia_package
    return (
        Path,
        bas,
        compose_method,
        datamodel,
        datetime,
        json,
        mo,
        pl,
        save_bia_package,
        shutil,
        subprocess,
        tempfile,
        timezone,
        write_ro_crate,
        yaml,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # A tour of the Bioimage Annotation Schema

    The schema describes a **set of image annotations made for AI training** with two documents:

    | File | Model | What it holds |
    |---|---|---|
    | `annotation-set.yaml` | `AnnotationSet` | one per set: study, source data, method, classes, sampling, split, sessions |
    | `annotation-records.csv` | `AnnotationRecord` | one row per annotation: image, plane, split, status, files, pixel digests |

    Both live in one folder, next to the image and mask files the records point to.
    This notebook copies the example set to a temporary folder, so you can change things freely.
    """)
    return


@app.cell
def _(Path, shutil, tempfile):
    examples = Path(__file__).parent.parent / "examples" / "0.1"
    folder = Path(tempfile.mkdtemp()) / "my-set"
    folder.mkdir()
    for _name in ("annotation-set.yaml", "annotation-records.csv"):
        shutil.copy(examples / _name, folder)
    # Stand-ins for the image and mask files of the two annotated records.
    for _id in ("a1b2c3", "d4e5f6"):
        for _rel in (f"annotation_input/{_id}.tif", f"annotation_output/{_id}_mask.tif"):
            (folder / _rel).parent.mkdir(exist_ok=True)
            (folder / _rel).write_bytes(b"II*\x00 placeholder")
    sorted(str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file())
    return examples, folder


@app.cell
def _(mo):
    mo.md(r"""
    ## 1 · Read a set

    `read_set` and `read_records` read **and validate**. What you get back are Pydantic models
    generated from the LinkML schema, so fields autocomplete and have types.
    """)
    return


@app.cell
def _(bas, folder, mo):
    annotation_set = bas.read_set(folder)
    records = bas.read_records(folder)
    mo.vstack(
        [
            mo.md(
                f"**{annotation_set.name}** · {len(records)} records · "
                f"criteria: *{annotation_set.methodology.criteria}*"
            ),
            mo.tree(annotation_set.model_dump(mode="json", exclude_none=True)),
        ]
    )
    return annotation_set, records


@app.cell
def _(pl, records):
    pl.DataFrame([r.model_dump(mode="json", exclude_none=True) for r in records])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 2 · Break it on purpose

    Pick a mistake. The cell below applies it to a copy of the example and shows what
    validation reports. Note that some rules span several fields (an excluded annotation
    cannot have a mask); those come from the JSON Schema that LinkML generated.
    """)
    return


@app.cell
def _(mo):
    mistake = mo.ui.dropdown(
        options=[
            "typo in a key (coverag)",
            "wrong schema_version",
            "missing required criteria",
            "excluded record that still has a mask",
            "text in a number column",
            "patch without width and height",
            "duplicate annotation_id",
        ],
        value="typo in a key (coverag)",
        label="Mistake",
    )
    mistake
    return (mistake,)


@app.cell
def _(bas, examples, mistake, mo, yaml):
    _set = yaml.safe_load((examples / "annotation-set.yaml").read_text())
    _rows = [
        {"annotation_id": "a", "image_uri": "omero:image:1", "split": "training", "status": "pending"}
    ]
    _choice = mistake.value
    if _choice.startswith("typo"):
        _set["methodology"]["coverag"] = _set["methodology"].pop("coverage")
    elif _choice.startswith("wrong"):
        _set["schema_version"] = "0.2.0"
    elif _choice.startswith("missing"):
        del _set["methodology"]["criteria"]
    elif _choice.startswith("excluded"):
        _rows[0].update(status="excluded", mask_file="annotation_output/a_mask.tif")
    elif _choice.startswith("text"):
        _rows[0]["channel"] = "DAPI"
    elif _choice.startswith("patch"):
        _rows[0]["patch_x"] = 0
    else:
        _rows.append(dict(_rows[0]))

    _problems = []
    for _check, _data in ((bas.parse_set, _set), (bas.parse_records, _rows)):
        try:
            _check(_data)
        except bas.SchemaError as _error:
            _problems += _error.problems
    mo.md("\n".join(f"- `{p}`" for p in _problems) or "No problems found.")
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 3 · Build a set in code

    This is what a tool does (omero-annotate-ai, a QuPath extension, your own script):
    fill the models, then write. `write_set` and `write_records` validate before writing,
    so a tool cannot produce an invalid folder.
    """)
    return


@app.cell
def _(Path, bas, datamodel, datetime, mo, tempfile, timezone):
    new_set = datamodel.AnnotationSet(
        schema_version="0.1.0",
        name="my-first-set",
        created=datetime.now(timezone.utc),
        license="CC0-1.0",
        methodology=datamodel.Methodology(
            annotation_types=["point_annotations"],
            method="manual",
            criteria="One point at the centre of each mitotic cell.",
        ),
        classes=[datamodel.AnnotationClass(name="mitotic cell", color="#E4685D")],
    )
    new_records = [
        datamodel.AnnotationRecord(
            annotation_id="p1", image_uri="https://example.org/plate.zarr/A/1/0",
            split="training", status="pending", timepoint=3,
        )
    ]
    _out = Path(tempfile.mkdtemp())
    bas.write_set(new_set, _out)
    bas.write_records(new_records, _out)
    mo.hstack(
        [
            mo.md(f"```yaml\n{(_out / bas.SET_FILE).read_text()}```"),
            mo.md(f"```\n{(_out / bas.RECORDS_FILE).read_text()}```"),
        ],
        widths="equal",
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 4 · Why LinkML: the link to MIFA

    The schema's source is one LinkML YAML file. Fields that mean the same as a MIFA field
    say so with `exact_mappings`. This table is read straight from that file, so it is the
    crosswalk the paper can cite and the MIFA export follows.
    """)
    return


@app.cell
def _(bas, pl, yaml):
    from importlib.resources import files as _files

    _schema = yaml.safe_load(
        _files(bas).joinpath("schema", "bioimage_annotation_schema.yaml").read_text()
    )
    _rows = []
    for _cls, _spec in _schema["classes"].items():
        for _slot, _attr in (_spec.get("attributes") or {}).items():
            for _kind in ("exact_mappings", "close_mappings"):
                for _target in (_attr or {}).get(_kind, []):
                    _rows.append(
                        {"class": _cls, "field": _slot,
                         "link": _kind.split("_")[0], "maps to": _target}
                    )
    pl.DataFrame(_rows).filter(pl.col("maps to").str.starts_with("mifa:"))
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 5 · Export: RO-Crate

    One call writes `ro-crate-metadata.json`: the folder's files, which source image each
    mask is based on, the pixel digests, and each session as an action (who, when, with
    which model). Repositories and workflow tools read this format.
    """)
    return


@app.cell
def _(annotation_set, folder, json, pl, records, write_ro_crate):
    _crate = json.loads(write_ro_crate(annotation_set, records, folder).read_text())
    pl.DataFrame(
        [
            {"@id": e["@id"], "@type": str(e["@type"]), "name": e.get("name", "")}
            for e in _crate["@graph"]
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 6 · Export: BioImage Archive bundle with MIFA

    `save_bia_package` writes the three MIFA documents, the two file lists the BioImage
    Archive asks for, and copies the annotated images and masks. Only annotated records
    go in; pending and excluded ones stay out. MIFA's free-text `annotation_method` is
    written from the structured fields:
    """)
    return


@app.cell
def _(annotation_set, compose_method, mo, records):
    mo.callout(mo.md(compose_method(annotation_set, records)), kind="info")
    return


@app.cell
def _(annotation_set, folder, mo, records, save_bia_package):
    bundle = folder.parent / "bia-bundle"
    _result = save_bia_package(annotation_set, records, folder, bundle)
    mo.vstack(
        [
            mo.md(
                f"{_result['n_annotations']} annotations, {_result['copied']} files copied, "
                f"{_result['missing']} missing"
            ),
            mo.tree(sorted(str(p.relative_to(bundle)) for p in bundle.rglob("*") if p.is_file())),
            mo.md(f"```yaml\n{_result['metadata']['annotations'].read_text()}```"),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 7 · From any language: the `bas` command

    A QuPath extension or an R script does not need this Python library: it writes the two
    files, then calls the command line (or any JSON Schema validator).

    ```bash
    bas validate my-set/
    bas ro-crate my-set/
    bas bia my-set/ bia-bundle/
    ```
    """)
    return


@app.cell
def _(folder, mo, subprocess):
    _run = subprocess.run(["bas", "validate", str(folder)], capture_output=True, text=True)
    mo.md(f"```\n$ bas validate {folder.name}/\n{_run.stdout}{_run.stderr}```")
    return


if __name__ == "__main__":
    app.run()
