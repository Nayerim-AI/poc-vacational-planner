#!/usr/bin/env python
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.rag.wiki_activities import build_wiki_activity_candidates


def main() -> None:
    base_path = Path("extracted/AA")
    output_dir = Path("data")
    build_wiki_activity_candidates(base_path, output_dir)


if __name__ == "__main__":
    main()
