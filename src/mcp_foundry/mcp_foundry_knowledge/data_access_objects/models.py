from typing import List, Optional, AnyStr, Any

from azure.search.documents.indexes._generated.models import FieldMapping
from pydantic import BaseModel, ConfigDict
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchSuggester

OperationResult = dict[str, Any]

from pydantic import BaseModel, Extra

class SearchDocument(BaseModel):
    id: str
    model_config = ConfigDict(extra="allow")

class SearchFieldSchema(BaseModel):
    name: str
    type: str
    key: Optional[bool] = False
    searchable: Optional[bool] = False
    filterable: Optional[bool] = False
    sortable: Optional[bool] = False
    facetable: Optional[bool] = False
    retrievable: Optional[bool] = True
    analyzer: Optional[str] = None
    search_analyzer: Optional[str] = None
    index_analyzer: Optional[str] = None
    synonym_maps: Optional[List[str]] = None


class SuggesterSchema(BaseModel):
    name: str
    source_fields: List[str]


class CorsOptionsSchema(BaseModel):
    allowed_origins: List[str]
    max_age_in_seconds: Optional[int] = 300


class ScoringProfileSchema(BaseModel):
    name: str
    # @TODO Add specific scoring profile fields as needed


class SearchIndexSchema(BaseModel):
    name: str
    description: Optional[str] = None
    fields: List[SearchFieldSchema]
    suggesters: Optional[List[SuggesterSchema]] = None
    scoring_profiles: Optional[List[ScoringProfileSchema]] = None
    default_scoring_profile: Optional[str] = None
    cors_options: Optional[CorsOptionsSchema] = None
    semantic_settings: Optional[dict] = None  # @TODO expand this to a model if needed
    encryption_key: Optional[dict] = None  # @TODO expand this to a model if needed


class FieldMappingModel(BaseModel):
    source_field_name: str
    target_field_name: str
    mapping_function: str | None = None

def convert_pydantic_model_to_search_index(schema: SearchIndexSchema) -> SearchIndex:
    fields = [SimpleField(**field.model_dump()) for field in schema.fields]
    suggesters = [SearchSuggester(name=s.name, source_fields=s.source_fields) for s in (schema.suggesters or [])]

    return SearchIndex(
        name=schema.name,
        description=schema.description,
        fields=fields,
        suggesters=suggesters or None,
        scoring_profiles=schema.scoring_profiles,
        default_scoring_profile=schema.default_scoring_profile,
        cors_options=schema.cors_options,
        semantic_settings=schema.semantic_settings,
        encryption_key=schema.encryption_key
    )


def convert_to_field_mappings(models: List[FieldMappingModel]) -> List[FieldMapping]:
    """
    Converts a list of FieldMappingModel instances to Azure FieldMapping objects.

    Args:
        models (List[FieldMappingModel]): List of Pydantic models representing field mappings.

    Returns:
        List[FieldMapping]: List of Azure SDK FieldMapping instances.
    """
    return [
        FieldMapping(
            source_field_name=model.source_field_name,
            target_field_name=model.target_field_name,
            mapping_function=model.mapping_function
        )
        for model in models
    ]
