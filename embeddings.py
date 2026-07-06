"""
embeddings.py — Semantic similarity engine for The Dot Resource Matcher.

What is this?
─────────────
Instead of matching startups to resources using only keyword rules, this module
uses *sentence embeddings* — a real machine learning technique where text is
converted into high-dimensional vectors (numbers) that capture *meaning*, not
just keywords.

Two texts with similar meaning will have vectors that point in the same
direction, even if they use completely different words. For example:
  "We need legal help to structure our company"
  "Corporate formation and incorporation support"
→ These will have a high cosine similarity (~0.85) despite sharing zero words.

How it works in The Dot pipeline:
──────────────────────────────────
1. At startup, all resources from resources.csv are encoded into 384-dim vectors
   and cached in memory (done once per Streamlit session).
2. When a startup submits their profile, it is converted into a natural-language
   text description and encoded into the same vector space.
3. Cosine similarity is computed between the profile vector and each resource
   vector → gives a 0–1 semantic relevance score for every resource.
4. This score is combined with the rule-based score in matcher.py:
    final_pre_score = RULE_WEIGHT * rule_score + SEMANTIC_WEIGHT * semantic_score * 100
This means the pre-filter now understands *context and meaning*, not just tags.

Model used: paraphrase-multilingual-MiniLM-L12-v2
──────────────────────────────────────────────────
- 118 MB, runs entirely on CPU (no GPU needed)
- Trained on 50+ languages including French, English, and Arabic
- 384-dimensional output vectors
- ~50ms per encoding on CPU
- Source: https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import EMBEDDING_MODEL

# ── Lazy model loader ──────────────────────────────────────────────────────────
# We load the model only once and keep it in module-level memory.
# This avoids re-loading 118MB weights on every function call.

_model = None


def _get_model():
    """Load the sentence-transformer model once and cache it in memory."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print(f"[embeddings] Loading model: {EMBEDDING_MODEL}")
            _model = SentenceTransformer(EMBEDDING_MODEL)
            print("[embeddings] Model loaded.")
        except ImportError:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers"
            )
    return _model


# ── Text builders ──────────────────────────────────────────────────────────────

def build_resource_text(row: pd.Series) -> str:
    """
    Convert a resource row into a natural-language sentence for encoding.
    We combine the most semantically rich fields: name, type, description,
    ideal_profile, needs, and sectors.
    Richer text → better embedding → more accurate similarity.
    """
    parts = []
    if row.get("name"):
        parts.append(str(row["name"]))
    if row.get("type"):
        parts.append(f"Type: {row['type']}")
    if row.get("description"):
        parts.append(str(row["description"]))
    if row.get("ideal_profile"):
        parts.append(f"Ideal for: {row['ideal_profile']}")
    if row.get("needs") and isinstance(row["needs"], list):
        readable = [n.replace("_", " ") for n in row["needs"]]
        parts.append(f"Covers: {', '.join(readable)}")
    if row.get("sectors") and isinstance(row["sectors"], list):
        parts.append(f"Sectors: {', '.join(row['sectors'])}")
    return ". ".join(parts)


def build_profile_text(profile: dict) -> str:
    """
    Convert a startup profile dict into a natural-language sentence for encoding.
    The goal is to describe the startup's situation in plain text so the model
    can find resources that match this description semantically.
    """
    parts = []

    stage = profile.get("stage", "")
    sector = profile.get("sector", "")
    bmodel = profile.get("business_model", "")

    if stage:
        parts.append(f"We are a {stage} stage startup")
    if sector:
        parts.append(f"operating in the {sector} sector")
    if bmodel:
        parts.append(f"with a {bmodel} business model")

    needs = profile.get("needs", [])
    if needs:
        readable = [n.replace("_", " ") for n in needs]
        parts.append(f"Our main needs are: {', '.join(readable)}")

    flags = []
    if profile.get("legal_gap"):
        flags.append("we have a legal structuring gap")
    if profile.get("team_gap"):
        flags.append("we need to strengthen our team")
    if profile.get("needs_funding"):
        flags.append("we are actively seeking funding")
    if profile.get("pre_product"):
        flags.append("we are still building our product")
    if profile.get("has_traction"):
        flags.append("we have early traction")
    if profile.get("solo_founder"):
        flags.append("we are a solo founder")
    if profile.get("diaspora"):
        flags.append("we are diaspora founders")
    if profile.get("outside_tunis"):
        flags.append("we are based outside Tunis")
    if profile.get("is_ai"):
        flags.append("we are an AI startup")

    if flags:
        parts.append(". Additionally, " + ", ".join(flags))

    spider = profile.get("spider_scores", {})
    weak_dims = [dim for dim, score in spider.items() if score < 40]
    if weak_dims:
        parts.append(f"Our weak areas are: {', '.join(weak_dims)}")

    return ". ".join(parts) + "."


# ── Core encoding functions ────────────────────────────────────────────────────

def encode_resources(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """
    Encode all resources into embedding vectors.
    Returns a dict: resource_id → numpy array (384,)

    This is called once and the result is cached in matcher.py via
    @st.cache_data to avoid re-encoding on every request.
    """
    model = _get_model()
    texts = {}
    for _, row in df.iterrows():
        texts[row["id"]] = build_resource_text(row)

    ids   = list(texts.keys())
    sents = list(texts.values())

    print(f"[embeddings] Encoding {len(sents)} resources...")
    vectors = model.encode(sents, batch_size=32, show_progress_bar=False)
    print("[embeddings] Resource encoding done.")

    return {rid: vec for rid, vec in zip(ids, vectors)}


def encode_profile(profile: dict) -> np.ndarray:
    """
    Encode a startup profile into a single embedding vector.
    Called at match time — fast (~50ms on CPU).
    """
    model = _get_model()
    text  = build_profile_text(profile)
    print(f"[embeddings] Profile text: {text[:120]}...")
    return model.encode([text])[0]


# ── Cosine similarity ──────────────────────────────────────────────────────────

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine similarity between two vectors.
    Returns a float in [0, 1] where:
      1.0 = identical direction (perfect semantic match)
      0.0 = orthogonal (no semantic relation)
    Formula: cos(θ) = (a · b) / (||a|| × ||b||)
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ── Main function: semantic scores for all resources ──────────────────────────

def semantic_scores(
    profile: dict,
    resource_embeddings: dict[str, np.ndarray],
) -> dict[str, float]:
    """
    Compute cosine similarity between the startup profile and every resource.

    Args:
        profile: startup profile dict (from the diagnostic form)
        resource_embeddings: dict of resource_id → embedding vector
                             (pre-computed and cached)

    Returns:
        dict of resource_id → similarity score in [0, 1]
        Higher = more semantically similar to the startup's profile.

    Example output:
        {
          "R001": 0.82,   ← very relevant
          "R003": 0.61,   ← moderately relevant
          "R007": 0.23,   ← low relevance
          ...
        }
    """
    profile_vec = encode_profile(profile)
    scores = {}
    for rid, res_vec in resource_embeddings.items():
        scores[rid] = cosine_similarity(profile_vec, res_vec)
    return scores
