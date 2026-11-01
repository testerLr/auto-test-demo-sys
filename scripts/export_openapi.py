"""导出当前代码对应的 OpenAPI 规范到 docs/openapi.json（不需要连数据库）。"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app  # noqa: E402

OUTPUT = PROJECT_ROOT / "docs" / "openapi.json"


def main() -> None:
    spec = app.openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"已导出 {len(spec['paths'])} 个路径 -> {OUTPUT}")


if __name__ == "__main__":
    main()
