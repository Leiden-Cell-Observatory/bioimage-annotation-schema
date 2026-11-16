# Bioimage Annotation Schema

An open schema for sets of image annotations made to train or evaluate AI models:
what was annotated, from which images, how, by whom, how the annotations are split,
and one record per annotation.

- **Source:** [`src/linkml/bioimage_annotation_schema.yaml`](src/linkml/bioimage_annotation_schema.yaml) (LinkML). Edit only this file.
- **Generated:** JSON Schema in [`schema/0.1/`](schema/0.1/) and Pydantic models in
  `bioimage_annotation_schema.datamodel` (`pixi run gen`).
- **Examples:** [`examples/0.1/`](examples/0.1/): an annotation set (YAML) and its records (CSV).
- **MIFA:** fields that correspond to MIFA ([bia-mifa-models](https://github.com/BioImage-Archive/bia-mifa-models),
  BioImage Archive) carry LinkML mappings to it, and `annotation_types` uses MIFA's values.

Status: **draft 0.1**. Fields may still change between 0.x releases.

## Two documents

| Document | Class | One per | Typical file |
|---|---|---|---|
| Annotation set | `AnnotationSet` | set | `annotation-set.yaml` |
| Annotation record | `AnnotationRecord` | annotation | a row of `annotation-records.csv` |

## Validate

```bash
# any JSON Schema validator, or:
linkml-validate -s src/linkml/bioimage_annotation_schema.yaml -C AnnotationSet annotation-set.yaml
```

```python
from bioimage_annotation_schema.datamodel import AnnotationSet
AnnotationSet(**yaml.safe_load(open("annotation-set.yaml")))
```

## Develop

```bash
pixi run gen    # regenerate JSON Schema and Pydantic models after editing the LinkML file
pixi run test   # examples validate; broken examples are rejected
```

## Implementations

- [omero-annotate-ai](https://github.com/Leiden-Cell-Observatory/omero_annotate_ai): annotation of OMERO and OME-Zarr images with micro-SAM and Cellpose (export in progress).

## License

Schema and documentation: [CC-BY-4.0](LICENSE).
