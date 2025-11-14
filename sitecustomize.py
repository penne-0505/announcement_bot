"""Test実行時にsrcディレクトリをインポートパスへ追加するユーティリティ。"""
from __future__ import annotations

import sys
from pathlib import Path

# プロジェクトルート配下のsrcディレクトリをPythonパスへ優先的に追加する。
_SRC_PATH = Path(__file__).resolve().parent / "src"
if _SRC_PATH.exists():
    src_str = str(_SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
