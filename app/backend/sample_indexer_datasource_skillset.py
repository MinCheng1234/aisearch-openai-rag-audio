"""
FILE: sample_indexer_datasource_skillset.py
DESCRIPTION:
    This sample demonstrates use an indexer, datasource and skillset together.

    Indexer is used to efficiently write data to an index using a datasource.
    So we first identify a supported data source - we use azure storage blobs
    in this example. Then we create an index which is compatible with the datasource.
    Further, we create an azure cognitive search datasource which we require to finally
    create an indexer.

    Additionally, we will also use skillsets to provide some AI enhancements in our indexers.

    Once we create the indexer, we run the indexer and perform some basic operations like getting
    the indexer status.

    The datasource used in this sample is stored as metadata for empty blobs in "searchcontainer".
    The json file can be found in samples/files folder named hotel_small.json has the metdata of
    each blob.
USAGE:
    python sample_indexer_datasource_skillset.py

    Set the environment variables with your own values before running the sample:
    1) AZURE_SEARCH_SERVICE_ENDPOINT - the endpoint of your Azure Cognitive Search service
    2) AZURE_SEARCH_API_KEY - your search API key
    3) AZURE_STORAGE_CONNECTION_STRING - The connection string for the storage blob account that is
    being used to create the datasource.
"""

import os
import datetime


from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.models import (
    SearchIndexerDataContainer,
    SearchIndex,
    SearchIndexer,
    SimpleField,
    SearchField,
    SearchFieldDataType,
    EntityRecognitionSkill,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    SearchIndexerSkillset,
    CorsOptions,
    IndexingSchedule,
    SearchableField,
    IndexingParameters,
    SearchIndexerDataSourceConnection,
    IndexingParametersConfiguration,
        AzureOpenAIEmbeddingSkill,
    AzureOpenAIParameters,
    AzureOpenAIVectorizer,
    FieldMapping,
    HnswAlgorithmConfiguration,
    HnswParameters,
    IndexProjectionMode,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchIndexer,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    SearchIndexerDataSourceType,
    SearchIndexerIndexProjections,
    SearchIndexerIndexProjectionSelector,
    SearchIndexerIndexProjectionsParameters,
    SearchIndexerSkillset,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    SplitSkill,
    VectorSearch,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)
from azure.search.documents.indexes import SearchIndexerClient, SearchIndexClient
from dotenv import load_dotenv

load_dotenv()

service_endpoint = os.environ["AZURE_SEARCH_SERVICE_ENDPOINT"]
key = os.environ["AZURE_SEARCH_API_KEY"]
connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]

AZURE_OPENAI_EMBEDDING_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"]
AZURE_OPENAI_EMBEDDING_MODEL = os.environ["AZURE_OPENAI_EMBEDDING_MODEL"]
AZURE_OPENAI_EMBEDDING_CREDENTIAL =os.environ["AZURE_OPENAI_EMBEDDING_CREDENTIAL"]

def _create_index():
    name = "hotel-index"

    # Here we create an index with listed fields.
    fields=[
            SearchableField(name="chunk_id", key=True, analyzer_name="keyword", sortable=True),
            SimpleField(name="parent_id", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="title"),
            SearchableField(name="chunk"),
            SearchField(
                name="text_vector", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=1536,
                vector_search_profile_name="vp",
                stored=True,
                hidden=False)
        ],
    cors_options = CorsOptions(allowed_origins=["*"], max_age_in_seconds=60)

    # pass in the name, fields and cors options and create the index
    index = SearchIndex(name=name, fields=fields, cors_options=cors_options)
    index_client = SearchIndexClient(service_endpoint, AzureKeyCredential(key))
    result = index_client.create_index(index)
    return result


def _create_datasource():
    # Here we create a datasource. As mentioned in the description we have stored it in
    # "searchcontainer"
    ds_client = SearchIndexerClient(service_endpoint, AzureKeyCredential(key))
    container = SearchIndexerDataContainer(name="documentation")
    data_source_connection = SearchIndexerDataSourceConnection(
        name="openairagaudio", type="azureblob", connection_string=connection_string, container=container
    )
    data_source = ds_client.create_data_source_connection(data_source_connection)
    return data_source


def _create_skillset():
    client = SearchIndexerClient(service_endpoint, AzureKeyCredential(key))
    skillset=SearchIndexerSkillset(
        name="testtskillset",
        skills=[
            SplitSkill(
                text_split_mode="pages",
                context="/document",
                maximum_page_length=2000,
                page_overlap_length=500,
                inputs=[InputFieldMappingEntry(name="text", source="/document/content")],
                outputs=[OutputFieldMappingEntry(name="textItems", target_name="pages")]),
            AzureOpenAIEmbeddingSkill(
                context="/document/pages/*",
                resource_uri=AZURE_OPENAI_EMBEDDING_ENDPOINT,
                api_key=AZURE_OPENAI_EMBEDDING_CREDENTIAL,
                deployment_id=AZURE_OPENAI_EMBEDDING_ENDPOINT,
                model_name=AZURE_OPENAI_EMBEDDING_MODEL,
                dimensions=1536,
                inputs=[InputFieldMappingEntry(name="text", source="/document/pages/*")],
                outputs=[OutputFieldMappingEntry(name="embedding", target_name="text_vector")])
        ],
        index_projections=SearchIndexerIndexProjections(
            selectors=[
                SearchIndexerIndexProjectionSelector(
                    target_index_name="gptkbindex",
                    parent_key_field_name="parent_id",
                    source_context="/document/pages/*",
                    mappings=[
                        InputFieldMappingEntry(name="chunk", source="/document/pages/*"),
                        InputFieldMappingEntry(name="text_vector", source="/document/pages/*/text_vector"),
                        InputFieldMappingEntry(name="title", source="/document/metadata_storage_name")
                    ]
                )
            ],
            parameters=SearchIndexerIndexProjectionsParameters(
                projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS
            )
        ))
    result = client.create_skillset(skillset)
    return result


def sample_indexer_workflow():
    # Now that we have a datasource and an index, we can create an indexer.

    skillset_name = _create_skillset().name
    print("Skillset is created")

    ds_name = _create_datasource().name
    print("Data source is created")

    #ind_name = _create_index().name
    #print("Index is created")

    # we pass the data source, skillsets and targeted index to build an indexer
    #configuration = IndexingParametersConfiguration(parsing_mode="jsonArray", query_timeout=None)
    #parameters = IndexingParameters(configuration=configuration)
    indexer = SearchIndexer(
        name="hotel-data-indexer",
        data_source_name=ds_name,
        target_index_name="gptkbindex",
        skillset_name=skillset_name,
        #parameters=parameters,
        field_mappings=[FieldMapping(source_field_name="metadata_storage_name", target_field_name="title")]
    )

    indexer_client = SearchIndexerClient(service_endpoint, AzureKeyCredential(key))
    indexer_client.create_indexer(indexer)  # create the indexer

    # to get an indexer
    result = indexer_client.get_indexer("hotel-data-indexer")
    print(result)

    # To run an indexer, we can use run_indexer()
    indexer_client.run_indexer(result.name)

    # Using create or update to schedule an indexer

    #schedule = IndexingSchedule(interval=datetime.timedelta(hours=24))
    #result.schedule = schedule
    #updated_indexer = indexer_client.create_or_update_indexer(result)

    #print(updated_indexer)

    # get the status of an indexer
    #indexer_client.get_indexer_status(updated_indexer.name)


if __name__ == "__main__":
    sample_indexer_workflow()