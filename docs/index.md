# Bioimage Annotation Schema

An open schema for sets of image annotations made to train or evaluate AI models:
what was annotated, from which images, how, by whom, how the annotations are split,
and one record per annotation. Fields that correspond to
[MIFA](https://bioimage-archive.github.io/bia-mifa-models/), the BioImage Archive's
metadata for AI-ready data, are mapped to it, so a BioImage Archive submission can be
written from a set.

!!! note "Draft 0.1"
    Fields may still change between 0.x releases.

## Two documents

| Document | Class | One per | File |
|---|---|---|---|
| Annotation set | [`AnnotationSet`](reference/classes/AnnotationSet.md) | set | `annotation-set.yaml` |
| Annotation record | [`AnnotationRecord`](reference/classes/AnnotationRecord.md) | annotation | a row of `annotation-records.csv` |

Both sit in the set's folder, next to the image and mask files the records point to:

```text
annotation-set.yaml          # AnnotationSet
annotation-records.csv       # one AnnotationRecord per row
annotation_input/…           # image regions (input_file)
annotation_output/…          # masks (mask_file)
```

## Where to look

- [Overview](overview.md): every field of both documents as a tree, and a diagram of how the classes connect.
- [Model browser](model.md): the same tree, interactive, with each field's details and MIFA mapping.
- [MIFA crosswalk](mifa.md): which field maps to which MIFA field.
- [Reference](reference/index.md): one page per class, field and allowed-value list, generated from the schema.

## Example

```yaml
--8<-- "examples/0.1/annotation-set.yaml"
```

```text
--8<-- "examples/0.1/annotation-records.csv"
```

## Validate and export

```bash
pip install "git+https://github.com/Leiden-Cell-Observatory/bioimage-annotation-schema"
bas validate my-set/             # check both documents
bas validate --mifa my-set/      # also list what MIFA still needs
bas ro-crate my-set/             # write my-set/ro-crate-metadata.json
bas bia my-set/ bia-bundle/      # BioImage Archive bundle: MIFA YAML, file lists, data
```

Tools in other languages write the two files and validate them with any JSON Schema
validator, using the generated schemas in
[`schema/0.1/`](https://github.com/Leiden-Cell-Observatory/bioimage-annotation-schema/tree/main/src/bioimage_annotation_schema/schema/0.1).

## Source

The schema is one [LinkML](https://linkml.io) file,
[`bioimage_annotation_schema.yaml`](https://github.com/Leiden-Cell-Observatory/bioimage-annotation-schema/blob/main/src/bioimage_annotation_schema/schema/bioimage_annotation_schema.yaml);
the JSON Schema, the Python models and these pages are generated from it.
