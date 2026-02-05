
import os
import sys
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

def debug_qdrant(knowledge_id="01KE8XQPYSZSGMCK9NPX8CH2PA"):
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    if not qdrant_url:
        print("Error: QDRANT_URL not set")
        return

    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    collection_name = "radikari_knowledge"

    print(f"Searching for Knowledge ID: {knowledge_id} in {collection_name}")

    try:
        # Filter by knowledge_id in metadata
        scroll_result = client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="knowledge_id",
                        match=models.MatchValue(value=knowledge_id)
                    )
                ]
            ),
            limit=5,
            with_payload=True,
            with_vectors=False
        )
        
        points, _ = scroll_result
        
        if not points:
            print("❌ No points found for this Knowledge ID.")
        else:
            print(f"✅ Found {len(points)} points (showing first 1):")
            for point in points[:1]:
                print(f"ID: {point.id}")
                print("Payload:")
                import json
                print(json.dumps(point.payload, indent=2))

    except Exception as e:
        print(f"Error querying Qdrant: {e}")

if __name__ == "__main__":
    debug_qdrant()
