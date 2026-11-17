"""Export an annotation set to MIFA and to a BioImage Archive submission bundle.

MIFA is the BioImage Archive's "Metadata, Incentives, Formats and Accessibility"
annotation-metadata model (https://github.com/BioImage-Archive/bia-mifa-models).
A MIFA submission has three YAML documents: ``Study_<accession>.yaml``,
``Annotations_<accession>.yaml`` (with one record per annotation file) and
``Version_<accession>.yaml``.

Only facts recorded in the set are written: if MIFA requires a field the set does
not have (e.g. a funding statement), :func:`check_mifa` names it and the export
refuses, rather than inventing a value. The free-text ``annotation_overview`` and
``annotation_method`` are the set's own, or written from its structured fields.

The documents are built with the upstream LinkML dataclasses, which check MIFA's
required fields on construction and serialise to the exact submission YAML. That
package is not on PyPI; install it with
``pip install "git+https://github.com/BioImage-Archive/bia-mifa-models.git@v1.1.5"``.
It is imported only when a MIFA document is built.
"""

from __future__ import annotations

import csv
import re
import shutil
import warnings
from collections import Counter
from collections.abc import Sequence
from datetime import UTC
from pathlib import Path
from typing import Any

import yaml

from .datamodel import AnnotationRecord, AnnotationSet

BUNDLE_IMAGE_DIR = "images"
BUNDLE_ANNOTATION_DIR = "annotations"

_LICENSES = {"CC-BY-4.0": "CC_BY", "CC0-1.0": "CC0"}
NOT_DESCRIBED = "Not described."


class MifaNotReady(ValueError):
    """The set lacks fields MIFA requires; ``missing`` names them."""

    def __init__(self, missing: Sequence[str]) -> None:
        self.missing = list(missing)
        super().__init__("Not ready for MIFA, missing:\n- " + "\n- ".join(missing))


def _import_mifa() -> tuple[Any, Any]:
    try:
        from bia_mifa_models.datamodel import bia_mifa_models as models
        from linkml_runtime.dumpers import yaml_dumper
    except ImportError as exc:  # pragma: no cover - only without the dependency
        raise ImportError(
            "MIFA export needs bia-mifa-models: pip install "
            "'git+https://github.com/BioImage-Archive/bia-mifa-models.git@v1.1.5'"
        ) from exc
    return models, yaml_dumper


def links(annotation_set: AnnotationSet) -> list[tuple[str, str | None]]:
    """``(url, description)`` of the set's links, then its source dataset's URL."""
    found = [(link.url, link.description) for link in annotation_set.links or []]
    source = annotation_set.source_dataset
    if source and source.url:
        found.append((source.url, "Source image dataset"))
    return found


def check_mifa(annotation_set: AnnotationSet) -> list[str]:
    """The fields MIFA requires that the set does not have (empty when ready)."""
    study = annotation_set.study
    missing = []
    if not study:
        missing.append("study (title, description, funding_statement)")
    else:
        missing += [
            f"study.{name}"
            for name in ("description", "funding_statement")
            if not getattr(study, name)
        ]
    if not annotation_set.keywords:
        missing.append("keywords")
    if not links(annotation_set):
        missing.append("links (or source_dataset.url)")
    if not annotation_set.version:
        missing.append("version")
    return missing


def annotated(records: Sequence[AnnotationRecord]) -> list[AnnotationRecord]:
    """The records with a saved annotation (not pending, not excluded)."""
    return [r for r in records if r.status == "annotated"]


def compose_overview(annotation_set: AnnotationSet) -> str:
    """MIFA ``annotation_overview``: the set's own, or one written from its fields."""
    meth = annotation_set.methodology
    if meth.overview:
        return meth.overview
    study = annotation_set.study
    parts = [
        (annotation_set.description or (study.title if study else "") or annotation_set.name)
        .strip()
        .rstrip(".")
        + ".",
        f"Annotation type: {', '.join(meth.annotation_types)}"
        + (f"; coverage: {meth.coverage}" if meth.coverage else "")
        + ".",
    ]
    if study and study.organism:
        parts.append(f"Organism: {study.organism}.")
    if study and study.imaging_method:
        parts.append(f"Imaging method: {study.imaging_method}.")
    if annotation_set.source_dataset:
        src = annotation_set.source_dataset
        parts.append(f"Source dataset: {src.identifier or src.description}.")
    return " ".join(parts)


def compose_split(annotation_set: AnnotationSet, records: Sequence[AnnotationRecord]) -> str:
    """One sentence on the train/validation/test split of the annotated records."""
    counts = Counter(r.split for r in annotated(records))
    text = "Split: " + ", ".join(
        f"{counts[s]} {s}" for s in ("training", "validation", "test") if counts[s]
    )
    split = annotation_set.split
    if split and split.unit:
        text += f", assigned per {split.unit}"
    if split and split.rationale:
        text += f" ({split.rationale.rstrip('.')})"
    return text + "."


def compose_normalization(annotation_set: AnnotationSet) -> str | None:
    """One sentence on the intensity normalisation intended for model input."""
    norm = annotation_set.normalization
    if not norm:
        return None
    if norm.method != "percentile":
        return "Model input: raw intensities."
    return (
        f"Model input normalisation: per-image percentiles {norm.percentile_low}-"
        f"{norm.percentile_high} mapped to [0, 1]" + (", clipped." if norm.clip else ".")
    )


def compose_method(annotation_set: AnnotationSet, records: Sequence[AnnotationRecord]) -> str:
    """MIFA ``annotation_method``: the set's own description followed by the method,
    tools, models, split and normalisation from its structured fields."""
    meth = annotation_set.methodology
    parts = [meth.method_description.rstrip(".") + "."] if meth.method_description else []
    if meth.method:
        parts.append(f"Annotation method: {meth.method.replace('_', '-')}.")
    for tool in meth.tools or []:
        text = f"Tool: {tool.name}" + (f" {tool.version}" if tool.version else "")
        if tool.mode:
            text += f" ({tool.mode.replace('_', ' ')})"
        if tool.model:
            model = tool.model
            text += f", model {model.name}" + (f" {model.version}" if model.version else "")
            text += f" ({model.doi or model.url})" if (model.doi or model.url) else ""
        parts.append(text + ".")
    if records:
        parts.append(compose_split(annotation_set, records))
    if normalization := compose_normalization(annotation_set):
        parts.append(normalization)
    return " ".join(parts) or NOT_DESCRIBED


def bundle_paths(record: AnnotationRecord) -> tuple[str, str]:
    """``(mask, image)`` paths of a record inside a BioImage Archive bundle."""
    return (
        f"{BUNDLE_ANNOTATION_DIR}/{record.annotation_id}_mask.tif",
        f"{BUNDLE_IMAGE_DIR}/{record.annotation_id}.tif",
    )


def spatial_information(record: AnnotationRecord) -> str:
    """Plane, patch and volume of a record as MIFA ``spatial_information`` text."""
    bits = [
        f"{name}={value}"
        for name, value in (("t", record.timepoint), ("z", record.z_slice), ("c", record.channel))
        if value is not None
    ]
    if record.patch_x is not None:
        bits.append(
            f"patch=(x={record.patch_x},y={record.patch_y},"
            f"w={record.patch_width},h={record.patch_height})"
        )
    if record.z_start is not None:
        bits.append(f"z_range=({record.z_start}-{record.z_end})")
    return ",".join(bits) or "whole image"


def _authors(models: Any, people: Sequence[Any] | None) -> list[Any]:
    authors = []
    for person in people or []:
        kwargs: dict[str, Any] = {
            "author_first_name": person.first_name,
            "author_last_name": person.last_name,
            "email": person.email,
            "orcid_id": person.orcid,
            "role": person.roles,
            "organisation": [
                models.OrganisationInfo(organisation_name=o.name, ror_id=o.ror, address=o.address)
                for o in person.affiliations or []
            ],
        }
        authors.append(models.Author(**{k: v for k, v in kwargs.items() if v}))
    return authors


def _version_timestamp(annotation_set: AnnotationSet) -> str:
    """When this version was made: the newest session end, else the set's creation."""
    times = [annotation_set.created]
    times += [s.ended or s.started for s in annotation_set.sessions or []]
    aware = [t if t.tzinfo else t.replace(tzinfo=UTC) for t in times]
    return max(aware).isoformat()


def to_mifa(
    annotation_set: AnnotationSet,
    records: Sequence[AnnotationRecord],
    *,
    file_ids: str = "bundle",
) -> dict[str, Any]:
    """The three MIFA documents: ``study`` and ``annotations`` as upstream
    dataclasses, ``version`` as plain data. Only annotated records are listed.

    ``file_ids``: ``"bundle"`` uses the file paths of :func:`save_bia_package`;
    ``"uri"`` uses each record's annotation_id and image_uri.
    """
    if missing := check_mifa(annotation_set):
        raise MifaNotReady(missing)
    models, _ = _import_mifa()
    study = annotation_set.study
    assert study is not None  # check_mifa
    urls = links(annotation_set)
    study_fields = {
        "authors": _authors(models, annotation_set.authors),
        "publications": [
            models.Publications(
                publication_title=p.title, publication_authors=p.authors,
                **{k: v for k, v in (("publication_doi", p.doi), ("publication_year", p.year),
                                     ("pubmed_id", p.pubmed_id)) if v is not None},
            )
            for p in study.publications or []
        ],
        "grants": [models.GrantReference(grant_id=g.id, funder=g.funder) for g in study.grants or []],
        "acknowledgements": study.acknowledgements,
        "ai_models_trained": annotation_set.ai_models_trained,
    }
    study_doc = models.Study(
        title=study.title,
        description=study.description,
        keywords=annotation_set.keywords,
        license=_LICENSES[annotation_set.license],
        funding_statement=study.funding_statement,
        link_url=[url for url, _ in urls],
        link_description=[d or "" for _, d in urls],
        **{k: v for k, v in study_fields.items() if v},
    )

    meth = annotation_set.methodology
    file_metadata = []
    for record in annotated(records):
        if file_ids == "uri":
            annotation_id, source_image_id = record.annotation_id, record.image_uri
        else:
            annotation_id, source_image_id = bundle_paths(record)
        kwargs: dict[str, Any] = {
            "annotation_id": annotation_id,
            "annotation_type": [record.annotation_type or meth.annotation_types[0]],
            "source_image_id": source_image_id,
            "spatial_information": spatial_information(record),
        }
        if record.created_at:
            kwargs["annotation_creation_time"] = record.created_at.isoformat()
        if record.transformations:
            kwargs["transformations"] = record.transformations
        file_metadata.append(models.FileLevelMetadata(**kwargs))

    optional = {
        "annotation_coverage": meth.coverage_description
        or (f"{meth.coverage} objects in the annotated regions" if meth.coverage else None),
        "annotation_confidence_level": meth.confidence_level,
        "authors": _authors(models, meth.annotators or annotation_set.authors),
    }
    annotations_doc = models.Annotations(
        annotation_overview=compose_overview(annotation_set),
        annotation_method=compose_method(annotation_set, records),
        annotation_criteria=meth.criteria,
        file_metadata=file_metadata,
        **{k: v for k, v in optional.items() if v},
    )
    # Plain data, not models.Version: in bia-mifa-models 1.1.5 the generated class
    # turns version into a float, while MIFA's schema (and validator) want a string.
    version_doc = {
        "version": str(annotation_set.version),
        "timestamp": _version_timestamp(annotation_set),
        **{k: v for k, v in (("changes", annotation_set.changes),
                             ("previous_version", annotation_set.previous_version)) if v},
    }
    return {"study": study_doc, "annotations": annotations_doc, "version": version_doc}


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip()).strip("_") or "export"


def save_mifa(
    annotation_set: AnnotationSet,
    records: Sequence[AnnotationRecord],
    directory: str | Path,
    *,
    accession: str | None = None,
    file_ids: str = "bundle",
) -> dict[str, Path]:
    """Write the three MIFA YAML documents to ``directory`` as
    ``<Class>_<accession>.yaml``. The accession defaults to the source dataset's
    identifier, else the set's name."""
    _, yaml_dumper = _import_mifa()
    docs = to_mifa(annotation_set, records, file_ids=file_ids)  # refuses before writing
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    source = annotation_set.source_dataset
    accession = _slug(accession or (source.identifier if source else None) or annotation_set.name)
    paths = {}
    for key, class_name in (("study", "Study"), ("annotations", "Annotations"), ("version", "Version")):
        doc = docs[key]
        text = yaml.safe_dump(doc, sort_keys=False) if isinstance(doc, dict) else yaml_dumper.dumps(doc)
        paths[key] = directory / f"{class_name}_{accession}.yaml"
        paths[key].write_text(text, encoding="utf-8")
    return paths


# BIA file-list columns that are always kept, and per-file provenance columns kept
# whenever any row has a value. Other columns are dropped when they hold fewer than
# two distinct values (BioImage Archive guidance).
_REQUIRED_COLUMNS = ("Files", "source_image")
_PROVENANCE_COLUMNS = ("pixel_sha256", "iscc")


def _write_file_list(rows: list[dict[str, Any]], columns: Sequence[str], path: Path) -> int:
    keep = [
        c
        for c in columns
        if c in _REQUIRED_COLUMNS
        or (c in _PROVENANCE_COLUMNS and any(r[c] for r in rows))
        or (c not in _PROVENANCE_COLUMNS and len({r[c] for r in rows}) >= 2)
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keep, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def save_bia_package(
    annotation_set: AnnotationSet,
    records: Sequence[AnnotationRecord],
    folder: str | Path,
    dest: str | Path,
    *,
    accession: str | None = None,
    move_data: bool = False,
) -> dict[str, Any]:
    """Assemble a BioImage Archive submission bundle in ``dest``.

    Writes ``metadata/`` (the three MIFA YAMLs), ``file_list_images.tsv`` and
    ``file_list_annotations.tsv``, and copies each annotated record's ``input_file``
    and ``mask_file`` from ``folder`` to ``images/`` and ``annotations/``. Missing
    files are skipped with a warning. ``move_data`` moves instead of copying; use
    it only on a disposable staging folder.

    Returns the paths written and the counts of images, annotations, files
    transferred and files missing.
    """
    records = annotated(records)
    if missing := check_mifa(annotation_set):
        raise MifaNotReady(missing)  # before anything is written
    folder, dest = Path(folder), Path(dest)
    metadata = save_mifa(annotation_set, records, dest / "metadata", accession=accession)

    annotation_rows, image_rows, seen = [], [], set()
    transfers: dict[str, str] = {}
    for r in records:
        mask, image = bundle_paths(r)
        if r.mask_file:
            transfers[r.mask_file] = mask
        if r.input_file:
            transfers[r.input_file] = image
        annotation_rows.append(
            {"Files": mask, "source_image": image, "Channel": r.channel,
             "Timepoint": r.timepoint, "Z": r.z_slice, "Category": r.split,
             "pixel_sha256": r.mask_digest or "", "iscc": r.mask_iscc or ""}
        )
        if image not in seen:
            seen.add(image)
            image_rows.append(
                {"Files": image, "Channel": r.channel,
                 "pixel_sha256": r.input_digest or "", "iscc": r.input_iscc or ""}
            )
    dest.mkdir(parents=True, exist_ok=True)
    images_path = dest / "file_list_images.tsv"
    annotations_path = dest / "file_list_annotations.tsv"
    n_images = _write_file_list(image_rows, ["Files", "Channel", *_PROVENANCE_COLUMNS], images_path)
    n_annotations = _write_file_list(
        annotation_rows,
        ["Files", "source_image", "Channel", "Timepoint", "Z", "Category", *_PROVENANCE_COLUMNS],
        annotations_path,
    )

    transfer = shutil.move if move_data else shutil.copy2
    copied = missing = 0
    for source_rel, bundle_rel in sorted(transfers.items()):
        source = folder / source_rel
        if source.is_file():
            target = dest / bundle_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            transfer(str(source), str(target))
            copied += 1
        else:
            missing += 1
    if missing:
        warnings.warn(
            f"{missing} file(s) listed in the records were not found under {folder} "
            "and are not in the bundle.",
            UserWarning,
            stacklevel=2,
        )
    return {
        "dir": dest,
        "metadata": metadata,
        "file_list_images": images_path,
        "file_list_annotations": annotations_path,
        "n_images": n_images,
        "n_annotations": n_annotations,
        "copied": copied,
        "missing": missing,
    }
