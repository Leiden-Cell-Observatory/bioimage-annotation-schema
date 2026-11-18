"""Describe an annotation set's folder as a Croissant dataset (``croissant.json``).

`Croissant <http://mlcommons.org/croissant/1.1>`_ is MLCommons' JSON-LD format for
machine-learning datasets, built on schema.org; ML frameworks load data from it.
For an annotation set the file holds:

- the set as a ``sc:Dataset``: name, description, licence, creators, keywords,
  version, publications, grants, links and the source dataset,
- the files (``distribution``): the set document, the records table, and one
  ``FileSet`` each for the masks and the annotated image regions,
- the record sets: ``annotations`` (one record per mask, with the columns of the
  records table), ``images`` (the image region of each annotation), ``splits``
  (Croissant's ``cr:Split``), ``classes`` (an enumeration) and ``sessions`` (PROV
  activities).

Only records with a saved mask that exists inside the folder are paired; pending
and excluded records stay in the records table. Croissant requires a description,
a creator and a URL: if the set lacks one, :func:`check_croissant` names it and the
export refuses, rather than inventing a value.

Croissant has no property for how the annotations were made, sampled, split or
normalised. These are written twice: in words under the Croissant RAI properties
(``rai:dataAnnotationProtocol`` and others), and as data under this schema's own
terms (``bas:split``, ``bas:sampling``, ...), which Croissant allows as an external
vocabulary.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, get_args

from pydantic import BaseModel

from .crate import PROFILE, _FORMATS, _inside, _published
from .datamodel import AnnotationClass, AnnotationRecord, AnnotationSet, Person, Session
from .io import RECORDS_FILE, SET_FILE
from .mifa import (
    NOT_DESCRIBED,
    compose_method,
    compose_normalization,
    compose_overview,
    compose_split,
)

METADATA_FILE = "croissant.json"
SPEC = "http://mlcommons.org/croissant/1.1"
RAI_SPEC = "http://mlcommons.org/croissant/RAI/1.0"

# The context of the Croissant 1.1 specification (appendix 1, as in MLCommons' own
# example datasets), plus PROV-O and this schema's namespace.
_CONTEXT: dict[str, Any] = {
    "@language": "en",
    "@vocab": "https://schema.org/",
    "sc": "https://schema.org/",
    "cr": "http://mlcommons.org/croissant/",
    "rai": "http://mlcommons.org/croissant/RAI/",
    "dct": "http://purl.org/dc/terms/",
    "prov": "http://www.w3.org/ns/prov#",
    "bas": "https://w3id.org/bioimage-annotation-schema/",
    "annotation": "cr:annotation",
    "arrayShape": "cr:arrayShape",
    "citeAs": "cr:citeAs",
    "column": "cr:column",
    "conformsTo": "dct:conformsTo",
    "containedIn": "cr:containedIn",
    "data": {"@id": "cr:data", "@type": "@json"},
    "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
    "equivalentProperty": "cr:equivalentProperty",
    "examples": {"@id": "cr:examples", "@type": "@json"},
    "excludes": "cr:excludes",
    "extract": "cr:extract",
    "field": "cr:field",
    "fileProperty": "cr:fileProperty",
    "fileObject": "cr:fileObject",
    "fileSet": "cr:fileSet",
    "format": "cr:format",
    "includes": "cr:includes",
    "isArray": "cr:isArray",
    "isLiveDataset": "cr:isLiveDataset",
    "jsonPath": "cr:jsonPath",
    "key": "cr:key",
    "md5": "cr:md5",
    "parentField": "cr:parentField",
    "path": "cr:path",
    "recordSet": "cr:recordSet",
    "references": "cr:references",
    "regex": "cr:regex",
    "repeated": "cr:repeated",
    "replace": "cr:replace",
    "samplingRate": "cr:samplingRate",
    "sdVersion": "cr:sdVersion",
    "separator": "cr:separator",
    "source": "cr:source",
    "subField": "cr:subField",
    "transform": "cr:transform",
    "unArchive": "cr:unArchive",
    "value": "cr:value",
}
_SPLITS = {
    "training": "cr:TrainingSplit",
    "validation": "cr:ValidationSplit",
    "test": "cr:TestSplit",
}
_MASK_KINDS = {
    "instance": " Instance mask: each object has its own pixel value.",
    "semantic": " Semantic mask: each class has its own pixel value (see classes).",
}
# Fields of the set with no Croissant, schema.org, RAI or PROV property (or only a
# free-text one): written as data under the schema's own terms.
_CARRIED = (
    "schema_version",
    "changes",
    "ai_models_trained",
    "study",
    "methodology",
    "sampling",
    "split",
    "normalization",
    "notes",
    "extensions",
)

Node = dict[str, Any]


class CroissantNotReady(ValueError):
    """The set lacks what Croissant requires; ``missing`` names it."""

    def __init__(self, missing: Sequence[str]) -> None:
        self.missing = list(missing)
        super().__init__("Not ready for Croissant, missing:\n- " + "\n- ".join(missing))


def check_croissant(annotation_set: AnnotationSet) -> list[str]:
    """The fields Croissant requires that the set does not have (empty when ready).

    Croissant's ``description``, ``creator`` and ``url`` are the set's description,
    authors and url (where the set is published).
    """
    required = ("description", "authors", "url")
    return [name for name in required if not getattr(annotation_set, name)]


def _term(model: type[BaseModel], name: str) -> str:
    """The term of a schema field: its LinkML ``slot_uri``, else ``bas:<name>``."""
    extra: Any = model.model_fields[name].json_schema_extra or {}
    return extra.get("linkml_meta", {}).get("slot_uri", f"bas:{name}").replace("schema:", "sc:")


def _linked(value: Any) -> Any:
    """A value of the schema as JSON-LD under the schema's own terms."""
    if isinstance(value, BaseModel):
        model = type(value)
        class_uri = getattr(model, "linkml_meta").root.get("class_uri", f"bas:{model.__name__}")
        node: Node = {"@type": class_uri.replace("schema:", "sc:")}
        for name in model.model_fields:
            if (item := getattr(value, name)) is not None:
                node[_term(model, name)] = _linked(item)
        return node
    if isinstance(value, list):
        return [_linked(item) for item in value]
    if isinstance(value, dict):  # free-form metadata (extensions, tool parameters)
        return {"@type": "@json", "@value": value}
    return value.isoformat() if isinstance(value, datetime) else value


def _data_type(model: type[BaseModel], name: str) -> str:
    annotation = model.model_fields[name].annotation
    types = get_args(annotation) or (annotation,)
    return "sc:Integer" if int in types else "sc:DateTime" if datetime in types else "sc:Text"


def _person(person: Person) -> Node:
    return {
        "@type": "sc:Person",
        "@id": person.orcid,
        "name": f"{person.first_name} {person.last_name}",
        "givenName": person.first_name,
        "familyName": person.last_name,
        "email": person.email,
        "affiliation": [
            {"@type": "sc:Organization", "@id": org.ror, "name": org.name, "address": org.address}
            for org in person.affiliations or []
        ],
        "bas:roles": person.roles,
    }


def _compact(node: Any) -> Any:
    """``node`` without its empty values, at every level (embedded records and
    free-form metadata are left as they are)."""
    if isinstance(node, dict) and node.get("@type") != "@json":
        compacted = {k: v if k == "data" else _compact(v) for k, v in node.items()}
        return {k: v for k, v in compacted.items() if v not in (None, [], {})}
    if isinstance(node, list):
        return [c for item in node if (c := _compact(item)) not in (None, [], {})]
    return node


def _embedded(
    name: str,
    rows: Sequence[dict[str, Any]],
    model: type[BaseModel],
    data_types: dict[str, str] | None = None,
    **properties: Any,
) -> Node:
    """A RecordSet whose records are in the file itself, with one field per key the
    rows use. A field is typed and described after ``model``'s field of that name,
    unless ``data_types`` gives its type."""
    keys = list(dict.fromkeys(key for row in rows for key in row))
    fields = []
    for key in keys:
        info = model.model_fields.get(key)
        term = _term(model, key) if info else "bas:"
        fields.append(
            {
                "@type": "cr:Field",
                "@id": f"{name}/{key}",
                "description": info.description if info else None,
                "dataType": (data_types or {}).get(key) or _data_type(model, key),
                "equivalentProperty": None if term.startswith("bas:") else term,
            }
        )
    return {
        "@type": "cr:RecordSet",
        "@id": name,
        **properties,
        "key": {"@id": f"{name}/{keys[0]}"},
        "field": fields,
        # every record needs every field (mlcroissant), so unset ones are null
        "data": [{f"{name}/{key}": row.get(key) for key in keys} for row in rows],
    }


def _column(record_set: str, name: str, **properties: Any) -> Node:
    """A field read from the column ``name`` of the records table."""
    return {
        "@type": "cr:Field",
        "@id": f"{record_set}/{name}",
        "description": AnnotationRecord.model_fields[name].description,
        "dataType": _data_type(AnnotationRecord, name),
        "source": {"fileObject": {"@id": "records-file"}, "extract": {"column": name}},
        **properties,
    }


def _from_files(record_set: str, file_set: str, column: str, content: Node) -> list[Node]:
    """Two fields read from a FileSet: each file's path, which joins the file to the
    row of the records table that has this path in ``column``, and its content."""
    return [
        _column(
            record_set,
            column,
            # The regex keeps the whole path; mlcroissant needs a transform here to
            # compare the path with the column as text.
            source={
                "fileSet": {"@id": file_set},
                "extract": {"fileProperty": "fullpath"},
                "transform": {"regex": "^(.+)$"},
            },
            references={"fileObject": {"@id": "records-file"}, "extract": {"column": column}},
        ),
        {
            "@type": "cr:Field",
            **content,
            "source": {"fileSet": {"@id": file_set}, "extract": {"fileProperty": "content"}},
        },
    ]


def _file_object(folder: Path, file_id: str, name: str, **properties: Any) -> Node:
    path = folder / name
    return {
        "@type": "cr:FileObject",
        "@id": file_id,
        "name": name,
        "contentUrl": name,
        "encodingFormat": _FORMATS[path.suffix],
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        **properties,
    }


def _file_set(file_id: str, description: str, paths: Sequence[str]) -> Node:
    suffixes = {Path(path).suffix.lower() for path in paths}
    formats = sorted({_FORMATS.get(suffix, "application/octet-stream") for suffix in suffixes})
    return {
        "@type": "cr:FileSet",
        "@id": file_id,
        "name": file_id,
        "description": description,
        "encodingFormat": formats[0] if len(formats) == 1 else formats,
        "includes": list(paths),
    }


def _dataset(annotation_set: AnnotationSet) -> Node:
    """The dataset-level properties of the set."""
    meth = annotation_set.methodology
    study = annotation_set.study
    source = annotation_set.source_dataset
    method = compose_method(annotation_set, [])
    coverage = meth.coverage_description or meth.coverage
    protocol = [
        compose_overview(annotation_set),
        "" if method == NOT_DESCRIBED else method,
        f"Criteria: {meth.criteria}",
        f"Coverage: {coverage}" if coverage else "",
    ]
    doc: Node = {
        "@context": _CONTEXT,
        "@type": "sc:Dataset",
        "conformsTo": [SPEC, RAI_SPEC],
        "name": annotation_set.name,
        "description": annotation_set.description,
        "url": annotation_set.url,
        "license": f"https://spdx.org/licenses/{annotation_set.license}",
        "creator": [_person(p) for p in annotation_set.authors or []],
        "contributor": [_person(p) for p in meth.annotators or []],
        "dateCreated": annotation_set.created.isoformat(),
        "datePublished": _published(annotation_set),
        "version": annotation_set.version,
        "keywords": annotation_set.keywords,
        "citation": [
            {
                "@type": "sc:ScholarlyArticle",
                "@id": p.doi if str(p.doi).startswith("http") else None,
                "name": p.title,
                "author": p.authors,
                "identifier": p.doi,
                "datePublished": str(p.year) if p.year else None,
            }
            for p in (study.publications if study else None) or []
        ],
        "funding": [
            {
                "@type": "sc:Grant",
                "identifier": g.id,
                "funder": {"@type": "sc:Organization", "name": g.funder},
            }
            for g in (study.grants if study else None) or []
        ],
        "subjectOf": [
            {"@type": "sc:WebPage", "url": link.url, "description": link.description}
            for link in annotation_set.links or []
        ],
        "prov:wasDerivedFrom": source
        and {
            "@type": "sc:Dataset",
            "description": source.description,
            "identifier": source.identifier,
            "url": source.url,
            "license": source.license,
        },
        "prov:wasRevisionOf": annotation_set.previous_version
        and {"@id": annotation_set.previous_version},
        "rai:dataAnnotationProtocol": " ".join(
            part.rstrip(".") + "." for part in protocol if part
        ),
        "rai:dataAnnotationPlatform": [
            f"{tool.name} {tool.version or ''}".strip() for tool in meth.tools or []
        ],
        "rai:machineAnnotationTools": [
            f"{tool.model.name} {tool.model.version or ''}".strip()
            for tool in meth.tools or []
            if tool.model
        ],
        "rai:dataAnnotationAnalysis": [meth.confidence_level],
        "rai:dataPreprocessingProtocol": [compose_normalization(annotation_set)],
    }
    for name in _CARRIED:
        doc[_term(AnnotationSet, name)] = _linked(getattr(annotation_set, name))
    return doc


def build_croissant(
    annotation_set: AnnotationSet,
    records: Sequence[AnnotationRecord],
    folder: str | Path,
) -> dict[str, Any]:
    """The Croissant metadata (JSON-LD) of an annotation set's folder.

    The folder must hold the set document, the records table and the mask files.
    Raises :class:`CroissantNotReady` when the set or the folder lacks something
    Croissant requires.
    """
    folder = Path(folder)
    paired = [r for r in records if r.status == "annotated" and _inside(folder, r.mask_file)]
    missing = check_croissant(annotation_set)
    if not paired:
        missing.append("mask files (mask_file of the annotated records, inside the folder)")
    if missing:
        raise CroissantNotReady(missing)
    with_image = [r for r in paired if _inside(folder, r.input_file)]
    meth = annotation_set.methodology
    sessions = [s.model_dump(mode="json", exclude_none=True) for s in annotation_set.sessions or []]
    classes = [c.model_dump(exclude_none=True) for c in annotation_set.classes or []]
    for row in classes:  # Croissant names an enumeration's term "url"
        if "ontology_term" in row:
            row["url"] = row.pop("ontology_term")

    doc = _dataset(annotation_set)
    doc["distribution"] = [
        _file_object(folder, "set-file", SET_FILE, conformsTo=PROFILE),
        _file_object(folder, "records-file", RECORDS_FILE),
        _file_set(
            "mask-files", "The masks of the annotated records.", [str(r.mask_file) for r in paired]
        ),
    ]
    mask: Node = {
        "@id": "annotations/mask",
        "description": "The mask." + (_MASK_KINDS[meth.mask_kind] if meth.mask_kind else ""),
        "dataType": ["sc:ImageObject", "cr:Label"]
        + (["cr:SegmentationMask"] if "segmentation_mask" in meth.annotation_types else []),
    }
    references = {"split": "splits/name", "session": "sessions/id" if sessions else None}
    columns = [
        name
        for name in AnnotationRecord.model_fields
        if name != "mask_file" and any(getattr(r, name) is not None for r in paired)
    ]
    doc["recordSet"] = [
        {
            "@type": "cr:RecordSet",
            "@id": "annotations",
            "description": "One record per annotation with a saved mask: the mask and "
            "the columns of the records table.",
            "key": {"@id": "annotations/annotation_id"},
            # The path of the mask comes first: mlcroissant joins on the first field
            # that has a source and a reference.
            "field": _from_files("annotations", "mask-files", "mask_file", mask)
            + [
                _column("annotations", name, references={"field": {"@id": references.get(name)}})
                for name in columns
            ],
        },
        {
            "@type": "cr:RecordSet",
            "@id": "splits",
            "description": compose_split(annotation_set, records),
            "dataType": "cr:Split",
            "key": {"@id": "splits/name"},
            "field": [
                {"@type": "cr:Field", "@id": "splits/name", "dataType": "sc:Text"},
                {"@type": "cr:Field", "@id": "splits/url", "dataType": "sc:URL"},
            ],
            "data": [{"splits/name": name, "splits/url": url} for name, url in _SPLITS.items()],
        },
    ]
    if with_image:
        doc["distribution"].append(
            _file_set(
                "image-files",
                "The annotated image regions.",
                [str(r.input_file) for r in with_image],
            )
        )
        image = {"@id": "images/image", "dataType": "sc:ImageObject"}
        doc["recordSet"].append(
            {
                "@type": "cr:RecordSet",
                "@id": "images",
                "description": "The annotated image region of each annotation; "
                "annotation_id and input_file are those of annotations.",
                "field": _from_files("images", "image-files", "input_file", image)
                + [_column("images", "annotation_id")],
            }
        )
    if classes:
        doc["recordSet"].append(
            _embedded(
                "classes",
                classes,
                AnnotationClass,
                data_types={"url": "sc:URL"},
                description="The annotation classes.",
                dataType="sc:Enumeration",
            )
        )
    if sessions:
        doc["recordSet"].append(
            _embedded(
                "sessions",
                sessions,
                Session,
                description="The annotation sessions; annotations/session refers to them.",
                dataType="prov:Activity",
            )
        )
    return _compact(doc)


def write_croissant(
    annotation_set: AnnotationSet,
    records: Sequence[AnnotationRecord],
    folder: str | Path,
) -> Path:
    """Write ``croissant.json`` into ``folder``; returns its path."""
    doc = build_croissant(annotation_set, records, folder)  # refuses before writing
    target = Path(folder) / METADATA_FILE
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(target)
    return target
