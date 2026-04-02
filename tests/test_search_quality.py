"""
Tests for hybrid search quality and correctness.

Requires a running PostgreSQL database with ingested documents.
Run with: uv run pytest tests/test_search_quality.py -v
"""

import asyncio

import pytest

from utils.db_utils import (
    _build_or_tsquery,
    acquire,
    embed_for_search,
    hybrid_search,
    initialize_database,
    search_vectors,
)

# Dedicated event loop for sync test wrappers (avoids deprecated get_event_loop)
_loop = asyncio.new_event_loop()


def run(coro):
    """Run an async function synchronously on the test event loop."""
    return _loop.run_until_complete(coro)


# ---------------------------------------------------------------------------
# Setup: initialize pool once
# ---------------------------------------------------------------------------

_embed_cache: dict[str, str] = {}


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    run(initialize_database())


def _embed(query: str) -> str:
    """Embed a query, caching results to avoid repeated API calls."""
    if query not in _embed_cache:
        _embed_cache[query] = run(embed_for_search(query))
    return _embed_cache[query]


# ---------------------------------------------------------------------------
# Unit tests: _build_or_tsquery
# ---------------------------------------------------------------------------


class TestBuildOrTsquery:
    def test_normal_query(self):
        assert _build_or_tsquery("customer retention rate") == "customer | retention | rate"

    def test_empty_string(self):
        assert _build_or_tsquery("") == ""

    def test_whitespace_only(self):
        assert _build_or_tsquery("   ") == ""

    def test_single_char_words_filtered(self):
        assert _build_or_tsquery("a b cd") == "cd"

    def test_special_chars_stripped(self):
        result = _build_or_tsquery("what's the rate?")
        assert "?" not in result
        assert "'" not in result

    def test_sql_operators_stripped(self):
        result = _build_or_tsquery("hello & world | test")
        words = [w.strip() for w in result.split("|")]
        for w in words:
            assert w == "" or w.isalnum()

    def test_preserves_alphanumeric(self):
        result = _build_or_tsquery("Q4 2024 revenue")
        assert "Q4" in result
        assert "2024" in result
        assert "revenue" in result


# ---------------------------------------------------------------------------
# Integration tests: tsvector column
# ---------------------------------------------------------------------------


class TestTsvectorColumn:
    def test_all_chunks_have_tsvector(self):
        """Every chunk should have a populated search_vector."""
        async def check():
            async with acquire() as conn:
                total = await conn.fetchval("SELECT COUNT(*) FROM chunks")
                with_sv = await conn.fetchval(
                    "SELECT COUNT(*) FROM chunks WHERE search_vector IS NOT NULL"
                )
            return total, with_sv

        total, with_sv = run(check())
        assert total > 0, "No chunks in database"
        assert with_sv == total, f"{total - with_sv} chunks missing search_vector"

    def test_tsvector_contains_expected_terms(self):
        """Spot-check that tsvector indexes content terms."""
        async def check():
            async with acquire() as conn:
                return await conn.fetchrow(
                    """
                    SELECT search_vector::text as sv FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                    WHERE c.content ILIKE '%retention%'
                    LIMIT 1
                    """
                )

        row = run(check())
        assert row is not None, "No chunk with 'retention' found"
        assert "retent" in row["sv"], "Stemmed 'retention' not in tsvector"


# ---------------------------------------------------------------------------
# Integration tests: hybrid_search
# ---------------------------------------------------------------------------


QUERY_EXPECTATIONS = [
    ("core collaboration hours", "10 AM"),
    ("employee benefits and PTO policy", "PTO"),
    ("engineering team structure", "Engineer"),
    ("GlobalFinance Corp results", "GlobalFinance"),
    ("DocFlow AI loan processing time reduction", "processing"),
    ("company revenue growth", "Revenue"),
    ("SOC 2 certification goals", "SOC 2"),
    ("client implementation timeline", "implementation"),
    ("what AI models does NeuralFlow use", "AI"),
    ("Q4 2024 customer retention rate", "retention"),
]


class TestHybridSearch:
    @pytest.mark.parametrize("query,expected_term", QUERY_EXPECTATIONS)
    def test_returns_relevant_results(self, query, expected_term):
        """Top 5 results should contain the expected term at least once."""
        embedding_str = _embed(query)
        results = run(hybrid_search(query, embedding_str, limit=5))

        assert len(results) > 0, f"No results for: {query}"

        all_content = " ".join(r["content"] for r in results)
        assert expected_term.lower() in all_content.lower(), (
            f"'{expected_term}' not found in top 5 results for: {query}"
        )

    def test_returns_correct_fields(self):
        """Each result should have all expected fields."""
        embedding_str = _embed("test query")
        results = run(hybrid_search("test query", embedding_str, limit=1))

        assert len(results) > 0
        r = results[0]
        required_fields = [
            "chunk_id", "content", "chunk_metadata", "chunk_index",
            "document_id", "title", "source", "doc_metadata", "rrf_score",
        ]
        for field in required_fields:
            assert field in r, f"Missing field: {field}"

    def test_rrf_scores_are_positive(self):
        """All RRF scores should be positive floats."""
        embedding_str = _embed("revenue growth")
        results = run(hybrid_search("revenue growth", embedding_str, limit=5))

        for r in results:
            assert isinstance(r["rrf_score"], float)
            assert r["rrf_score"] > 0

    def test_results_ordered_by_rrf_score(self):
        """Results should be in descending RRF score order."""
        embedding_str = _embed("team structure")
        results = run(hybrid_search("team structure", embedding_str, limit=5))

        scores = [r["rrf_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_empty_query_builds_empty_tsquery(self):
        """Empty query should produce empty tsquery string."""
        assert _build_or_tsquery("") == ""


# ---------------------------------------------------------------------------
# Integration tests: hybrid vs vector-only comparison
# ---------------------------------------------------------------------------


class TestHybridVsVectorOnly:
    def test_hybrid_finds_keyword_matches(self):
        """Hybrid top result should contain relevant keywords."""
        query = "core collaboration hours"
        embedding_str = _embed(query)
        results = run(hybrid_search(query, embedding_str, limit=5))

        assert len(results) > 0
        h_content = results[0]["content"].lower()
        assert "10 am" in h_content or "core" in h_content

    def test_hybrid_changes_ranking_for_some_queries(self):
        """Hybrid should produce different rankings than vector-only
        for at least some queries, proving keyword search contributes."""
        queries_with_different_top = 0

        for query, _ in QUERY_EXPECTATIONS:
            embedding_str = _embed(query)
            hybrid = run(hybrid_search(query, embedding_str, limit=1))
            vector = run(search_vectors(embedding_str, limit=1))

            if hybrid and vector and hybrid[0]["chunk_id"] != vector[0]["chunk_id"]:
                queries_with_different_top += 1

        assert queries_with_different_top >= 2, (
            f"Only {queries_with_different_top}/10 queries had different top results — "
            "keyword search may not be contributing meaningfully"
        )
