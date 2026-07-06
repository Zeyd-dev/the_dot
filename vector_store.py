"""
vector_store.py — RAG vector database layer (proof of concept).

STATUS: Feature branch only (feature/rag-vector-store).
        The current system (embeddings.py + in-memory cosine) is the default.
        Set USE_RAG = True in config.py to activate this module.

What this adds over embeddings.py
──────────────────────────────────
embeddings.py (current default):
  - Encodes all resources into numpy arrays in memory
  - Loops over every resource to compute cosine similarity at query time
  - Re-encodes resources on each new Streamlit session (not persisted)
  - Works well for < ~500 resources

vector_store.py (this file, RAG mode):
  - Persists embeddings to disk (./chroma_db/) via ChromaDB
  - Uses ANN (Approximate Nearest Neighbor) index for fast retrieval
  - Does NOT re-encode resources unless the catalog changes
  - Scales to millions of documents with sub-millisecond retrieval
  - Enables metadata filtering (e.g. only "incubator" type resources)

When does this matter?
───────────────────────
Today (8 resources)  → zero practical difference
At 500+ resources    → 10x faster retrieval, no session re-encoding
At 10 000+ resources → the current approach becomes unusably slow

Usage
──────
1. Build index once (run this script directly):
       python vector_store.py

2. Enable RAG in config.py:
       USE_RAG = True

3. matcher.py will automatically use ChromaDB instead of the in-memory loop.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from config import EMBEDDING_MODEL
from embeddings import build_resource_text, build_profile_text, _get_model

# ── ChromaDB persistence path ─────────────────────────────────────────────────
CHROMA_PATH       = str(Path(__file__).parent / "chroma_db")
COLLECTION_NAME   = "resources"


# ── Index management ──────────────────────────────────────────────────────────

def _get_collection(read_only: bool = False):
    """
    Connect to (or create) the ChromaDB collection.
    ChromaDB persists the index to CHROMA_PATH automatically.
    """
    try:
        import chromadb
    except ImportError:
        raise ImportError(
            "chromadb is not installed. "
            "Run: pip install chromadb"
        )

    client     = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name     = COLLECTION_NAME,
        metadata = {"hnsw:space": "cosine"},   # use cosine distance for ANN
    )
    return collection


def build_index(df: pd.DataFrame, force: bool = False) -> None:
    """
    Encode all resources and persist them to the ChromaDB vector store.

    Args:
        df:    Resources dataframe (from resources.csv)
        force: If True, drops and rebuilds the index even if it exists.

    This should be run once when resources.csv changes.
    Running it again on the same data is safe (ChromaDB deduplicates by ID).
    """
    collection = _get_collection()

    if force:
        # Drop existing entries
        existing = collection.get()
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            print(f"[vector_store] Dropped {len(existing['ids'])} existing entries.")

    model = _get_model()

    ids       = []
    texts     = []
    metadatas = []

    for _, row in df.iterrows():
        rid  = str(row["id"])
        text = build_resource_text(row)
        ids.append(rid)
        texts.append(text)
        metadatas.append({
            "name":  str(row.get("name", "")),
            "type":  str(row.get("type", "")),
        })

    print(f"[vector_store] Encoding {len(texts)} resources...")
    vectors = model.encode(texts, batch_size=32, show_progress_bar=False)
    print("[vector_store] Encoding done. Writing to ChromaDB...")

    collection.upsert(
        ids        = ids,
        embeddings = [v.tolist() for v in vectors],
        documents  = texts,
        metadatas  = metadatas,
    )
    print(f"[vector_store] Index built: {len(ids)} resources at {CHROMA_PATH}")


def index_exists() -> bool:
    """Return True if the ChromaDB index has been built (has at least 1 entry)."""
    try:
        collection = _get_collection()
        return collection.count() > 0
    except Exception:
        return False


def reset_index() -> None:
    """Delete all entries from the index (useful for testing / catalog refresh)."""
    collection = _get_collection()
    existing   = collection.get()
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        print(f"[vector_store] Index cleared ({len(existing['ids'])} entries removed).")
    else:
        print("[vector_store] Index was already empty.")


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve(profile: dict, top_k: int = 10) -> list[str]:
    """
    Find the top_k most semantically similar resources to the startup profile.

    This is the RAG retrieval step:
      profile text → embedding → ANN query in ChromaDB → top_k resource IDs

    Args:
        profile: startup profile dict (same format as the diagnostic form)
        top_k:   number of results to retrieve (default 10)

    Returns:
        List of resource IDs, ordered by semantic similarity (most similar first).

    Example:
        ["R002", "R005", "R001", "R007", "R003"]
    """
    if not index_exists():
        raise RuntimeError(
            "ChromaDB index is empty. Run: python vector_store.py "
            "(or set USE_RAG = False in config.py to use the default system)"
        )

    collection   = _get_collection()
    model        = _get_model()
    profile_text = build_profile_text(profile)

    print(f"[vector_store] Querying ChromaDB for top {top_k} resources...")
    profile_vec = model.encode([profile_text])[0].tolist()

    results = collection.query(
        query_embeddings = [profile_vec],
        n_results        = min(top_k, collection.count()),
    )

    ids = results["ids"][0]           # already sorted by similarity
    print(f"[vector_store] Retrieved: {ids}")
    return ids


def retrieve_with_scores(profile: dict, top_k: int = 10) -> dict[str, float]:
    """
    Same as retrieve() but also returns similarity scores.

    Returns:
        dict of resource_id → similarity score in [0, 1]
    """
    if not index_exists():
        raise RuntimeError("ChromaDB index is empty. Run: python vector_store.py")

    collection   = _get_collection()
    model        = _get_model()
    profile_text = build_profile_text(profile)
    profile_vec  = model.encode([profile_text])[0].tolist()

    results = collection.query(
        query_embeddings = [profile_vec],
        n_results        = min(top_k, collection.count()),
        include          = ["distances"],
    )

    ids       = results["ids"][0]
    distances = results["distances"][0]   # cosine distance = 1 - similarity

    return {rid: round(1.0 - dist, 4) for rid, dist in zip(ids, distances)}


# ── CLI entry point: build the index ─────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import json
    import ast

    resources_path = Path(__file__).parent / "data" / "resources.csv"
    if not resources_path.exists():
        print(f"ERROR: {resources_path} not found.")
        sys.exit(1)

    df = pd.read_csv(resources_path)

    # Parse JSON list columns
    for col in ("needs", "stages", "sectors"):
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: json.loads(x) if isinstance(x, str) and x.startswith("[")
                else (ast.literal_eval(x) if isinstance(x, str) else x)
            )

    force = "--force" in sys.argv
    build_index(df, force=force)
    print("\nDone. You can now set USE_RAG = True in config.py.")
