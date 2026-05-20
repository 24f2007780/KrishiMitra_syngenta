"""Simple local retrieval over knowledge/*.txt and *.md using BM25."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _chunk_text(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    text = text.strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for p in paragraphs:
        if size + len(p) > max_chars and buf:
            chunks.append("\n\n".join(buf))
            tail = "\n\n".join(buf)[-overlap:] if overlap else ""
            buf = ([tail + "\n\n" + p] if tail else [p])
            size = len(buf[0])
        else:
            buf.append(p)
            size += len(p) + 2
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


class RagIndex:
    def __init__(self, knowledge_dir: Path):
        self._sources: list[str] = []
        self._chunks: list[str] = []
        self._bm25: BM25Okapi | None = None
        self._build(knowledge_dir)

    def _build(self, knowledge_dir: Path) -> None:
        if not knowledge_dir.is_dir():
            logger.warning("Knowledge directory missing: %s", knowledge_dir)
            return

        paths = sorted(list(knowledge_dir.glob("*.txt")) + list(knowledge_dir.glob("*.md")))
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                logger.warning("Skip %s: %s", path, e)
                continue
            for i, chunk in enumerate(_chunk_text(text)):
                self._chunks.append(chunk)
                self._sources.append(f"{path.name}#{i}")

        if not self._chunks:
            logger.warning("No knowledge chunks loaded from %s", knowledge_dir)
            return

        tokenized = [_tokenize(c) for c in self._chunks]
        self._bm25 = BM25Okapi(tokenized)
        logger.info("RAG: loaded %s chunks from %s files", len(self._chunks), len(paths))

    @property
    def is_ready(self) -> bool:
        return self._bm25 is not None and bool(self._chunks)

    def retrieve(self, query: str, top_k: int = 4) -> str:
        if not self._bm25 or not query.strip():
            return ""
        q = _tokenize(query)
        if not q:
            return ""
        scores = self._bm25.get_scores(q)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        parts: list[str] = []
        for i in ranked:
            if scores[i] <= 0:
                continue
            parts.append(f"[{self._sources[i]}]\n{self._chunks[i]}")
        # Tiny POC corpora: BM25 can be zero for all tokens; still attach best chunk.
        if not parts and ranked:
            i = ranked[0]
            parts.append(f"[{self._sources[i]}]\n{self._chunks[i]}")
        return "\n\n---\n\n".join(parts)
