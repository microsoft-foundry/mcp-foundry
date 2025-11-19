import pytest

from mcp_foundry.mcp_foundry_knowledge.data_access_objects.dao import SearchIndexDao
from mcp_foundry.mcp_foundry_knowledge.data_access_objects.models import (
    SearchIndexSchema,
    SearchFieldSchema,
    convert_pydantic_model_to_search_index,
)


def test_retrieve_indexes_with_descriptions(monkeypatch):
    class FakeIndex:
        def __init__(self, name: str, description: str | None):
            self.name = name
            self.description = description

    class FakeClient:
        def list_indexes(self):
            return [
                FakeIndex("idx1", "Description 1"),
                FakeIndex("idx2", None),
            ]

    def fake_init(self):
        self.client = FakeClient()

    monkeypatch.setattr(SearchIndexDao, "__init__", fake_init, raising=False)

    dao = SearchIndexDao()
    results = dao.retrieve_indexes_with_descriptions()

    assert results == [
        {"name": "idx1", "description": "Description 1"},
        {"name": "idx2", "description": None},
    ]


def test_convert_pydantic_model_to_search_index_description_passthrough():
    schema = SearchIndexSchema(
        name="test-index",
        description="My test index",
        fields=[
            SearchFieldSchema(name="id", type="Edm.String", key=True),
        ],
    )

    search_index = convert_pydantic_model_to_search_index(schema)

    assert getattr(search_index, "description", None) == "My test index"
    assert search_index.name == "test-index"
    assert hasattr(search_index, "fields") and len(search_index.fields) == 1

