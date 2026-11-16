from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "1.12.0"
version = "0.1.0"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'bas',
     'default_range': 'string',
     'description': 'Describes sets of image annotations made for training or '
                    'evaluating AI models: what was annotated, from which images, '
                    'how, by whom, and how the annotations are split, plus one '
                    'record per annotation. Fields that correspond to MIFA '
                    '(bia-mifa-models, BioImage Archive) carry mappings to it, so '
                    'a MIFA submission can be derived from a document that follows '
                    'this schema.',
     'id': 'https://w3id.org/bioimage-annotation-schema',
     'imports': ['linkml:types'],
     'license': 'CC-BY-4.0',
     'name': 'bioimage_annotation_schema',
     'prefixes': {'bas': {'prefix_prefix': 'bas',
                          'prefix_reference': 'https://w3id.org/bioimage-annotation-schema/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'},
                  'mifa': {'prefix_prefix': 'mifa',
                           'prefix_reference': 'https://w3id.org/BioImage-Archive/bia-mifa-models/'},
                  'pav': {'prefix_prefix': 'pav',
                          'prefix_reference': 'http://purl.org/pav/'},
                  'prov': {'prefix_prefix': 'prov',
                           'prefix_reference': 'http://www.w3.org/ns/prov#'},
                  'schema': {'prefix_prefix': 'schema',
                             'prefix_reference': 'http://schema.org/'}},
     'see_also': ['https://github.com/Leiden-Cell-Observatory/bioimage-annotation-schema'],
     'source_file': 'src/linkml/bioimage_annotation_schema.yaml',
     'title': 'Bioimage Annotation Schema',
     'types': {'IsccCode': {'description': 'ISCC Image-Code (ISO 24138), for '
                                           'finding near-duplicate images.',
                            'from_schema': 'https://w3id.org/bioimage-annotation-schema',
                            'name': 'IsccCode',
                            'pattern': '^ISCC:[A-Z2-7]+$',
                            'typeof': 'string'},
               'PixelDigest': {'description': 'Pixel SHA-256 - lowercase hex '
                                              'SHA-256 of the UTF-8 text '
                                              "'<dtype>|<shape>|' followed by the "
                                              'pixel values in C order, '
                                              'little-endian. <dtype> is the NumPy '
                                              "dtype string with '<' byte order "
                                              "(e.g. '<u2', '|u1'), <shape> the "
                                              "Python tuple text (e.g. '(512, "
                                              "512)'). Independent of file format "
                                              'and compression.',
                               'from_schema': 'https://w3id.org/bioimage-annotation-schema',
                               'name': 'PixelDigest',
                               'pattern': '^[0-9a-f]{64}$',
                               'typeof': 'string'}}} )

class AnnotationType(str, Enum):
    """
    Same values as MIFA's AnnotationType.
    """
    class_labels = "class_labels"
    bounding_boxes = "bounding_boxes"
    counts = "counts"
    derived_annotations = "derived_annotations"
    geometrical_annotations = "geometrical_annotations"
    graphs = "graphs"
    point_annotations = "point_annotations"
    segmentation_mask = "segmentation_mask"
    tracks = "tracks"
    weak_annotations = "weak_annotations"
    other = "other"


class MaskKind(str, Enum):
    instance = "instance"
    """
    Each object has its own pixel value.
    """
    semantic = "semantic"
    """
    Each class has its own pixel value (see AnnotationClass.label_value).
    """


class AnnotationMethod(str, Enum):
    manual = "manual"
    semi_automatic = "semi_automatic"
    automatic = "automatic"


class Coverage(str, Enum):
    all = "all"
    representative = "representative"
    partial = "partial"


class ToolMode(str, Enum):
    automatic = "automatic"
    interactive = "interactive"
    human_in_the_loop = "human_in_the_loop"


class SelectionMode(str, Enum):
    all = "all"
    random = "random"
    specific = "specific"


class SplitStrategy(str, Enum):
    random_split = "random_split"
    expert_review = "expert_review"
    cross_validation = "cross_validation"


class NormalizationMethod(str, Enum):
    percentile = "percentile"
    """
    Per-image percentile bounds mapped to [0, 1].
    """
    none = "none"
    """
    Raw intensities.
    """


class SessionKind(str, Enum):
    annotate = "annotate"
    review = "review"


class SessionStatus(str, Enum):
    open = "open"
    finished = "finished"
    interrupted = "interrupted"


class SplitName(str, Enum):
    training = "training"
    validation = "validation"
    test = "test"


class RecordStatus(str, Enum):
    pending = "pending"
    """
    Not yet annotated.
    """
    annotated = "annotated"
    """
    Annotation saved.
    """
    excluded = "excluded"
    """
    Looked at and left out (e.g. out of focus); no mask, not used for training.
    """



class AnnotationSet(ConfiguredBaseModel):
    """
    A set of image annotations for AI: one document per set. The annotations themselves are AnnotationRecords, usually kept as a CSV table next to it.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'schema:Dataset',
         'close_mappings': ['mifa:Annotations'],
         'from_schema': 'https://w3id.org/bioimage-annotation-schema',
         'tree_root': True})

    schema_version: str = Field(default=..., description="""Version of this schema the document follows (semantic versioning).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    name: str = Field(default=..., description="""Short name of the set.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'Person', 'Tool', 'Model', 'AnnotationClass'],
         'slot_uri': 'schema:name'} })
    description: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'Study', 'SourceDataset', 'AnnotationClass'],
         'slot_uri': 'schema:description'} })
    created: datetime  = Field(default=..., description="""When the set was created.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet'], 'slot_uri': 'schema:dateCreated'} })
    license: str = Field(default=..., description="""License of the annotations, preferably an SPDX identifier (CC-BY-4.0, CC0-1.0).""", json_schema_extra = { "linkml_meta": {'close_mappings': ['mifa:license'],
         'domain_of': ['AnnotationSet', 'SourceDataset'],
         'slot_uri': 'schema:license'} })
    authors: Optional[list[Person]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet'],
         'exact_mappings': ['mifa:author'],
         'slot_uri': 'schema:author'} })
    keywords: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet'],
         'exact_mappings': ['mifa:keywords'],
         'slot_uri': 'schema:keywords'} })
    study: Optional[Study] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    source_dataset: Optional[SourceDataset] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    methodology: Methodology = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    classes: Optional[list[AnnotationClass]] = Field(default=None, description="""The annotation classes (e.g. nucleus, cell, background).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    sampling: Optional[Sampling] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    split: Optional[Split] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'AnnotationRecord']} })
    normalization: Optional[Normalization] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    sessions: Optional[list[Session]] = Field(default=None, description="""Annotation sessions, oldest first. Records refer to them by id.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    notes: Optional[str] = Field(default=None, description="""Free text - context, caveats, known issues.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    extensions: Optional[Any] = Field(default=None, description="""Tool- or project-specific metadata this schema does not cover, under a namespace key such as the tool name.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })

    @field_validator('schema_version')
    def pattern_schema_version(cls, v):
        pattern=re.compile(r"^0\.1\.[0-9]+$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid schema_version format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid schema_version format: {v}"
            raise ValueError(err_msg)
        return v


class Person(ConfiguredBaseModel):
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'schema:Person',
         'close_mappings': ['mifa:Author'],
         'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    name: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'Person', 'Tool', 'Model', 'AnnotationClass'],
         'slot_uri': 'schema:name'} })
    affiliation: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Person'], 'slot_uri': 'schema:affiliation'} })
    orcid: Optional[str] = Field(default=None, description="""ORCID iD as URL.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Person'], 'exact_mappings': ['mifa:orcid_id']} })
    email: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Person'],
         'exact_mappings': ['mifa:email'],
         'slot_uri': 'schema:email'} })

    @field_validator('orcid')
    def pattern_orcid(cls, v):
        pattern=re.compile(r"^https://orcid\.org/[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid orcid format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid orcid format: {v}"
            raise ValueError(err_msg)
        return v


class Study(ConfiguredBaseModel):
    """
    Biological and experimental context of the images.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'close_mappings': ['mifa:Study'],
         'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    title: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Study'], 'exact_mappings': ['mifa:title']} })
    description: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'Study', 'SourceDataset', 'AnnotationClass'],
         'exact_mappings': ['mifa:description']} })
    organism: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Study']} })
    imaging_method: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Study']} })
    funding_statement: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Study'], 'exact_mappings': ['mifa:funding_statement']} })


class SourceDataset(ConfiguredBaseModel):
    """
    The image dataset the annotated images come from.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    description: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'Study', 'SourceDataset', 'AnnotationClass']} })
    identifier: Optional[str] = Field(default=None, description="""Accession or DOI, e.g. S-BIAD123 or idr0001.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SourceDataset'], 'slot_uri': 'schema:identifier'} })
    url: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['SourceDataset', 'Model'], 'slot_uri': 'schema:url'} })
    license: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'SourceDataset'], 'slot_uri': 'schema:license'} })


class Methodology(ConfiguredBaseModel):
    """
    How the annotations were made.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    overview: Optional[str] = Field(default=None, description="""Short summary of the type of annotation and how it was made.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology'], 'exact_mappings': ['mifa:annotation_overview']} })
    annotation_types: list[AnnotationType] = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology'], 'exact_mappings': ['mifa:annotation_type']} })
    mask_kind: Optional[MaskKind] = Field(default=None, description="""For segmentation masks - one value per object (instance) or per class (semantic).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology']} })
    method: Optional[AnnotationMethod] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology', 'Normalization']} })
    method_description: Optional[str] = Field(default=None, description="""How the annotations were created, in words: who, which software, consensus and quality checks.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology'], 'exact_mappings': ['mifa:annotation_method']} })
    criteria: str = Field(default=..., description="""What counts as an object and where its boundary is, in words.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology'], 'exact_mappings': ['mifa:annotation_criteria']} })
    coverage: Optional[Coverage] = Field(default=None, description="""Within an annotated region, whether all objects are annotated, a representative selection, or only some.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology']} })
    coverage_description: Optional[str] = Field(default=None, description="""Which images were annotated and what share of the dataset, in words.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology'], 'exact_mappings': ['mifa:annotation_coverage']} })
    confidence_level: Optional[str] = Field(default=None, description="""Confidence in the annotations' accuracy, e.g. annotator experience or inter-annotator agreement.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology'],
         'exact_mappings': ['mifa:annotation_confidence_level']} })
    tools: Optional[list[Tool]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology']} })


class Tool(ConfiguredBaseModel):
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'schema:SoftwareApplication',
         'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    name: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'Person', 'Tool', 'Model', 'AnnotationClass'],
         'slot_uri': 'schema:name'} })
    version: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Tool', 'Model'], 'slot_uri': 'schema:softwareVersion'} })
    mode: Optional[ToolMode] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Tool', 'PlaneSelection']} })
    model: Optional[Model] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Tool', 'Session']} })
    parameters: Optional[Any] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Tool']} })


class Model(ConfiguredBaseModel):
    """
    An AI model that proposed annotations.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    name: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'Person', 'Tool', 'Model', 'AnnotationClass']} })
    version: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Tool', 'Model']} })
    url: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['SourceDataset', 'Model']} })
    doi: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Model']} })


class AnnotationClass(ConfiguredBaseModel):
    """
    One annotation class.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    name: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'Person', 'Tool', 'Model', 'AnnotationClass']} })
    description: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'Study', 'SourceDataset', 'AnnotationClass']} })
    label_value: Optional[int] = Field(default=None, description="""Pixel value of the class in semantic masks. Not used for instance masks, where each object has its own value.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationClass']} })
    ontology_term: Optional[str] = Field(default=None, description="""IRI of an ontology term for the class, e.g. a CL or GO term.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationClass']} })
    color: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationClass']} })

    @field_validator('color')
    def pattern_color(cls, v):
        pattern=re.compile(r"^#[0-9A-Fa-f]{6}$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid color format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid color format: {v}"
            raise ValueError(err_msg)
        return v


class PlaneSelection(ConfiguredBaseModel):
    """
    Which timepoints or z-slices were annotated.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    mode: SelectionMode = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Tool', 'PlaneSelection']} })
    values: Optional[list[int]] = Field(default=None, description="""The indices, for mode 'specific'.""", json_schema_extra = { "linkml_meta": {'domain_of': ['PlaneSelection']} })
    n: Optional[int] = Field(default=None, description="""How many were drawn, for mode 'random'.""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['PlaneSelection']} })


class Sampling(ConfiguredBaseModel):
    """
    Which parts of the images were annotated. Per-annotation detail is in the records.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    label_channel: Optional[int] = Field(default=None, description="""Channel the annotations were drawn on.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Sampling']} })
    input_channels: Optional[list[int]] = Field(default=None, description="""Channels meant as model input; may differ from label_channel (annotate on a nuclear stain, train on brightfield).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Sampling']} })
    timepoints: Optional[PlaneSelection] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Sampling']} })
    z_slices: Optional[PlaneSelection] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Sampling']} })
    volumetric: Optional[bool] = Field(default=None, description="""True if annotations are 3D volumes rather than 2D planes.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Sampling']} })
    patches: Optional[Patches] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Sampling']} })


class Patches(ConfiguredBaseModel):
    """
    Present if annotations cover patches rather than whole planes.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    width: int = Field(default=..., ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Patches']} })
    height: int = Field(default=..., ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Patches']} })
    per_image: Optional[int] = Field(default=None, ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Patches']} })
    random: Optional[bool] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Patches']} })


class Split(ConfiguredBaseModel):
    """
    How annotations were divided over training, validation and test.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    strategy: Optional[SplitStrategy] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Split']} })
    unit: Optional[str] = Field(default=None, description="""Level at which data are assigned to a split; all annotations of one unit share a split. 'image' or 'well', or another level named by the tool.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Split']} })
    rationale: Optional[str] = Field(default=None, description="""Why this unit, e.g. 'fields within a well do not overlap'.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Split']} })
    stratify_by: Optional[list[str]] = Field(default=None, description="""Metadata keys the split was balanced on (e.g. cell_line, treatment).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Split']} })
    seed: Optional[int] = Field(default=None, description="""Seed of the random choices, to reproduce the selection with the same tool.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Split']} })


class Normalization(ConfiguredBaseModel):
    """
    Intensity normalisation intended for model input.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    method: NormalizationMethod = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology', 'Normalization']} })
    percentile_low: Optional[float] = Field(default=None, ge=0, le=100, json_schema_extra = { "linkml_meta": {'domain_of': ['Normalization']} })
    percentile_high: Optional[float] = Field(default=None, ge=0, le=100, json_schema_extra = { "linkml_meta": {'domain_of': ['Normalization']} })
    clip: Optional[bool] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Normalization']} })


class Session(ConfiguredBaseModel):
    """
    One annotation session - who, when, with what, and a note.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'prov:Activity',
         'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    id: int = Field(default=..., ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Session']} })
    kind: SessionKind = Field(default=..., description="""'annotate' creates annotations, 'review' checks or corrects them.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Session']} })
    started: datetime  = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Session'], 'slot_uri': 'prov:startedAtTime'} })
    ended: Optional[datetime ] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Session'], 'slot_uri': 'prov:endedAtTime'} })
    status: Optional[SessionStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Session', 'AnnotationRecord']} })
    annotator: Optional[str] = Field(default=None, description="""Who annotated - a name, ORCID or pseudonym.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Session']} })
    software: Optional[str] = Field(default=None, description="""Software and version, e.g. 'omero-annotate-ai 0.5.0'.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Session']} })
    model: Optional[str] = Field(default=None, description="""Name of the AI model used in the session, if any.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Tool', 'Session']} })
    n_annotated: Optional[int] = Field(default=None, ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Session']} })
    note: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Session']} })


class AnnotationRecord(ConfiguredBaseModel):
    """
    One annotation of a set: the image region it covers, its split, its state and its files. Flat, so a table of records is a CSV file with one column per field (well_metadata and external_ids as JSON text).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'close_mappings': ['mifa:FileLevelMetadata'],
         'from_schema': 'https://w3id.org/bioimage-annotation-schema',
         'rules': [{'description': 'An excluded annotation has no mask.',
                    'postconditions': {'slot_conditions': {'mask_file': {'name': 'mask_file',
                                                                         'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'status': {'equals_string': 'excluded',
                                                                     'name': 'status'}}}},
                   {'description': 'A patch needs all four of x, y, width and height.',
                    'postconditions': {'slot_conditions': {'patch_height': {'name': 'patch_height',
                                                                            'value_presence': 'PRESENT'},
                                                           'patch_width': {'name': 'patch_width',
                                                                           'value_presence': 'PRESENT'},
                                                           'patch_y': {'name': 'patch_y',
                                                                       'value_presence': 'PRESENT'}}},
                    'preconditions': {'slot_conditions': {'patch_x': {'name': 'patch_x',
                                                                      'value_presence': 'PRESENT'}}}},
                   {'description': 'A volumetric annotation needs z_start and z_end.',
                    'postconditions': {'slot_conditions': {'z_end': {'name': 'z_end',
                                                                     'value_presence': 'PRESENT'}}},
                    'preconditions': {'slot_conditions': {'z_start': {'name': 'z_start',
                                                                      'value_presence': 'PRESENT'}}}}]})

    annotation_id: str = Field(default=..., description="""Identifier of the annotation, unique within the set. Files are named after it.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord'],
         'exact_mappings': ['mifa:annotation_id'],
         'slot_uri': 'schema:identifier'} })
    image_uri: str = Field(default=..., description="""The source image - omero:image:<id>, an http(s) URL of an OME-Zarr image, or another resolvable URI.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord'], 'exact_mappings': ['mifa:source_image_id']} })
    image_name: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    level: Optional[int] = Field(default=None, description="""Multiscale level the coordinates refer to (0 = full resolution).""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    well: Optional[str] = Field(default=None, description="""Plate well, e.g. B2.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    field: Optional[str] = Field(default=None, description="""Field (well sample) within the well.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    well_metadata: Optional[str] = Field(default=None, description="""Key-value metadata of the well as a JSON object, e.g. {\"cell_line\":\"U2OS\"}.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    channel: Optional[int] = Field(default=None, ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    timepoint: Optional[int] = Field(default=None, ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    z_slice: Optional[int] = Field(default=None, description="""Z-slice of a 2D annotation.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    z_start: Optional[int] = Field(default=None, description="""First z-slice of a volumetric annotation.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    z_end: Optional[int] = Field(default=None, description="""Last z-slice of a volumetric annotation (inclusive).""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    patch_x: Optional[int] = Field(default=None, ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    patch_y: Optional[int] = Field(default=None, ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    patch_width: Optional[int] = Field(default=None, ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    patch_height: Optional[int] = Field(default=None, ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    split: SplitName = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'AnnotationRecord']} })
    status: RecordStatus = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Session', 'AnnotationRecord']} })
    annotation_type: Optional[AnnotationType] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord'], 'exact_mappings': ['mifa:annotation_type']} })
    created_at: Optional[datetime ] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord'],
         'exact_mappings': ['mifa:annotation_creation_time'],
         'slot_uri': 'pav:authoredOn'} })
    updated_at: Optional[datetime ] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord'], 'slot_uri': 'pav:lastUpdateOn'} })
    session: Optional[int] = Field(default=None, description="""id of the session (in the set) that last saved this annotation.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    input_file: Optional[str] = Field(default=None, description="""Path of the annotated image region, relative to the set's folder.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    mask_file: Optional[str] = Field(default=None, description="""Path of the mask, relative to the set's folder.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    input_digest: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    mask_digest: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    input_iscc: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    mask_iscc: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    external_ids: Optional[str] = Field(default=None, description="""Identifiers of copies in other systems as a JSON object, e.g. {\"omero_roi\":\"123\",\"omero_label_image\":\"456\"}.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
AnnotationSet.model_rebuild()
Person.model_rebuild()
Study.model_rebuild()
SourceDataset.model_rebuild()
Methodology.model_rebuild()
Tool.model_rebuild()
Model.model_rebuild()
AnnotationClass.model_rebuild()
PlaneSelection.model_rebuild()
Sampling.model_rebuild()
Patches.model_rebuild()
Split.model_rebuild()
Normalization.model_rebuild()
Session.model_rebuild()
AnnotationRecord.model_rebuild()
