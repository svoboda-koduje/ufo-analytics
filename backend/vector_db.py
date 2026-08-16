import os
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Inicializace klienta OpenAI (využívá klíč z prostředí Renderu)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Inicializace klienta pro Qdrant (v cloudu nebo lokálně přes Docker)
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))

qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
COLLECTION_NAME = "ufo_documents"

def init_vector_db():
    """
    Zkontroluje, zda v Qdrantu existuje kolekce pro dokumenty. 
    Pokud ne, vytvoří ji pro vektory o velikosti 1536 (standard OpenAI).
    """
    try:
        collections = qdrant_client.get_collections().collections
        exists = any(col.name == COLLECTION_NAME for col in collections)
        
        if not exists:
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=1536,  # Velikost vektoru pro model text-embedding-3-small
                    distance=models.Distance.COSINE  # Kosinová podobnost pro sémantické hledání
                )
            )
            print(f"✅ Vektorová kolekce '{COLLECTION_NAME}' byla úspěšně vytvořena v Qdrantu.")
    except Exception as e:
        print(f"⚠️ Qdrant není dostupný při startu (běží lokálně nebo se připojuje): {e}")

def get_embedding(text: str) -> list:
    """
    Převede libovolný textový řetězec na číselný vektor (embedding) pomocí OpenAI API.
    """
    response = openai_client.embeddings.create(
        input=[text],
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def store_document_embedding(case_id: int, text_content: str, metadata: dict):
    """
    Vygeneruje embedding z textu (např. překladu spisu) a uloží ho do Qdrantu.
    """
    vector = get_embedding(text_content)
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=case_id,
                vector=vector,
                payload={"case_id": case_id, "text": text_content, **metadata}
            )
        ]
    )
    print(f"🔍 [Qdrant] Úspěšně uložen sémantický embedding pro případ #{case_id}.")

def search_similar_documents(query_text: str, limit: int = 5):
    """
    Převede vyhledávací dotaz uživatele na vektor a najde v Qdrantu 
    nejpodobnější dokumenty podle významu.
    """
    query_vector = get_embedding(query_text)
    
    hits = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=limit
    )
    
    results = []
    for hit in hits:
        results.append({
            "case_id": hit.payload.get("case_id"),
            "score": hit.score,  # Míra shody (blíže k 1.0 znamená identický význam)
            "payload": hit.payload
        })
    return results
