"""
Skrypt do załadowania dokumentów z knowledge_base do Qdrant.
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
    """Wczytaj wszystkie pliki .txt z katalogu i zwróć jako listę dokumentów."""
    documents = []
    metadatas = []
    ids = []
    
    knowledge_path = Path(directory)
    if not knowledge_path.exists():
        print(f"❌ Katalog {directory} nie istnieje!")
        return documents, metadatas, ids
    
    txt_files = list(knowledge_path.glob("*.txt"))
    if not txt_files:
        print(f"⚠️ Brak plików .txt w katalogu {directory}")
        return documents, metadatas, ids
    
    print(f"📚 Znaleziono {len(txt_files)} plików w {directory}:")
    
    for file_path in txt_files:
        print(f"   - {file_path.name}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    documents.append(content)
                    # Metadata zawiera nazwę pliku i typ dokumentu
                    filename = file_path.stem
                    metadata = {
                        "source": filename,
                        "file": file_path.name,
                        "type": _classify_document_type(filename)
                    }
                    metadatas.append(metadata)
                    ids.append(f"kb_{filename}")
        except Exception as e:
            print(f"   ⚠️ Błąd przy wczytywaniu {file_path.name}: {e}")
    
    return documents, metadatas, ids


def _classify_document_type(filename: str) -> str:
    """Klasyfikuj typ dokumentu na podstawie nazwy pliku."""
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
    """Główna funkcja - ładuje dokumenty do Qdrant."""
    print("=" * 60)
    print("ŁADOWANIE KNOWLEDGE BASE DO QDRANT")
    print("=" * 60)
    
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    
    if not azure_api_key:
        raise RuntimeError("AZURE_OPENAI_API_KEY nie jest ustawiony w .env")
    
    # Wczytaj dokumenty
    documents, metadatas, ids = load_documents_from_files("knowledge_base")
    
    if not documents:
        print("❌ Brak dokumentów do załadowania!")
        return
    
    print(f"\n📝 Przygotowano {len(documents)} dokumentów do załadowania")
    
    # Inicjalizuj Qdrant
    try:
        db = QdrantRAG(
            collection_name="recruitment_knowledge_base",
            use_azure_openai=True,
            azure_endpoint=azure_endpoint,
            azure_api_key=azure_api_key,
            azure_deployment=azure_deployment,
            azure_api_version=azure_api_version,
            qdrant_path="./qdrant_db"
        )
    except (RuntimeError, Exception) as e:
        error_str = str(e)
        if "already accessed" in error_str or "AlreadyLocked" in error_str or "already locked" in error_str.lower():
            print("\n" + "=" * 60)
            print("❌ BŁĄD: Baza danych Qdrant jest już używana!")
            print("=" * 60)
            print("\n📌 Rozwiązanie:")
            print("   1. Zamknij aplikację (app.py) jeśli jest uruchomiona")
            print("   2. Sprawdź czy nie ma innych procesów używających Qdrant")
            print("   3. Spróbuj ponownie za chwilę")
            print("\n💡 Alternatywnie:")
            print("   - Użyj Qdrant server dla współbieżnego dostępu")
            print("   - Lub poczekaj aż aplikacja zwolni blokadę")
            print("=" * 60)
            return
        else:
            print(f"\n❌ Nieoczekiwany błąd podczas inicjalizacji Qdrant: {error_str}")
            raise
    
    # Załaduj dokumenty
    print(f"\n📤 Ładowanie dokumentów do Qdrant...")
    db.add_documents(documents, ids=ids, metadatas=metadatas)
    
    print(f"\n✅ Załadowano {len(documents)} dokumentów do kolekcji 'recruitment_knowledge_base'")
    print(f"📊 Łączna liczba dokumentów w kolekcji: {db.count()}")
    
    # Test wyszukiwania
    print("\n" + "=" * 60)
    print("TEST WYSZUKIWANIA")
    print("=" * 60)
    
    test_queries = [
        "Jakie są etapy rekrutacji?",
        "Co to jest RODO?",
        "Jakie są wartości firmy?"
    ]
    
    for query in test_queries:
        print(f"\n❓ Pytanie: {query}")
        results = db.search(query, n_results=2)
        if results:
            print(f"   Znaleziono {len(results)} wyników:")
            for i, r in enumerate(results, 1):
                print(f"   {i}. Źródło: {r['metadata'].get('source', 'N/A')}")
                print(f"      Fragment: {r['document'][:100]}...")
        else:
            print("   Brak wyników")
    
    print("\n" + "=" * 60)
    print("✅ Zakończono!")
    print("=" * 60)


if __name__ == "__main__":
    main()

