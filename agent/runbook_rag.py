"""
runbook_rag.py — FAISS-based vector search over engineering runbooks.

Loads all .md runbooks from /data/runbooks, embeds them, and provides
semantic search so the agent can retrieve the most relevant remediation steps.
"""

import os
from functools import lru_cache

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import MarkdownTextSplitter


RUNBOOK_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "runbooks")


@lru_cache(maxsize=1)
def _build_vectorstore():
    """
    Builds a FAISS vector store from all runbook .md files.
    Cached so it is only built once per session.
    """
    all_docs = []
    splitter = MarkdownTextSplitter(chunk_size=800, chunk_overlap=100)

    for filename in os.listdir(RUNBOOK_DIR):
        if filename.endswith(".md"):
            path = os.path.join(RUNBOOK_DIR, filename)
            loader = TextLoader(path, encoding="utf-8")
            raw_docs = loader.load()
            chunks = splitter.split_documents(raw_docs)
            for chunk in chunks:
                chunk.metadata["source"] = filename
            all_docs.extend(chunks)

    if not all_docs:
        return None

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectorstore = FAISS.from_documents(all_docs, embeddings)
    return vectorstore


def search_runbooks(query: str, top_k: int = 3) -> str:
    """
    Semantic search over runbook knowledge base.

    Args:
        query: Incident type or search query string.
        top_k: Number of top-matching chunks to retrieve.

    Returns:
        Concatenated runbook content most relevant to the query.
    """
    try:
        vs = _build_vectorstore()
        if vs is None:
            return "ERROR: No runbooks found in /data/runbooks directory."

        docs = vs.similarity_search(query, k=top_k)
        if not docs:
            return "No matching runbook sections found."

        sections = []
        for doc in docs:
            source = doc.metadata.get("source", "unknown.md")
            sections.append(f"--- From: {source} ---\n{doc.page_content}")

        return "=== RUNBOOK KNOWLEDGE BASE RESULTS ===\n\n" + "\n\n".join(sections)

    except Exception as e:
        # Fallback if embeddings fail (no API key etc.)
        return _keyword_fallback(query)


def _keyword_fallback(query: str) -> str:
    """Simple keyword fallback when embeddings are unavailable."""
    query_upper = query.upper()
    if any(kw in query_upper for kw in ["DATABASE", "CONNECTION", "POOL"]):
        fname = "db_connection_exhaustion.md"
    elif any(kw in query_upper for kw in ["MEMORY", "OOM", "HEAP", "JVM"]):
        fname = "memory_leak_oom.md"
    elif any(kw in query_upper for kw in ["RATE", "DDOS", "429", "ATTACK"]):
        fname = "api_rate_limit.md"
    elif any(kw in query_upper for kw in ["NETWORK", "TIMEOUT", "DNS"]):
        fname = "network_timeout.md"
    else:
        fname = "service_restart.md"

    path = os.path.join(RUNBOOK_DIR, fname)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f"=== RUNBOOK (keyword match): {fname} ===\n\n{f.read()}"
    except FileNotFoundError:
        return f"Runbook '{fname}' not found."
