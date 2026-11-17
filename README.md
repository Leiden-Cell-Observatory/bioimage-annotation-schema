# Bioimage Annotation Schema

An open schema for sets of image annotations made to train or evaluate AI models:
what was annotated, from which images, how, by whom, how the annotations are split,
and one record per annotation.

- **Source:** [`schema/bioimage_annotation_schema.yaml`](src/bioimage_annotation_schema/schema/bioimage_annotation_schema.yaml) (LinkML). Edit only this file.
- **Generated:** JSON Schema in [`schema/0.1/`](src/bioimage_annotation_schema/schema/0.1/) and Pydantic models in
  `bioimage_annotation_schema.datamodel` (`pixi run gen`).
- **Python library and `bas` command:** read, write and validate the documents, and export
  them to RO-Crate and to a BioImage Archive bundle with MIFA metadata.
- **Examples:** [`examples/0.1/`](examples/0.1/): an annotation set (YAML) and its records (CSV).
- **MIFA:** fields that correspond to MIFA ([bia-mifa-models](https://github.com/BioImage-Archive/bia-mifa-models),
  BioImage Archive) carry LinkML mappings to it, and `annotation_types` uses MIFA's values.

Status: **draft 0.1**. Fields may still change between 0.x releases.

## Two documents

| Document | Class | One per | Typical file |
|---|---|---|---|
| Annotation set | `AnnotationSet` | set | `annotation-set.yaml` |
| Annotation record | `AnnotationRecord` | annotation | a row of `annotation-records.csv` |

## A set's folder

```
annotation-set.yaml          # AnnotationSet
annotation-records.csv       # AnnotationRecord per row
annotation_input/…           # files the records point to (input_file, mask_file)
annotation_output/…
```

## Try it

`pixi run tour` opens [`notebooks/tour.py`](notebooks/tour.py), a hands-on marimo walk
through reading, breaking, building and exporting a set.

## Use

```bash
bas validate my-set/             # check both documents
bas ro-crate my-set/             # write my-set/ro-crate-metadata.json
bas bia my-set/ bia-bundle/      # BioImage Archive bundle: MIFA YAML, file lists, data
```

```python
from bioimage_annotation_schema import read_set, read_records, write_set, write_records
from bioimage_annotation_schema.crate import write_ro_crate
from bioimage_annotation_schema.mifa import save_bia_package

annotation_set, records = read_set("my-set"), read_records("my-set")   # validated
write_ro_crate(annotation_set, records, "my-set")
```

Any JSON Schema validator works too, as does
`linkml-validate -s <schema yaml> -C AnnotationSet annotation-set.yaml`.

The MIFA export needs `bia-mifa-models`, which is not on PyPI:
`pip install "git+https://github.com/BioImage-Archive/bia-mifa-models.git@v1.1.5"`.

## Develop

```bash
pixi run gen    # regenerate JSON Schema and Pydantic models after editing the LinkML file
pixi run test   # examples validate; broken examples are rejected
```

## Implementations

- [omero-annotate-ai](https://github.com/Leiden-Cell-Observatory/omero_annotate_ai): annotation of OMERO and OME-Zarr images with micro-SAM and Cellpose (export in progress).

## License

Schema and documentation: [CC-BY-4.0](LICENSE).
