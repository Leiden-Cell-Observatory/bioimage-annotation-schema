"""Describe an annotation set's folder as an RO-Crate (``ro-crate-metadata.json``).

An `RO-Crate <https://w3id.org/ro/crate/1.1>`_ is a JSON-LD file next to the data
that says what the folder holds and how it came about, in a form repositories and
workflow tools read. For an annotation set it lists:

- the set (name, description, licence, authors) as the root dataset, with the
  study's organism (``about``) and imaging method (``measurementTechnique``) as
  terms, identified by their ontology IRI when recorded,
- the files: the set document, the records table, each annotated image region and
  each mask, with the pixel SHA-256 digest and ISCC code when recorded,
- the source images by URI, with their ISCC code when recorded; a URI that is not
  an OMERO or web address (a local path, which may hold a user name) gets a
  ``#source-<hash>`` id instead,
- every annotation session as an action: who, when, which software and model, its
  note, and the masks it saved (an annotate session is a ``CreateAction``, a review
  an ``UpdateAction``).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from .datamodel import AnnotationRecord, AnnotationSet, CodeMethod, Session
from .io import RECORDS_FILE, SCHEMA_VERSION, SET_FILE

METADATA_FILE = "ro-crate-metadata.json"
SPEC = "https://w3id.org/ro/crate/1.1"
PROFILE = f"https://w3id.org/bioimage-annotation-schema/{SCHEMA_VERSION}"

Entity = dict[str, Any]

_FORMATS = {
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".png": "image/png",
    ".csv": "text/csv",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".json": "application/json",
}
_ACTION_STATUS = {
    "open": "http://schema.org/ActiveActionStatus",
    "finished": "http://schema.org/CompletedActionStatus",
    "interrupted": "http://schema.org/FailedActionStatus",
}


def _ref(entity_id: str) -> dict[str, str]:
    return {"@id": entity_id}


def _key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def _local_id(kind: str, text: str) -> str:
    """A stable, unique ``#kind-...`` id for ``text`` (readable part plus a hash)."""
    readable = re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-")[:40] or "x"
    return f"#{kind}-{readable}-{_key(text)}"


def _source_id(uri: str) -> str:
    """The id of a source image: its URI if it is an OMERO or web address,
    otherwise a local id, so no local path enters the crate."""
    if re.match(r"^omero:image:\d+$", uri) or re.match(r"^[a-z][a-z0-9+.-]*://", uri):
        return uri
    return f"#source-{_key(uri)}"


def _license(text: str) -> Entity:
    """An SPDX licence (e.g. ``CC-BY-4.0``) by its URL, anything else by name."""
    if re.fullmatch(r"[A-Za-z0-9.+-]+", text):
        return {"@id": f"https://spdx.org/licenses/{text}", "@type": "CreativeWork", "name": text}
    return {"@id": "#license", "@type": "CreativeWork", "name": text}


def _aware(t: datetime) -> datetime:
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def _published(annotation_set: AnnotationSet) -> str:
    """The last time the set changed: its newest session end, else its creation."""
    times = [annotation_set.created]
    times += [s.ended or s.started for s in annotation_set.sessions or []]
    return max(_aware(t) for t in times).isoformat()


def _inside(folder: Path, relative: str | None) -> Path | None:
    """``folder / relative`` if it is an existing file inside ``folder``."""
    if not relative:
        return None
    path = (folder / relative).resolve()
    if not path.is_relative_to(folder.resolve()) or not path.is_file():
        return None
    return path


class _Graph:
    """Collects entities by ``@id``; the first one written for an id wins."""

    def __init__(self, folder: Path, annotation_set: AnnotationSet) -> None:
        self.folder = folder.resolve()
        self.entities: dict[str, Entity] = {}
        codes = annotation_set.content_codes
        self.region_code = codes.region if codes else None

    def add(self, entity: Entity) -> dict[str, str]:
        self.entities.setdefault(entity["@id"], entity)
        return _ref(entity["@id"])

    def file(self, path: Path, **extra: Any) -> dict[str, str]:
        entity: Entity = {
            "@id": path.relative_to(self.folder).as_posix(),
            "@type": "File",
            "name": path.name,
            "contentSize": str(path.stat().st_size),
        }
        if fmt := _FORMATS.get(path.suffix.lower()):
            entity["encodingFormat"] = fmt
        entity.update({k: v for k, v in extra.items() if v})
        return self.add(entity)

    def digests(self, owner: str, digest: str | None, iscc: str | None) -> list[Any]:
        """``identifier`` values of a file: its pixel digest and ISCC code."""
        found: list[Any] = []
        if digest:
            found.append(
                self.add(
                    {
                        "@id": f"#{owner}-pixel-sha256",
                        "@type": "PropertyValue",
                        "propertyID": "pixel-sha256",
                        "name": "SHA-256 of the pixels (dtype, shape and values)",
                        "value": digest,
                    }
                )
            )
        if iscc:
            found.append(
                self.add(
                    {
                        "@id": f"#{owner}-iscc",
                        "@type": "PropertyValue",
                        "propertyID": "iscc",
                        "name": _code_name(self.region_code),
                        "value": iscc,
                    }
                )
            )
        return found

    def software(self, text: str) -> dict[str, str]:
        return self.add(
            {"@id": _local_id("software", text), "@type": "SoftwareApplication", "name": text}
        )


def _code_name(method: CodeMethod | None) -> str:
    """How an ISCC code was made, from the set's content_codes."""
    if method is None:
        return "ISCC code (ISO 24138)"
    return f"ISCC {method.code_type} of {method.pixels}; {method.preparation} ({method.implementation})"


def _session_action(graph: _Graph, session: Session, masks: list[dict[str, str]]) -> Entity:
    review = session.kind == "review"
    action: Entity = {
        "@id": f"#session-{session.id}",
        "@type": "UpdateAction" if review else "CreateAction",
        "name": f"{'Review' if review else 'Annotation'} session {session.id}",
        "startTime": _aware(session.started).isoformat(),
        "result": masks,
    }
    if session.ended:
        action["endTime"] = _aware(session.ended).isoformat()
    if session.status:
        action["actionStatus"] = _ACTION_STATUS[session.status]
    instruments = [graph.software(t) for t in (session.software, session.model) if t]
    if instruments:
        action["instrument"] = instruments
    if session.annotator:
        action["agent"] = graph.add(
            {
                "@id": _local_id("annotator", session.annotator),
                "@type": "Person",
                "name": session.annotator,
            }
        )
    if session.note:
        action["description"] = session.note
    return action


def _authors(graph: _Graph, annotation_set: AnnotationSet) -> list[dict[str, str]]:
    authors = []
    for i, author in enumerate(annotation_set.authors or []):
        person: Entity = {
            "@id": author.orcid or f"#author-{i}",
            "@type": "Person",
            "name": f"{author.first_name} {author.last_name}",
            "givenName": author.first_name,
            "familyName": author.last_name,
        }
        affiliations = [
            graph.add(
                {"@id": org.ror or _local_id("org", org.name), "@type": "Organization", "name": org.name}
            )
            for org in author.affiliations or []
        ]
        if affiliations:
            person["affiliation"] = affiliations
        authors.append(graph.add(person))
    return authors


def _term(graph: _Graph, kind: str, name: str | None, iri: str | None) -> dict[str, str] | None:
    """A ``DefinedTerm`` for a free-text name and/or its ontology term IRI."""
    if not (name or iri):
        return None
    term: Entity = {"@id": iri or _local_id(kind, name or ""), "@type": "DefinedTerm"}
    if name:
        term["name"] = name
    return graph.add(term)


def build_ro_crate(
    annotation_set: AnnotationSet,
    records: Sequence[AnnotationRecord],
    folder: str | Path,
    *,
    metadata_files: Sequence[str] = (SET_FILE, RECORDS_FILE),
) -> dict[str, Any]:
    """The RO-Crate metadata (JSON-LD) of an annotation set's folder.

    ``metadata_files`` are files in ``folder`` that describe the set (listed when
    they exist). Only record files that exist inside ``folder`` are listed; images
    that were never saved locally appear as source images only.
    """
    folder = Path(folder)
    graph = _Graph(folder, annotation_set)
    parts = [graph.file(p) for name in metadata_files if (p := _inside(folder, name))]

    masks_by_session: dict[int, list[dict[str, str]]] = {}
    for record in records:
        source_entity: Entity = {
            "@id": _source_id(record.image_uri),
            "@type": "ImageObject",
            "name": record.image_name or record.image_uri,
        }
        if record.image_iscc:
            source_entity["identifier"] = record.image_iscc
        source = graph.add(source_entity)
        based_on = [source]
        if image := _inside(folder, record.input_file):
            image_ref = graph.file(
                image,
                isBasedOn=source,
                identifier=graph.digests(
                    f"{record.annotation_id}-input", record.input_digest, record.input_iscc
                ),
            )
            parts.append(image_ref)
            based_on = [image_ref, source]
        mask = _inside(folder, record.mask_file)
        if record.status == "annotated" and mask:
            mask_ref = graph.file(
                mask,
                isBasedOn=based_on,
                identifier=graph.digests(
                    f"{record.annotation_id}-mask", record.mask_digest, record.mask_iscc
                ),
            )
            parts.append(mask_ref)
            if record.session is not None:
                masks_by_session.setdefault(record.session, []).append(mask_ref)

    actions = [
        graph.add(_session_action(graph, s, masks_by_session.get(s.id, [])))
        for s in annotation_set.sessions or []
    ]
    study = annotation_set.study
    source_dataset = annotation_set.source_dataset
    root: Entity = {
        "@id": "./",
        "@type": "Dataset",
        "name": annotation_set.name,
        "description": annotation_set.description
        or (study.description if study else None)
        or (source_dataset.description if source_dataset else None)
        or f"Image annotations of the set {annotation_set.name}.",
        "datePublished": _published(annotation_set),
        "license": graph.add(_license(annotation_set.license)),
        "conformsTo": graph.add(
            {
                "@id": PROFILE,
                "@type": "CreativeWork",
                "name": f"Bioimage Annotation Schema {SCHEMA_VERSION}",
            }
        ),
        "hasPart": parts,
        "mentions": actions,
    }
    if authors := _authors(graph, annotation_set):
        root["author"] = authors
    if annotation_set.keywords:
        root["keywords"] = annotation_set.keywords
    if study and (organism := _term(graph, "organism", study.organism, study.organism_term)):
        root["about"] = organism
    if study and (
        method := _term(graph, "method", study.imaging_method, study.imaging_method_term)
    ):
        root["measurementTechnique"] = method
    descriptor: Entity = {
        "@id": METADATA_FILE,
        "@type": "CreativeWork",
        "conformsTo": _ref(SPEC),
        "about": _ref("./"),
    }
    entities = [descriptor, root, *graph.entities.values()]
    return {"@context": f"{SPEC}/context", "@graph": [_single(e) for e in entities]}


def _single(entity: Entity) -> Entity:
    """One value instead of a one-item list (the RO-Crate 1.1 JSON-LD convention)."""
    single: Entity = {}
    for key, value in entity.items():
        items = cast(list[Any], value) if isinstance(value, list) else None
        single[key] = items[0] if items is not None and len(items) == 1 else value
    return single


def write_ro_crate(
    annotation_set: AnnotationSet,
    records: Sequence[AnnotationRecord],
    folder: str | Path,
    *,
    metadata_files: Sequence[str] = (SET_FILE, RECORDS_FILE),
) -> Path:
    """Write ``ro-crate-metadata.json`` into ``folder``; returns its path."""
    crate = build_ro_crate(annotation_set, records, folder, metadata_files=metadata_files)
    target = Path(folder) / METADATA_FILE
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(crate, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(target)
    return target
