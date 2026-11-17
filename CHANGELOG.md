# Changelog

Versions follow semantic versioning. While the major version is 0, a minor release
(0.x) may change or remove fields; a patch release (0.x.y) only adds optional fields,
fixes descriptions or loosens constraints.

## 0.1.0 (unreleased)

- First draft: `AnnotationSet` and `AnnotationRecord`, LinkML source with generated
  JSON Schema and Pydantic models, MIFA mappings, examples and tests.
- Python library and `bas` command: read, write and validate set folders; export to
  RO-Crate and to a BioImage Archive bundle with MIFA metadata.
- MIFA-complete: authors with first and last name, affiliations (ROR) and roles;
  study publications, grants and acknowledgements; links with descriptions; set
  version, changes, previous version and AI models trained; annotators; record
  transformations. Licence limited to CC-BY-4.0 and CC0-1.0.
- `check_mifa` / `bas validate --mifa`; the MIFA export no longer fills in
  placeholders and its output passes MIFA's own validator.
- ISCC codes are declared: the set's `content_codes` says, for region codes
  (`input_iscc`, `mask_iscc`) and source-image codes (new `image_iscc`), the code
  type, bits, which pixels, their preparation, the specification and the
  implementation, since ISCC codes are only comparable when made the same way.
  `check_documents` (run by `bas validate`) requires it, and checks that records
  name existing sessions. The pixel digest's description says how it differs from
  IMAGEWALK (IEP-0018).
- `omero_server` (host, OMERO.web address, database UUID) says which OMERO server
  the records' `omero:image:<id>` URIs refer to; `check_documents` requires it when
  any record has such a URI, and the RO-Crate links each OMERO source image to it.
- Documentation site (Zensical): overview tree, class diagram you can zoom and pan, interactive model
  browser, MIFA crosswalk and LinkML reference pages, all generated from the schema.
  Every class, field and allowed value has a description.
- Croissant export (`write_croissant`, `bas croissant`): `croissant.json` following
  Croissant 1.1 and Croissant RAI 1.0, with the files, a record per mask, the split as
  `cr:Split`, classes, sessions, and the fields Croissant has no property for under the
  RAI properties and the schema's own terms. Loads in `mlcroissant`.
- bioimage.io export (`write_bioimageio_dataset`, `bas bioimageio`): `rdf.yaml`, a
  dataset description in format 0.3.4 that validates with `bioimageio.spec`.
- RO-Crate export: the split is in the metadata graph. Each split (training,
  validation, test) is a `Collection` of its image regions and masks, under a `#split`
  collection that says how the split was made (unit, rationale, strategy, balancing,
  seed). Before, the split was only inside `annotation-set.yaml`.
- New optional `AnnotationSet.url`: where the set itself is published (DOI or archive
  page). The Croissant `url` and the bioimage.io `source` are this address and both
  exports require it; they used the set's first link before, which may be the analysis
  code.
