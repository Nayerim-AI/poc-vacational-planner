from pathlib import Path

from app.llm.tools.rag_store import RAGTool


def test_rag_search_returns_snippet(tmp_path: Path):
    docs_dir = tmp_path / "extracted"
    docs_dir.mkdir()
    (docs_dir / "lisbon.txt").write_text("Lisbon guide with pastel de nata and tram 28", encoding="utf-8")

    rag = RAGTool(store_path=docs_dir, dim=64)
    rag.load_dir()

    results = rag.search("Lisbon", top_k=1)
    assert results
    assert "Lisbon" in results[0][0]
