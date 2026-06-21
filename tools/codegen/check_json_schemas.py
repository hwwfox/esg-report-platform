import json
import sys
from pathlib import Path


def main() -> int:
    roots = [Path(p) for p in sys.argv[1:]] or [Path("contracts/schemas"), Path("ai/schemas")]
    failed = False
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.json"):
            try:
                json.loads(path.read_text(encoding="utf-8"))
                print(f"schema ok: {path}")
            except Exception as exc:
                print(f"schema invalid: {path}: {exc}")
                failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
