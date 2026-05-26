import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.rag.retriever.vector_retriever import VectorRetriever
from app.storage.documents import DocumentStorage

USER_ID     = "default_user"
DOCUMENT_ID = "psychology.pdf_f28b422e10e8"

# Step 1 — Load vectorstore and retriever
doc_storage = DocumentStorage(user_id=USER_ID)
doc_path    = doc_storage.get_document_path(DOCUMENT_ID)

vr = VectorRetriever(user_id=USER_ID)
vectorstore, retriever = vr.load_or_create_vectorstore(
    document_id=DOCUMENT_ID,
    pdf_path=doc_path,
)

# Step 2 — Invoke retriever with test query
raw_docs = list(retriever.invoke("supervised learning"))

# Step 3 — Print source metadata and generated IDs
print(f"\nTotal retrieved: {len(raw_docs)}")
print("=" * 60)

for i, doc in enumerate(raw_docs):
    source = doc.metadata.get("source", "unknown")
    page   = doc.metadata.get("page", 0)

    filename = str(source).replace("\\", "/").split("/")[-1]
    chunk_id = f"{filename}__p{page}"

    print(f"\nDoc      : {i+1}")
    print(f"Source   : {source}")
    print(f"Page     : {page}")
    print(f"Chunk ID : {chunk_id}")
    print(f"Text     : {doc.page_content[:100]}")
    print("-" * 60)