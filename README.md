# Bioimage Annotation Schema

An open schema for sets of image annotations made to train or evaluate AI models:
what was annotated, from which images, how, by whom, how the annotations are split,
and one record per annotation.

- **Source:** [`schema/bioimage_annotation_schema.yaml`](src/bioimage_annotation_schema/schema/bioimage_annotation_schema.yaml) (LinkML). Edit only this file.
- **Generated:** JSON Schema in [`schema/0.1/`](src/bioimage_annotation_schema/schema/0.1/) and Pydantic models in
  `bioimage_annotation_schema.datamodel` (`pixi run gen`).
- **Python library and `bas` command:** read, write and validate the documents, and export
  them to RO-Crate, to Croissant (MLCommons), to a bioimage.io dataset description and to a
  BioImage Archive bundle with MIFA metadata.
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
bas validate --mifa my-set/      # also list what MIFA still needs (funding, keywords, …)
bas ro-crate my-set/             # write my-set/ro-crate-metadata.json
bas croissant my-set/            # write my-set/croissant.json (Croissant 1.1, with RAI)
bas bioimageio my-set/           # write my-set/rdf.yaml (bioimage.io dataset 0.3)
bas bia my-set/ bia-bundle/      # BioImage Archive bundle: MIFA YAML, file lists, data
```

```python
from bioimage_annotation_schema import read_set, read_records, write_set, write_records
from bioimage_annotation_schema.bioimageio import write_bioimageio_dataset
from bioimage_annotation_schema.crate import write_ro_crate
from bioimage_annotation_schema.croissant import write_croissant
from bioimage_annotation_schema.mifa import save_bia_package

annotation_set, records = read_set("my-set"), read_records("my-set")   # validated
write_ro_crate(annotation_set, records, "my-set")
write_croissant(annotation_set, records, "my-set")
write_bioimageio_dataset(annotation_set, records, "my-set")
```

Any JSON Schema validator works too, as does
`linkml-validate -s <schema yaml> -C AnnotationSet annotation-set.yaml`.

Every MIFA field has a place in the schema. The MIFA export writes only what the set
records: when MIFA requires something the set lacks, the export names it and stops,
rather than filling in a placeholder. The written documents pass MIFA's own
`linkml-validate` check.

The MIFA export needs `bia-mifa-models`, which is not on PyPI:
`pip install "git+https://github.com/BioImage-Archive/bia-mifa-models.git@v1.1.5"`.

The Croissant and bioimage.io exports follow the same rule: a set that lacks what the
format asks for (a description, authors, the address of the set (`url`); for bioimage.io also keywords and a
publication with a DOI) is refused with the names of the missing fields.

- **Croissant** (`croissant.json`): the set as a `sc:Dataset`, its files, and record sets
  that load in [mlcroissant](https://pypi.org/project/mlcroissant/). `annotations` has one
  record per mask that is in the folder, with the columns of the records table; pending and
  excluded records are left out. The split is a `cr:Split` record set, the classes an
  enumeration, the sessions PROV activities. What Croissant has no property for
  (methodology, sampling, split unit and rationale, normalisation) is written in words
  under the Croissant RAI properties and as data under this schema's own terms (`bas:`).
- **bioimage.io** (`rdf.yaml`): name, description, authors, citations, licence, tags,
  version and source of a dataset description. The format has no fields for the rest, so
  the whole set is kept under `config.bioimage_annotation_schema` and the two documents
  are listed as attachments.

Neither export needs an extra package. The tests check the files with `mlcroissant` and
`bioimageio.spec`, which are in the pixi environment.

## Documentation

The [documentation site](https://wiki.cellobservatory.nl/bioimage-annotation-schema/)
has an overview of both documents as a tree, a class diagram you can zoom and pan,
an interactive model browser, the MIFA crosswalk and a reference page per class, field and value
list, all generated from the schema:

```bash
pixi run -e docs docs-serve   # http://127.0.0.1:8000
```

## Develop

```bash
pixi run gen    # regenerate JSON Schema and Pydantic models after editing the LinkML file
pixi run test   # examples validate; broken examples are rejected
pixi run -e docs docs-build   # documentation, built strictly (also in CI)
```

## Implementations

- [omero-annotate-ai](https://github.com/Leiden-Cell-Observatory/omero_annotate_ai): annotation of OMERO and OME-Zarr images with micro-SAM and Cellpose (export in progress).

## License

Schema and documentation: [CC-BY-4.0](LICENSE).
