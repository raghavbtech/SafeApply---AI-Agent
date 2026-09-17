"""
SafeApply - Azure AI Search Indexer
Builds and uploads the recruitment scam patterns index into Azure AI Search.
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT", "")
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "")
SEARCH_INDEX_NAME = os.getenv("SEARCH_INDEX_NAME", "safeapply-scam-patterns")
RAG_TOP_K = int(os.getenv("SAFEAPPLY_TOP_K", "5"))
DATASET_PATH = os.path.join(os.path.dirname(__file__), "scam_patterns.json")


def load_patterns_dataset():
    """Load curated scam patterns from local JSON."""
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def is_azure_configured():
    """Check whether real Azure AI Search credentials are configured."""
    return bool(
        SEARCH_ENDPOINT
        and SEARCH_API_KEY
        and "your-search-service" not in SEARCH_ENDPOINT
        and "your_search_admin_api_key" not in SEARCH_API_KEY
    )


def create_and_populate_index():
    """Create the Azure AI Search index schema and upload all pattern documents."""
    patterns = load_patterns_dataset()
    print(f"Loaded {len(patterns)} scam patterns from {DATASET_PATH}")

    if not is_azure_configured():
        print("\n[Azure AI Search Notice]")
        print("Live Azure AI Search credentials not found in .env.")
        print(f"Dataset validated successfully with {len(patterns)} patterns.")
        print("To deploy to live Azure AI Search:")
        print("1. Create Azure AI Search resource in Portal (Free F0 Tier).")
        print("2. Set SEARCH_ENDPOINT and SEARCH_API_KEY in .env.")
        print("3. Re-run this script.\n")
        return False

    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        SearchIndex,
        SimpleField,
        SearchableField,
        SearchFieldDataType,
    )
    from azure.search.documents import SearchClient

    credential = AzureKeyCredential(SEARCH_API_KEY)
    index_client = SearchIndexClient(
        endpoint=SEARCH_ENDPOINT,
        credential=credential,
    )

    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
        ),
        SearchableField(
            name="category",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SearchableField(
            name="pattern",
            type=SearchFieldDataType.String,
        ),
        SearchableField(
            name="example_text",
            type=SearchFieldDataType.String,
        ),
        SimpleField(
            name="risk_weight",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
    ]

    index = SearchIndex(
        name=SEARCH_INDEX_NAME,
        fields=fields,
    )

    print(
        f"Creating or updating Azure AI Search index: "
        f"{SEARCH_INDEX_NAME}..."
    )
    index_client.create_or_update_index(index)
    print("Index schema successfully created/updated!")

    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX_NAME,
        credential=credential,
    )

    print(
        f"Uploading {len(patterns)} documents to Azure AI Search..."
    )
    result = search_client.upload_documents(documents=patterns)

    succeeded = sum(
        1
        for item in result
        if item.succeeded
    )

    print(
        f"Successfully indexed {succeeded}/{len(patterns)} "
        "documents into Azure AI Search."
    )

    return True


def test_search_query(
    query_text: str = "refundable registration fee UPI",
):
    """
    Test the Search index using the same top-k configuration as the RAG layer.

    Azure Search explicitly searches the category, pattern, and example_text
    fields. @search.score is reported as a retrieval relevance score, not a
    confidence probability.
    """
    patterns = load_patterns_dataset()

    if not is_azure_configured():
        print(
            f"\n[Running Local Simulation Search for: "
            f"'{query_text}']"
        )

        query_words = set(query_text.lower().split())
        scored = []

        for pattern in patterns:
            text = (
                f"{pattern['category']} "
                f"{pattern['pattern']} "
                f"{pattern['example_text']}"
            ).lower()

            score = sum(
                1
                for word in query_words
                if word in text
            )

            if score > 0:
                scored.append((score, pattern))

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        top = scored[:RAG_TOP_K]

        for score, match in top:
            print(
                f"- [Search Score: {score}] "
                f"Category: {match['category']} | "
                f"Pattern: {match['pattern']}"
            )

        return [
            match
            for _, match in top
        ]

    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient

    credential = AzureKeyCredential(SEARCH_API_KEY)

    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX_NAME,
        credential=credential,
    )

    print(
        f"\n[Querying Live Azure AI Search for: "
        f"'{query_text}']"
    )

    results = search_client.search(
        search_text=query_text,
        search_fields=[
            "pattern",
            "example_text",
            "category",
        ],
        select=[
            "id",
            "category",
            "pattern",
            "example_text",
            "risk_weight",
        ],
        top=RAG_TOP_K,
    )

    matches = []

    for result in results:
        matches.append(dict(result))

        print(
            f"- [Search Score: "
            f"{result.get('@search.score', 0):.2f}] "
            f"Category: {result['category']} | "
            f"Pattern: {result['pattern']}"
        )

    return matches


if __name__ == "__main__":
    create_and_populate_index()
    test_search_query(
        "pay INR 999 registration fee"
    )
