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
     'see_also': ['https://github.com/Leiden-Cell-Observatory/bioimage-annotation-schema',
                  'https://bioimage-archive.github.io/bia-mifa-models/'],
     'source_file': 'src/bioimage_annotation_schema/schema/bioimage_annotation_schema.yaml',
     'title': 'Bioimage Annotation Schema',
     'types': {'IsccCode': {'description': 'An ISCC code (ISO 24138) in its '
                                           'canonical text form. Which code type '
                                           'and how it was made is declared in the '
                                           "set's content_codes.",
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
                                              'and compression. An exact-match '
                                              'check of the saved files; not the '
                                              'IMAGEWALK canonical bytes '
                                              '(IEP-0018: big-endian, no dtype and '
                                              'shape prefix), so it does not equal '
                                              'a SHA-256 another bioimage tool '
                                              'computes over IMAGEWALK.',
                               'from_schema': 'https://w3id.org/bioimage-annotation-schema',
                               'name': 'PixelDigest',
                               'pattern': '^[0-9a-f]{64}$',
                               'typeof': 'string'}}} )

class License(str, Enum):
    """
    Licenses the BioImage Archive accepts for annotations.
    """
    CC_BY_4FULL_STOP0 = "CC-BY-4.0"
    """
    Creative Commons Attribution 4.0: reuse with credit.
    """
    CC0_1FULL_STOP0 = "CC0-1.0"
    """
    Creative Commons Zero: no rights reserved.
    """


class AnnotationType(str, Enum):
    """
    Same values as MIFA's AnnotationType.
    """
    class_labels = "class_labels"
    """
    Tags that identify features, patterns or classes in images.
    """
    bounding_boxes = "bounding_boxes"
    """
    Rectangles completely enclosing a structure of interest.
    """
    counts = "counts"
    """
    Number of objects, such as cells, in an image.
    """
    derived_annotations = "derived_annotations"
    """
    Values derived from the images, e.g. point spread function, signal-to-noise ratio or focus.
    """
    geometrical_annotations = "geometrical_annotations"
    """
    Polygons and shapes outlining a region of interest: primitives, 2D polygons, 3D meshes.
    """
    graphs = "graphs"
    """
    Graphs of the morphology, connectivity or spatial arrangement of structures, e.g. skeletons.
    """
    point_annotations = "point_annotations"
    """
    Coordinates of points of interest, e.g. object centroids or landmarks.
    """
    segmentation_mask = "segmentation_mask"
    """
    An image of the same size as the source, each pixel value marking an object, class or background.
    """
    tracks = "tracks"
    """
    Movement or trajectories of objects through a sequence of images.
    """
    weak_annotations = "weak_annotations"
    """
    Rough, imprecise annotations that are fast to make, e.g. a scribble per object.
    """
    other = "other"
    """
    Another kind; describe it in the methodology overview.
    """


class IsccCodeType(str, Enum):
    """
    ISCC code types used for images.
    """
    image_code = "image_code"
    """
    ISCC-UNIT Image-Code - a perceptual code of a small grayscale image; codes of similar images differ in few bits, so it finds near-duplicates.
    """
    iscc_sum = "iscc_sum"
    """
    ISCC-SUM - Data-Code plus Instance-Code over a byte stream (for bioimages, the IMAGEWALK canonical bytes); the Instance-Code part matches only identical content.
    """
    iscc_code = "iscc_code"
    """
    A composite ISCC-CODE of several units.
    """


class MaskKind(str, Enum):
    """
    How pixel values in a segmentation mask are assigned.
    """
    instance = "instance"
    """
    Each object has its own pixel value.
    """
    semantic = "semantic"
    """
    Each class has its own pixel value (see AnnotationClass.label_value).
    """


class AnnotationMethod(str, Enum):
    """
    How much of the annotation was done by people and how much by software.
    """
    manual = "manual"
    """
    Drawn by hand.
    """
    semi_automatic = "semi_automatic"
    """
    Proposed by software and checked or corrected by a person.
    """
    automatic = "automatic"
    """
    Made by software without correction.
    """


class Coverage(str, Enum):
    """
    How completely the objects in an annotated region are annotated.
    """
    all = "all"
    """
    Every object in the region is annotated.
    """
    representative = "representative"
    """
    A representative selection of the objects is annotated.
    """
    partial = "partial"
    """
    Only some objects are annotated, without claim of representativeness.
    """


class ToolMode(str, Enum):
    """
    How a tool was used.
    """
    automatic = "automatic"
    """
    The tool annotated on its own.
    """
    interactive = "interactive"
    """
    A person annotated with the tool's help, e.g. prompts to a segmentation model.
    """
    human_in_the_loop = "human_in_the_loop"
    """
    The tool's model was retrained on corrected annotations during the work.
    """


class SelectionMode(str, Enum):
    """
    How timepoints or z-slices were chosen.
    """
    all = "all"
    """
    All of them.
    """
    random = "random"
    """
    A random draw of n.
    """
    specific = "specific"
    """
    The indices listed in values.
    """


class SplitStrategy(str, Enum):
    """
    How annotations were assigned to splits.
    """
    random_split = "random_split"
    """
    At random, by unit.
    """
    expert_review = "expert_review"
    """
    Chosen by a person.
    """
    cross_validation = "cross_validation"
    """
    Rotating folds; the split recorded is one fold.
    """


class NormalizationMethod(str, Enum):
    """
    Intensity normalisation methods.
    """
    percentile = "percentile"
    """
    Per-image percentile bounds mapped to [0, 1].
    """
    none = "none"
    """
    Raw intensities.
    """


class SessionKind(str, Enum):
    """
    What a session did.
    """
    annotate = "annotate"
    """
    Created annotations.
    """
    review = "review"
    """
    Checked or corrected existing annotations.
    """


class SessionStatus(str, Enum):
    """
    State of a session.
    """
    open = "open"
    """
    In progress.
    """
    finished = "finished"
    """
    Ended normally.
    """
    interrupted = "interrupted"
    """
    Ended without finishing, e.g. a crash or a closed window.
    """


class SplitName(str, Enum):
    """
    The splits of a set.
    """
    training = "training"
    """
    Used to train models.
    """
    validation = "validation"
    """
    Used to tune and select models during training.
    """
    test = "test"
    """
    Held out to evaluate the final model.
    """


class RecordStatus(str, Enum):
    """
    State of an annotation record.
    """
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
    name: str = Field(default=..., description="""Short name of the set.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet',
                       'Organisation',
                       'Tool',
                       'Model',
                       'AnnotationClass'],
         'slot_uri': 'schema:name'} })
    description: Optional[str] = Field(default=None, description="""What the set contains and what it is for, in a few sentences.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet',
                       'Link',
                       'Study',
                       'SourceDataset',
                       'AnnotationClass'],
         'slot_uri': 'schema:description'} })
    created: datetime  = Field(default=..., description="""When the set was created.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet'], 'slot_uri': 'schema:dateCreated'} })
    license: License = Field(default=..., description="""License of the annotations. Only the two licences the BioImage Archive accepts are allowed.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'SourceDataset'],
         'exact_mappings': ['mifa:license'],
         'slot_uri': 'schema:license'} })
    version: Optional[str] = Field(default=None, description="""Version of this set, e.g. \"1\" or \"1.1\".""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'Tool', 'Model'],
         'exact_mappings': ['mifa:version']} })
    changes: Optional[str] = Field(default=None, description="""What changed since the previous version.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet'], 'exact_mappings': ['mifa:changes']} })
    previous_version: Optional[str] = Field(default=None, description="""Identifier (DOI or URL) of the previous version of the set.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet'], 'exact_mappings': ['mifa:previous_version']} })
    ai_models_trained: Optional[list[str]] = Field(default=None, description="""AI models trained on these annotations, by DOI or URL (e.g. a BioImage Model Zoo entry).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet'], 'exact_mappings': ['mifa:ai_models_trained']} })
    authors: Optional[list[Person]] = Field(default=None, description="""Authors of the set, in citation order.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'Publication'],
         'exact_mappings': ['mifa:author'],
         'slot_uri': 'schema:author'} })
    keywords: Optional[list[str]] = Field(default=None, description="""Keywords or tags that describe the set.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet'],
         'exact_mappings': ['mifa:keywords'],
         'slot_uri': 'schema:keywords'} })
    links: Optional[list[Link]] = Field(default=None, description="""Web pages about the set or its data, e.g. a repository or a project page.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    study: Optional[Study] = Field(default=None, description="""The biological and experimental context of the images.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    source_dataset: Optional[SourceDataset] = Field(default=None, description="""The image dataset the annotated images come from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    methodology: Methodology = Field(default=..., description="""How the annotations were made.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    classes: Optional[list[AnnotationClass]] = Field(default=None, description="""The annotation classes (e.g. nucleus, cell, background).""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    sampling: Optional[Sampling] = Field(default=None, description="""Which channels, planes and regions of the images were annotated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    split: Optional[Split] = Field(default=None, description="""How the annotations were divided over training, validation and test.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'AnnotationRecord']} })
    normalization: Optional[Normalization] = Field(default=None, description="""Intensity normalisation intended for model input.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
    content_codes: Optional[ContentCodes] = Field(default=None, description="""How the ISCC codes in the records were made. Required when any record has input_iscc, mask_iscc or image_iscc: codes are only comparable when they were made the same way.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet']} })
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
    """
    A person: an author of the set or an annotator.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'schema:Person',
         'exact_mappings': ['mifa:Author'],
         'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    first_name: str = Field(default=..., description="""Given name.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Person'],
         'exact_mappings': ['mifa:author_first_name'],
         'slot_uri': 'schema:givenName'} })
    last_name: str = Field(default=..., description="""Family name, with particles such as \"van der\".""", json_schema_extra = { "linkml_meta": {'domain_of': ['Person'],
         'exact_mappings': ['mifa:author_last_name'],
         'slot_uri': 'schema:familyName'} })
    orcid: Optional[str] = Field(default=None, description="""ORCID iD as URL.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Person'], 'exact_mappings': ['mifa:orcid_id']} })
    email: Optional[str] = Field(default=None, description="""Email address.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Person'],
         'exact_mappings': ['mifa:email'],
         'slot_uri': 'schema:email'} })
    affiliations: Optional[list[Organisation]] = Field(default=None, description="""Organisations the person is affiliated with.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Person'],
         'exact_mappings': ['mifa:organisation'],
         'slot_uri': 'schema:affiliation'} })
    roles: Optional[list[str]] = Field(default=None, description="""Roles in the work, e.g. annotator, data curator.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Person'], 'exact_mappings': ['mifa:role']} })

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


class Organisation(ConfiguredBaseModel):
    """
    An organisation a person is affiliated with.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'schema:Organization',
         'exact_mappings': ['mifa:OrganisationInfo'],
         'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    name: str = Field(default=..., description="""Name of the organisation.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet',
                       'Organisation',
                       'Tool',
                       'Model',
                       'AnnotationClass'],
         'exact_mappings': ['mifa:organisation_name'],
         'slot_uri': 'schema:name'} })
    ror: Optional[str] = Field(default=None, description="""ROR identifier as URL, e.g. https://ror.org/027bh9e22.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Organisation'], 'exact_mappings': ['mifa:ror_id']} })
    address: Optional[str] = Field(default=None, description="""Postal address of the organisation.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Organisation'], 'exact_mappings': ['mifa:address']} })

    @field_validator('ror')
    def pattern_ror(cls, v):
        pattern=re.compile(r"^https://ror\.org/[0-9a-z]{9}$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid ror format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid ror format: {v}"
            raise ValueError(err_msg)
        return v


class Link(ConfiguredBaseModel):
    """
    A web page about the set or its data.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    url: str = Field(default=..., description="""URL of the page.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Link', 'SourceDataset', 'Model'],
         'exact_mappings': ['mifa:link_url'],
         'slot_uri': 'schema:url'} })
    description: Optional[str] = Field(default=None, description="""What the linked page contains.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet',
                       'Link',
                       'Study',
                       'SourceDataset',
                       'AnnotationClass'],
         'exact_mappings': ['mifa:link_description']} })


class Publication(ConfiguredBaseModel):
    """
    A publication associated with the study.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'schema:ScholarlyArticle',
         'exact_mappings': ['mifa:Publications'],
         'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    title: str = Field(default=..., description="""Title of the publication.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Publication', 'Study'],
         'exact_mappings': ['mifa:publication_title']} })
    authors: str = Field(default=..., description="""Author list as written in the reference.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'Publication'],
         'exact_mappings': ['mifa:publication_authors']} })
    doi: Optional[str] = Field(default=None, description="""DOI as URL, e.g. https://doi.org/10.1038/s41592-019-0612-7.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Publication', 'Model'],
         'exact_mappings': ['mifa:publication_doi']} })
    year: Optional[int] = Field(default=None, description="""Year of publication.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Publication'], 'exact_mappings': ['mifa:publication_year']} })
    pubmed_id: Optional[str] = Field(default=None, description="""PubMed identifier.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Publication'], 'exact_mappings': ['mifa:pubmed_id']} })


class Grant(ConfiguredBaseModel):
    """
    A grant that funded the study.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'exact_mappings': ['mifa:GrantReference'],
         'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    id: str = Field(default=..., description="""Identifier of the grant.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Grant', 'Session'], 'exact_mappings': ['mifa:grant_id']} })
    funder: str = Field(default=..., description="""Name of the funding body.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Grant'], 'exact_mappings': ['mifa:funder']} })


class Study(ConfiguredBaseModel):
    """
    Biological and experimental context of the images.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'close_mappings': ['mifa:Study'],
         'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    title: str = Field(default=..., description="""Title of the study; often the title of the associated publication.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Publication', 'Study'], 'exact_mappings': ['mifa:title']} })
    description: Optional[str] = Field(default=None, description="""Brief description of the study, including the biological application of the images.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet',
                       'Link',
                       'Study',
                       'SourceDataset',
                       'AnnotationClass'],
         'exact_mappings': ['mifa:description']} })
    organism: Optional[str] = Field(default=None, description="""Organism the samples come from, e.g. Homo sapiens.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Study']} })
    organism_term: Optional[str] = Field(default=None, description="""IRI of an NCBI Taxonomy term for the organism, e.g. http://purl.obolibrary.org/obo/NCBITaxon_9606.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Study']} })
    imaging_method: Optional[str] = Field(default=None, description="""Imaging method, e.g. confocal fluorescence microscopy.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Study']} })
    imaging_method_term: Optional[str] = Field(default=None, description="""IRI of an FBbi term for the imaging method, e.g. http://purl.obolibrary.org/obo/FBbi_00100013.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Study']} })
    funding_statement: Optional[str] = Field(default=None, description="""How the study was funded, in words.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Study'], 'exact_mappings': ['mifa:funding_statement']} })
    publications: Optional[list[Publication]] = Field(default=None, description="""Publications associated with the study.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Study'], 'exact_mappings': ['mifa:publications']} })
    grants: Optional[list[Grant]] = Field(default=None, description="""Grants that funded the study.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Study'], 'exact_mappings': ['mifa:grants']} })
    acknowledgements: Optional[str] = Field(default=None, description="""People or groups to acknowledge.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Study'], 'exact_mappings': ['mifa:acknowledgements']} })


class SourceDataset(ConfiguredBaseModel):
    """
    The image dataset the annotated images come from.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    description: str = Field(default=..., description="""What the source images are, in words.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet',
                       'Link',
                       'Study',
                       'SourceDataset',
                       'AnnotationClass']} })
    identifier: Optional[str] = Field(default=None, description="""Accession or DOI, e.g. S-BIAD123 or idr0001.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SourceDataset'], 'slot_uri': 'schema:identifier'} })
    url: Optional[str] = Field(default=None, description="""Web page or download address of the dataset.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Link', 'SourceDataset', 'Model'], 'slot_uri': 'schema:url'} })
    license: Optional[str] = Field(default=None, description="""License of the source images, e.g. CC-BY-4.0.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'SourceDataset'], 'slot_uri': 'schema:license'} })


class Methodology(ConfiguredBaseModel):
    """
    How the annotations were made.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    overview: Optional[str] = Field(default=None, description="""Short summary of the type of annotation and how it was made.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology'], 'exact_mappings': ['mifa:annotation_overview']} })
    annotation_types: list[AnnotationType] = Field(default=..., description="""Kinds of annotation in the set, using MIFA's values.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology'], 'exact_mappings': ['mifa:annotation_type']} })
    mask_kind: Optional[MaskKind] = Field(default=None, description="""For segmentation masks - one value per object (instance) or per class (semantic).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology']} })
    method: Optional[AnnotationMethod] = Field(default=None, description="""Whether annotations were drawn by hand, proposed by software and corrected, or made by software alone.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology', 'Normalization']} })
    method_description: Optional[str] = Field(default=None, description="""How the annotations were created, in words: who, which software, consensus and quality checks.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology'], 'exact_mappings': ['mifa:annotation_method']} })
    criteria: str = Field(default=..., description="""What counts as an object and where its boundary is, in words.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology'], 'exact_mappings': ['mifa:annotation_criteria']} })
    coverage: Optional[Coverage] = Field(default=None, description="""Within an annotated region, whether all objects are annotated, a representative selection, or only some.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology']} })
    coverage_description: Optional[str] = Field(default=None, description="""Which images were annotated and what share of the dataset, in words.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology'], 'exact_mappings': ['mifa:annotation_coverage']} })
    annotators: Optional[list[Person]] = Field(default=None, description="""People who made or reviewed the annotations, if different from the set's authors.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology'], 'exact_mappings': ['mifa:authors']} })
    confidence_level: Optional[str] = Field(default=None, description="""Confidence in the annotations' accuracy, e.g. annotator experience or inter-annotator agreement.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology'],
         'exact_mappings': ['mifa:annotation_confidence_level']} })
    tools: Optional[list[Tool]] = Field(default=None, description="""Software used to make the annotations.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology']} })


class Tool(ConfiguredBaseModel):
    """
    Software used to make the annotations.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'schema:SoftwareApplication',
         'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    name: str = Field(default=..., description="""Name of the software, e.g. micro-sam or cellpose.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet',
                       'Organisation',
                       'Tool',
                       'Model',
                       'AnnotationClass'],
         'slot_uri': 'schema:name'} })
    version: Optional[str] = Field(default=None, description="""Version of the software.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'Tool', 'Model'],
         'slot_uri': 'schema:softwareVersion'} })
    mode: Optional[ToolMode] = Field(default=None, description="""How the software was used.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Tool', 'PlaneSelection']} })
    model: Optional[Model] = Field(default=None, description="""The AI model the software used, if any.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Tool', 'Session']} })
    parameters: Optional[Any] = Field(default=None, description="""Settings the software ran with, as the tool names them.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Tool']} })


class Model(ConfiguredBaseModel):
    """
    An AI model that proposed annotations.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    name: str = Field(default=..., description="""Name of the model, e.g. vit_b_lm.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet',
                       'Organisation',
                       'Tool',
                       'Model',
                       'AnnotationClass']} })
    version: Optional[str] = Field(default=None, description="""Version of the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'Tool', 'Model']} })
    url: Optional[str] = Field(default=None, description="""Where the model can be found, e.g. a BioImage Model Zoo page.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Link', 'SourceDataset', 'Model']} })
    doi: Optional[str] = Field(default=None, description="""DOI of the model.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Publication', 'Model']} })


class AnnotationClass(ConfiguredBaseModel):
    """
    One annotation class.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    name: str = Field(default=..., description="""Name of the class, e.g. nucleus.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet',
                       'Organisation',
                       'Tool',
                       'Model',
                       'AnnotationClass']} })
    description: Optional[str] = Field(default=None, description="""What belongs to the class, in words.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet',
                       'Link',
                       'Study',
                       'SourceDataset',
                       'AnnotationClass']} })
    label_value: Optional[int] = Field(default=None, description="""Pixel value of the class in semantic masks. Not used for instance masks, where each object has its own value.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationClass']} })
    ontology_term: Optional[str] = Field(default=None, description="""IRI of an ontology term for the class, e.g. a CL or GO term.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationClass']} })
    color: Optional[str] = Field(default=None, description="""Display colour as hex, e.g. #E4685D.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationClass']} })

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

    mode: SelectionMode = Field(default=..., description="""How the planes were chosen.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Tool', 'PlaneSelection']} })
    values: Optional[list[int]] = Field(default=None, description="""The indices, for mode 'specific'.""", json_schema_extra = { "linkml_meta": {'domain_of': ['PlaneSelection']} })
    n: Optional[int] = Field(default=None, description="""How many were drawn, for mode 'random'.""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['PlaneSelection']} })


class Sampling(ConfiguredBaseModel):
    """
    Which parts of the images were annotated. Per-annotation detail is in the records.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    label_channel: Optional[int] = Field(default=None, description="""Channel the annotations were drawn on.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Sampling']} })
    input_channels: Optional[list[int]] = Field(default=None, description="""Channels meant as model input; may differ from label_channel (annotate on a nuclear stain, train on brightfield).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Sampling']} })
    timepoints: Optional[PlaneSelection] = Field(default=None, description="""Which timepoints were annotated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Sampling']} })
    z_slices: Optional[PlaneSelection] = Field(default=None, description="""Which z-slices were annotated.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Sampling']} })
    volumetric: Optional[bool] = Field(default=None, description="""True if annotations are 3D volumes rather than 2D planes.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Sampling']} })
    patches: Optional[Patches] = Field(default=None, description="""Patch size and number, if annotations cover patches.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Sampling']} })


class Patches(ConfiguredBaseModel):
    """
    Present if annotations cover patches rather than whole planes.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    width: int = Field(default=..., description="""Patch width in pixels.""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Patches']} })
    height: int = Field(default=..., description="""Patch height in pixels.""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Patches']} })
    per_image: Optional[int] = Field(default=None, description="""Number of patches per image plane.""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Patches']} })
    random: Optional[bool] = Field(default=None, description="""True if patch positions were drawn at random, false if they tile the plane.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Patches']} })


class Split(ConfiguredBaseModel):
    """
    How annotations were divided over training, validation and test.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    strategy: Optional[SplitStrategy] = Field(default=None, description="""How the split was decided.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Split']} })
    unit: Optional[str] = Field(default=None, description="""Level at which data are assigned to a split; all annotations of one unit share a split. 'image' or 'well', or another level named by the tool.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Split']} })
    rationale: Optional[str] = Field(default=None, description="""Why this unit, e.g. 'fields within a well do not overlap'.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Split']} })
    stratify_by: Optional[list[str]] = Field(default=None, description="""Metadata keys the split was balanced on (e.g. cell_line, treatment).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Split']} })
    seed: Optional[int] = Field(default=None, description="""Seed of the random choices, to reproduce the selection with the same tool.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Split']} })


class Normalization(ConfiguredBaseModel):
    """
    Intensity normalisation intended for model input.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    method: NormalizationMethod = Field(default=..., description="""Normalisation method.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Methodology', 'Normalization']} })
    percentile_low: Optional[float] = Field(default=None, description="""Lower percentile, mapped to 0.""", ge=0, le=100, json_schema_extra = { "linkml_meta": {'domain_of': ['Normalization']} })
    percentile_high: Optional[float] = Field(default=None, description="""Upper percentile, mapped to 1.""", ge=0, le=100, json_schema_extra = { "linkml_meta": {'domain_of': ['Normalization']} })
    clip: Optional[bool] = Field(default=None, description="""True if values outside [0, 1] are clipped.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Normalization']} })


class Session(ConfiguredBaseModel):
    """
    One annotation session - who, when, with what, and a note.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'prov:Activity',
         'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    id: int = Field(default=..., description="""Number of the session within the set, from 0.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Grant', 'Session']} })
    kind: SessionKind = Field(default=..., description="""'annotate' creates annotations, 'review' checks or corrects them.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Session']} })
    started: datetime  = Field(default=..., description="""When the session started.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Session'], 'slot_uri': 'prov:startedAtTime'} })
    ended: Optional[datetime ] = Field(default=None, description="""When the session ended; absent while it is open.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Session'], 'slot_uri': 'prov:endedAtTime'} })
    status: Optional[SessionStatus] = Field(default=None, description="""State of the session.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Session', 'AnnotationRecord']} })
    annotator: Optional[str] = Field(default=None, description="""Who annotated - a name, ORCID or pseudonym.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Session']} })
    software: Optional[str] = Field(default=None, description="""Software and version, e.g. 'omero-annotate-ai 0.5.0'.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Session']} })
    model: Optional[str] = Field(default=None, description="""Name of the AI model used in the session, if any.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Tool', 'Session']} })
    n_annotated: Optional[int] = Field(default=None, description="""Number of annotations saved in the session.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Session']} })
    note: Optional[str] = Field(default=None, description="""Free-text note by the annotator.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Session']} })


class ContentCodes(ConfiguredBaseModel):
    """
    How the ISCC codes (ISO 24138) in the records were made. ISCC is a family of codes: the same image gives different codes depending on the code type, which pixels are coded and how they are prepared, so each kind is declared here.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    region: Optional[CodeMethod] = Field(default=None, description="""How input_iscc and mask_iscc were made.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ContentCodes']} })
    image: Optional[CodeMethod] = Field(default=None, description="""How image_iscc (the code of the whole source image) was made.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ContentCodes']} })


class CodeMethod(ConfiguredBaseModel):
    """
    How one kind of ISCC code was computed.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/bioimage-annotation-schema'})

    code_type: IsccCodeType = Field(default=..., description="""The ISCC code type.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CodeMethod']} })
    bits: Optional[int] = Field(default=None, description="""Length of the code's body in bits, e.g. 64 for an Image-Code unit, 128 or 256 (wide) for an ISCC-SUM.""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['CodeMethod']} })
    pixels: str = Field(default=..., description="""Which pixels were coded, e.g. 'the annotated region as saved in input_file' or 'all planes of the source image'.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CodeMethod']} })
    preparation: str = Field(default=..., description="""What was done to the pixels before coding: plane order and byte encoding, projection, resizing, intensity scaling, mask binarisation. 'none' if the stored pixels were coded as they are.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CodeMethod']} })
    specification: Optional[str] = Field(default=None, description="""The specification the preparation follows, if any, e.g. https://ieps.iscc.codes/iep-0018/ (IMAGEWALK) for bioimage ISCC-SUMs.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CodeMethod']} })
    implementation: str = Field(default=..., description="""Software and version that computed the codes, e.g. 'omero-annotate-ai 0.6.0 (iscc-lib 0.7.1)'.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CodeMethod']} })


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
    image_name: Optional[str] = Field(default=None, description="""Name of the source image, for people.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    level: Optional[int] = Field(default=None, description="""Multiscale level the coordinates refer to (0 = full resolution).""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    well: Optional[str] = Field(default=None, description="""Plate well, e.g. B2.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    field: Optional[str] = Field(default=None, description="""Field (well sample) within the well.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    well_metadata: Optional[str] = Field(default=None, description="""Key-value metadata of the well as a JSON object, e.g. {\"cell_line\":\"U2OS\"}.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    channel: Optional[int] = Field(default=None, description="""Channel annotated, from 0.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    timepoint: Optional[int] = Field(default=None, description="""Timepoint annotated, from 0.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    z_slice: Optional[int] = Field(default=None, description="""Z-slice of a 2D annotation.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    z_start: Optional[int] = Field(default=None, description="""First z-slice of a volumetric annotation.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    z_end: Optional[int] = Field(default=None, description="""Last z-slice of a volumetric annotation (inclusive).""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    patch_x: Optional[int] = Field(default=None, description="""Left edge of the patch in pixels, at the given level.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    patch_y: Optional[int] = Field(default=None, description="""Top edge of the patch in pixels, at the given level.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    patch_width: Optional[int] = Field(default=None, description="""Width of the patch in pixels.""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    patch_height: Optional[int] = Field(default=None, description="""Height of the patch in pixels.""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    split: SplitName = Field(default=..., description="""Split the annotation belongs to.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationSet', 'AnnotationRecord']} })
    status: RecordStatus = Field(default=..., description="""State of the annotation.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Session', 'AnnotationRecord']} })
    annotation_type: Optional[AnnotationType] = Field(default=None, description="""Kind of annotation, using MIFA's values.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord'], 'exact_mappings': ['mifa:annotation_type']} })
    created_at: Optional[datetime ] = Field(default=None, description="""When the annotation was created.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord'],
         'exact_mappings': ['mifa:annotation_creation_time'],
         'slot_uri': 'pav:authoredOn'} })
    updated_at: Optional[datetime ] = Field(default=None, description="""When the annotation was last changed.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord'], 'slot_uri': 'pav:lastUpdateOn'} })
    session: Optional[int] = Field(default=None, description="""id of the session (in the set) that last saved this annotation.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    input_file: Optional[str] = Field(default=None, description="""Path of the annotated image region, relative to the set's folder.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    mask_file: Optional[str] = Field(default=None, description="""Path of the mask, relative to the set's folder.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    input_digest: Optional[str] = Field(default=None, description="""Pixel SHA-256 of the annotated image region.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    mask_digest: Optional[str] = Field(default=None, description="""Pixel SHA-256 of the mask.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    input_iscc: Optional[str] = Field(default=None, description="""ISCC code of the annotated image region, made as declared in the set's content_codes.region.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    mask_iscc: Optional[str] = Field(default=None, description="""ISCC code of the mask, made as declared in the set's content_codes.region.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    image_iscc: Optional[str] = Field(default=None, description="""ISCC code of the whole source image, made as declared in the set's content_codes.image - for example the ISCC-SUM (IMAGEWALK) that omero-iscc stores on OMERO images. Identifies the source by content, whatever its URI.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })
    transformations: Optional[str] = Field(default=None, description="""Transformations needed to align the annotation with the source image, e.g. a rotation or crop.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord'], 'exact_mappings': ['mifa:transformations']} })
    external_ids: Optional[str] = Field(default=None, description="""Identifiers of copies in other systems as a JSON object, e.g. {\"omero_roi\":\"123\",\"omero_label_image\":\"456\"}.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotationRecord']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
AnnotationSet.model_rebuild()
Person.model_rebuild()
Organisation.model_rebuild()
Link.model_rebuild()
Publication.model_rebuild()
Grant.model_rebuild()
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
ContentCodes.model_rebuild()
CodeMethod.model_rebuild()
AnnotationRecord.model_rebuild()
