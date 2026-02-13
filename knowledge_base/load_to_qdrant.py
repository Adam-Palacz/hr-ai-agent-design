"""
Script to load documents from knowledge_base into Qdrant.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import services
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.qdrant_service import QdrantRAG

load_dotenv()


def load_documents_from_files(directory: str = "knowledge_base") -> list:
    """Load all .txt files from the directory and return as a list of documents."""
    documents = []
    metadatas = []
    ids = []

    knowledge_path = Path(directory)
    if not knowledge_path.exists():
        print(f"❌ Directory {directory} does not exist!")
        return documents, metadatas, ids

    txt_files = list(knowledge_path.glob("*.txt"))
    if not txt_files:
        print(f"⚠️ No .txt files in directory {directory}")
        return documents, metadatas, ids

    print(f"📚 Found {len(txt_files)} files in {directory}:")

    for file_path in txt_files:
        print(f"   - {file_path.name}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    documents.append(content)
                    # Metadata contains file name and document type
                    filename = file_path.stem
                    metadata = {
                        "source": filename,
                        "file": file_path.name,
                        "type": _classify_document_type(filename),
                    }
                    metadatas.append(metadata)
                    ids.append(f"kb_{filename}")
        except Exception as e:
            print(f"   ⚠️ Error loading {file_path.name}: {e}")

    return documents, metadatas, ids


def _classify_document_type(filename: str) -> str:
    """Classify document type based on file name."""
    filename_lower = filename.lower()
    if "rodo" in filename_lower or "ai_act" in filename_lower or "ai act" in filename_lower:
        return "regulacje_prawne"
    elif "polityka" in filename_lower or "rekrutacja" in filename_lower:
        return "polityka_rekrutacji"
    elif "firma" in filename_lower or "informacje" in filename_lower:
        return "informacje_o_firmie"
    else:
        return "inne"


def main():
    """Main function – loads documents into Qdrant."""
    print("=" * 60)
    print("LOADING KNOWLEDGE BASE TO QDRANT")
    print("=" * 60)

    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

    if not azure_api_key:
        raise RuntimeError("AZURE_OPENAI_API_KEY is not set in .env")

    # Load documents
    documents, metadatas, ids = load_documents_from_files("knowledge_base")

    if not documents:
        print("❌ No documents to load!")
        return

    print(f"\n📝 Prepared {len(documents)} documents for loading")

    # Initialize Qdrant
    # Check whether to use Qdrant server or local database
    qdrant_host = os.getenv("QDRANT_HOST")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333")) if os.getenv("QDRANT_PORT") else None

    try:
        if qdrant_host:
            # Use Qdrant server
            print(f"📤 Loading to Qdrant server ({qdrant_host}:{qdrant_port})...")
            db = QdrantRAG(
                collection_name="recruitment_knowledge_base",
                use_azure_openai=True,
                azure_endpoint=azure_endpoint,
                azure_api_key=azure_api_key,
                azure_deployment=azure_deployment,
                azure_api_version=azure_api_version,
                qdrant_host=qdrant_host,
                qdrant_port=qdrant_port,
            )
        else:
            # Use local database (default)
            print("📤 Loading to local Qdrant database...")
            db = QdrantRAG(
                collection_name="recruitment_knowledge_base",
                use_azure_openai=True,
                azure_endpoint=azure_endpoint,
                azure_api_key=azure_api_key,
                azure_deployment=azure_deployment,
                azure_api_version=azure_api_version,
                qdrant_path="./qdrant_db",
            )
    except (RuntimeError, Exception) as e:
        error_str = str(e)
        if (
            "already accessed" in error_str
            or "AlreadyLocked" in error_str
            or "already locked" in error_str.lower()
        ):
            print("\n" + "=" * 60)
            print("❌ ERROR: Qdrant database is already in use!")
            print("=" * 60)
            print("\n📌 Solution:")
            print("   1. Close the application (app.py) if it is running")
            print("   2. Check for other processes using Qdrant")
            print("   3. Try again in a moment")
            print("\n💡 Alternatively:")
            print("   - Use Qdrant server for concurrent access")
            print("   - Or wait until the application releases the lock")
            print("=" * 60)
            return
        else:
            print(f"\n❌ Unexpected error during Qdrant initialization: {error_str}")
            raise

    # Load documents
    print("\n📤 Loading documents into Qdrant...")
    db.add_documents(documents, ids=ids, metadatas=metadatas)

    print(f"\n✅ Loaded {len(documents)} documents into collection 'recruitment_knowledge_base'")
    print(f"📊 Total documents in collection: {db.count()}")

    # Search test
    print("\n" + "=" * 60)
    print("SEARCH TEST")
    print("=" * 60)

    test_queries = ["Jakie są etapy rekrutacji?", "Co to jest RODO?", "Jakie są wartości firmy?"]

    for query in test_queries:
        print(f"\n❓ Pytanie: {query}")
        results = db.search(query, n_results=2)
        if results:
            print(f"   Found {len(results)} results:")
            for i, r in enumerate(results, 1):
                print(f"   {i}. Source: {r['metadata'].get('source', 'N/A')}")
                print(f"      Excerpt: {r['document'][:100]}...")
        else:
            print("   No results")

    print("\n" + "=" * 60)
    print("✅ Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
