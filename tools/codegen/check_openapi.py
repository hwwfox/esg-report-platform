import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: check_openapi.py <openapi.yaml>")
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"missing OpenAPI file: {path}")
        return 1
    if yaml is None:
        print("PyYAML not installed; only checking file exists")
        return 0
    with path.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    for key in ["openapi", "info", "paths"]:
        if key not in doc:
            print(f"OpenAPI missing required key: {key}")
            return 1
    print(f"OpenAPI check passed: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
