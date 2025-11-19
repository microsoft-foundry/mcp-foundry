
from pathlib import Path
from typing import Optional, List, cast
import logging
import sys

import httpx
from azure.search.documents.indexes._generated.models import FieldMapping
from mcp_foundry.mcp_server import mcp

from .data_access_objects import SearchIndexDao, SearchClientDao, SearchIndexerDao, SearchIndexSchema, \
    convert_pydantic_model_to_search_index, FieldMappingModel, convert_to_field_mappings, \
    OperationResult, \
    SearchDocument

logger = logging.getLogger(__name__)

@mcp.tool(description="Reads the content of a local file and returns it as a string")
def fk_fetch_local_file_contents(file_path: str, encoding: str = "utf-8") -> str:
    """
    Reads the content of a local file and returns it as a string.

    Args:
        file_path (str): The path to the local file.
        encoding (str): The character encoding to use (default is 'utf-8').

    Returns:
        str: The contents of the file as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If the file cannot be read.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"No such file: '{file_path}'")

    return path.read_text(encoding=encoding)

@mcp.tool(description="Fetches the contents of the given HTTP URL")
async def fk_fetch_url_contents(url: str) -> str:
    """
    Fetches the contents of the given HTTP URL

    Args:
        url (str): The URL to fetch content from.

    Returns:
        str: The content retrieved from the URL.

    Raises:
        httpx.RequestError: If the request fails due to a network problem.
        httpx.HTTPStatusError: If the response status code is not 2xx.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text

@mcp.tool(description="Retrieves the names of all indexes ")
async def list_index_names() -> list[str]:
    """
    Retrieves the names of all indexes

    Returns:
        list[str]: A list containing the names of all available search indexes.
    """
    dao = SearchIndexDao()
    return dao.retrieve_index_names()

@mcp.tool(description="Retrieves the names and descriptions of all indexes")
async def list_indexes_with_descriptions() -> list[dict[str, str | None]]:
    """
    Retrieves the names and descriptions of all indexes.

    Returns:
        list[dict[str, str | None]]: A list of dictionaries, each containing 'name' and 'description' 
        keys for each search index. Description may be None if not set.
    """
    dao = SearchIndexDao()
    return dao.retrieve_indexes_with_descriptions()

@mcp.tool(description="Retrieves the schemas for all indexes ")
async def list_index_schemas() -> list[OperationResult]:
    """
    Retrieves the schemas for all indexes.

    Returns:
        list[OperationResult]: A list of dictionaries, each representing the schema of an index.
    """
    dao = SearchIndexDao()
    return cast(list[OperationResult], dao.retrieve_index_schemas())

@mcp.tool(description="Retrieves the schema for a specific index")
async def retrieve_index_schema(index_name: str) -> OperationResult:
    """
    Retrieves the schema for a specific index

    Args:
        index_name (str): The name of the index for which the schema should be retrieved.

    Returns:
        OperationResult: A dictionary representing the schema of the specified index.
    """
    dao = SearchIndexDao()
    return cast(OperationResult, dao.retrieve_index_schema(index_name))

@mcp.tool(description="Creates an AI Search index")
async def create_index(index_definition: SearchIndexSchema) -> OperationResult:
    """
    Creates a new index.

    Args:
        index_definition (SearchIndexSchema): The full definition of the index to be created.

    Returns:
        OperationResult: The serialized response of the created index.
    """
    dao = SearchIndexDao()
    compatible_index_definition = convert_pydantic_model_to_search_index(index_definition)
    return cast(OperationResult, dao.create_index(compatible_index_definition))

@mcp.tool(description="Updates an AI Search index with a new index definition")
async def modify_index(index_name: str, updated_index_definition: SearchIndexSchema) -> OperationResult:
    """
    Updates an AI Search index with the modified index definition

    Args:
        index_name (str): The name of the index to be updated
        updated_index_definition (SearchIndexSchema): The full updated definition of the index.

    Returns:
        OperationResult: The serialized response of the modified index.
    """
    dao = SearchIndexDao()
    compatible_index_definition = convert_pydantic_model_to_search_index(updated_index_definition)
    return cast(OperationResult, dao.modify_index(index_name, compatible_index_definition))

@mcp.tool(description="Deletes the specified index")
async def delete_index(index_name: str) -> str:
    """
    Deletes an existing index .

    Args:
        index_name (str): The name of the index to be deleted.

    Returns:
        str: The result of the operation
    """
    dao = SearchIndexDao()
    dao.delete_index(index_name)
    return "Successful"

@mcp.tool(description="Return the total number of documents in the index")
def get_document_count(index_name: str) -> int:
    """
    Returns the total number of documents in the index

    Args:
        index_name (str): the name of the index

    Returns:
        int: The total number of documents in the index
    """
    search_client_dao = SearchClientDao(index_name)
    result = search_client_dao.get_document_count()
    return result

@mcp.tool(description="Adds a document to the index")
def add_document(index_name: str, document: SearchDocument) -> OperationResult:
    """
    Add a document to the specified Azure AI Search index

    Args:
        index_name (str): the name of the index we are adding the document to
        document (SearchDocument): The contents of the document to be added to the index.

    Returns:
        OperationResult: The serialized result of the add operation for the single document.
    """
    search_client_dao = SearchClientDao(index_name)
    result = search_client_dao.add_document(document.model_dump())
    return cast(OperationResult, result)

@mcp.tool(description="Removes a document from the index")
async def delete_document(index_name: str, key_field_name: str, key_value: str) -> OperationResult:
    """
    Removes a document from the index.

    Args:
        index_name (str): the name of the index from which to delete the document
        key_field_name (str): The name of the key field in the index we are removing the document from
        key_value (str): The value of the key field for the document we are deleting

    Returns:
        OperationResult: A list of serialized results for each document deletion operation.
    """
    search_client_dao = SearchClientDao(index_name)
    return cast(OperationResult, search_client_dao.delete_document(key_field_name, key_value))

@mcp.tool(description="Search a specific index for documents in that index")
async def query_index(
        index_name: str,
        search_text: Optional[str] = None,
        *,
        query_filter: Optional[str] = None,
        order_by: Optional[List[str]] = None,
        select: Optional[List[str]] = None,
        skip: Optional[int] = None,
        top: Optional[int] = None,
        include_total_count: Optional[bool] = None,
) -> list[dict]:
    """Searches the Azure search index for documents matching the query criteria

        :param str index_name: The name of the index to query. This parameter is required
        :param str search_text: A full-text search query expression; Use "*" or omit this parameter to
            match all documents.
        :param str query_filter: The OData $filter expression to apply to the search query.
        :param list[str] order_by: The list of OData $orderby expressions by which to sort the results. Each
            expression can be either a field name or a call to either the geo.distance() or the
            search.score() functions. Each expression can be followed by asc to indicate ascending, and
            desc to indicate descending. The default is ascending order. Ties will be broken by the match
            scores of documents. If no OrderBy is specified, the default sort order is descending by
            document match score. There can be at most 32 $orderby clauses.
        :param list[str] select: The list of fields to retrieve. If unspecified, all fields marked as retrievable
            in the schema are included.
        :param int skip: The number of search results to skip. This value cannot be greater than 100,000.
            If you need to scan documents in sequence, but cannot use $skip due to this limitation,
            consider using $orderby on a totally-ordered key and $filter with a range query instead.
        :param int top: The number of search results to retrieve. This can be used in conjunction with
            $skip to implement client-side paging of search results. If results are truncated due to
            server-side paging, the response will include a continuation token that can be used to issue
            another Search request for the next page of results.
        :param bool include_total_count: A value that specifies whether to fetch the total count of
            results. Default is false. Setting this value to true may have a performance impact. Note that
            the count returned is an approximation.
        :rtype: list[dict]
        """
    search_client_dao = SearchClientDao(index_name)

    search_results: list[dict] = search_client_dao.query_index(
        search_text=search_text,
        include_total_count=include_total_count,
        query_filter=query_filter,
        order_by=order_by,
        select=select,
        skip=skip,
        top=top
    )

    return search_results

@mcp.tool(
    description="Retrieves the list of all the names of the indexers")
async def list_indexers() -> list[str]:
    """
    Retrieves the list of all indexers registered .

    Returns:
        list[str]: A list of indexer names.
    """
    search_indexer_dao = SearchIndexerDao()
    return search_indexer_dao.list_indexers()

@mcp.tool(description="Retrieves the details of a specific indexer by name.")
async def get_indexer(name: str) -> OperationResult:
    """
    Retrieves the details of a specific indexer by name.

    Args:
        name (str): The name of the indexer to retrieve.

    Returns:
        OperationResult: A dictionary containing the indexer details.
    """
    search_indexer_dao = SearchIndexerDao()
    return cast(OperationResult, search_indexer_dao.get_indexer(name))

@mcp.tool(description="Creates a new indexer")
async def create_indexer(
        name: str,
        data_source_name: str,
        target_index_name: str,
        description: str,
        field_mappings: list[FieldMappingModel],
        output_field_mappings: list[FieldMappingModel],
        skill_set_name: str = None
) -> OperationResult:
    """
    Creates a new indexer.

    Args:
        name (str): The name of the indexer to be created.
        data_source_name (str): The name of the indexer to be created.
        target_index_name (str): The name of the indexer to be created.
        description (str): The name of the indexer to be created.
        field_mappings (list[FieldMapping]): The field mappings to be created.
        output_field_mappings (list[FieldMapping]): The field mappings in the index .
        skill_set_name (str): The name of the indexer to be created.

    Returns:
        OperationResult: A dictionary representing the created indexer.
    """
    search_indexer_dao = SearchIndexerDao()

    compat_field_mappings = convert_to_field_mappings(field_mappings)
    compat_output_field_mappings = convert_to_field_mappings(output_field_mappings)

    result = search_indexer_dao.create_indexer(
        name=name,
        data_source_name=data_source_name,
        target_index_name=target_index_name,
        description=description,
        field_mappings=compat_field_mappings,
        output_field_mappings=compat_output_field_mappings,
        skill_set_name=skill_set_name
    )

    return cast(OperationResult, result)

@mcp.tool(description="Deletes the indexer")
async def delete_indexer(name: str) -> str:
    """
    Deletes an indexer by name.

    Args:
        name (str): The name of the indexer to delete.

    Returns:
        None
    """
    search_indexer_dao = SearchIndexerDao()
    search_indexer_dao.delete_indexer(name)
    return "Successful"

@mcp.tool(description="Retrieves the list of all data source names")
async def list_data_sources() -> list[str]:
    """
    Retrieves the list of all data source names

    Returns:
        list[str]: A list of data source names.
    """
    search_indexer_dao = SearchIndexerDao()
    return search_indexer_dao.list_data_sources()

@mcp.tool(description="Retrieves the details of a specific data source by name")
async def get_data_source(name: str) -> OperationResult:
    """
    Retrieves the details of a specific data source by name.

    Args:
        name (str): The name of the data source to retrieve.

    Returns:
        OperationResult: A dictionary containing the data source details.
    """
    search_indexer_dao = SearchIndexerDao()
    return cast(OperationResult, search_indexer_dao.get_data_source(name))

@mcp.tool(description="Retrieves the list of the names of all skill sets")
async def list_skill_sets() -> list[str]:
    """
    Retrieves the list of all skill sets

    Returns:
        list[str]: A list of skill set names.
    """
    search_indexer_dao = SearchIndexerDao()
    return search_indexer_dao.list_skill_sets()

@mcp.tool(description="Retrieves the details of a specific skill set by name")
async def get_skill_set(skill_set_name: str) -> OperationResult:
    """
    Retrieves the details of a specific skill set by name.

    Args:
        skill_set_name (str): The name of the skill set to retrieve.

    Returns:
        OperationResult: A dictionary containing the skill set details.
    """
    search_indexer_dao = SearchIndexerDao()
    return cast(OperationResult, search_indexer_dao.get_skill_set(skill_set_name))
