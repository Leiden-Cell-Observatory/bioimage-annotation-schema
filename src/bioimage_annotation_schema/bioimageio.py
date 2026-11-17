"""Describe an annotation set as a bioimage.io dataset (``rdf.yaml``).

A `bioimage.io <https://bioimage.io>`_ resource description file lists a resource
of the BioImage Model Zoo; for a dataset (format 0.3) it holds the name,
description, authors, citations, licence, tags, version and source URL.

bioimage.io asks for a description, authors, citations, tags and a source for FAIR
compliance: if the set lacks one, :func:`check_bioimageio` names it and the export
refuses, rather than inventing a value. Everything else the set records has no
field in a dataset description. The whole set is therefore kept under
``config.bioimage_annotation_schema`` (the place the format gives to tool-specific
metadata), and the set document and the records table are listed as attachments.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from .crate import _inside
from .datamodel import AnnotationRecord, AnnotationSet, Publication
from .io import RECORDS_FILE, SET_FILE

METADATA_FILE = "rdf.yaml"
FORMAT_VERSION = "0.3.4"
CONFIG_KEY = "bioimage_annotation_schema"

_NAME = re.compile(r"[A-Za-z0-9_+\- ()]{5,128}")
_DOI_PREFIX = re.compile(r"^(https?://(dx\.)?doi\.org/|doi:)", re.IGNORECASE)


class BioimageioNotReady(ValueError):
    """The set lacks fields bioimage.io asks for; ``missing`` names them."""

    def __init__(self, missing: Sequence[str]) -> None:
        self.missing = list(missing)
        super().__init__("Not ready for bioimage.io, missing:\n- " + "\n- ".join(missing))


def _cite(publication: Publication) -> dict[str, str] | None:
    """A bioimage.io citation; ``None`` without a DOI, which the format needs."""
    if not publication.doi:
        return None
    year = f" ({publication.year})" if publication.year else ""
    return {
        "text": f"{publication.authors}{year}. {publication.title.rstrip('.')}.",
        "doi": _DOI_PREFIX.sub("", publication.doi),
    }


def _citations(annotation_set: AnnotationSet) -> list[dict[str, str]]:
    study = annotation_set.study
    return [c for p in (study.publications if study else None) or [] if (c := _cite(p))]


def check_bioimageio(annotation_set: AnnotationSet) -> list[str]:
    """The fields bioimage.io asks for that the set does not have (empty when ready)."""
    missing = []
    if not _NAME.fullmatch(annotation_set.name):
        missing.append("name (5 to 128 letters, digits, spaces and _ + - ( ))")
    missing += [
        name
        for name in ("description", "authors", "keywords", "links")
        if not getattr(annotation_set, name)
    ]
    if not _citations(annotation_set):
        missing.append("study.publications (with a doi)")
    return missing


def build_bioimageio_dataset(
    annotation_set: AnnotationSet,
    records: Sequence[AnnotationRecord],
    folder: str | Path,
) -> dict[str, Any]:
    """The bioimage.io dataset description of an annotation set, as plain data.

    The set's first link is the dataset's ``source``. Raises
    :class:`BioimageioNotReady` when the set lacks a field bioimage.io asks for.
    """
    if missing := check_bioimageio(annotation_set):
        raise BioimageioNotReady(missing)
    folder = Path(folder)
    assert annotation_set.links  # check_bioimageio
    authors = [
        {
            "name": f"{author.first_name} {author.last_name}",
            "orcid": author.orcid.removeprefix("https://orcid.org/") if author.orcid else None,
            "affiliation": "; ".join(org.name for org in author.affiliations or []),
            "email": author.email,
        }
        for author in annotation_set.authors or []
    ]
    changes = annotation_set.changes
    rdf = {
        "type": "dataset",
        "format_version": FORMAT_VERSION,
        "name": annotation_set.name,
        "description": annotation_set.description,
        "authors": [{k: v for k, v in author.items() if v} for author in authors],
        "cite": _citations(annotation_set),
        "license": annotation_set.license,
        "tags": annotation_set.keywords,
        "version": annotation_set.version,
        # bioimage.io allows a comment of at most 512 characters
        "version_comment": changes if changes and len(changes) <= 512 else None,
        "source": annotation_set.links[0].url,
        "attachments": [
            {"source": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for name in (SET_FILE, RECORDS_FILE)
            if (path := _inside(folder, name))
        ],
        "config": {
            CONFIG_KEY: {
                "annotation_set": annotation_set.model_dump(mode="json", exclude_none=True),
                "annotated_records": dict(
                    Counter(r.split for r in records if r.status == "annotated")
                ),
            }
        },
    }
    return {k: v for k, v in rdf.items() if v not in (None, [])}


def write_bioimageio_dataset(
    annotation_set: AnnotationSet,
    records: Sequence[AnnotationRecord],
    folder: str | Path,
) -> Path:
    """Write ``rdf.yaml`` into ``folder``; returns its path."""
    rdf = build_bioimageio_dataset(annotation_set, records, folder)  # refuses before writing
    target = Path(folder) / METADATA_FILE
    target.write_text(yaml.safe_dump(rdf, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return target
