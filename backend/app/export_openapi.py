"""Write the OpenAPI schema to a file: `uv run python -m app.export_openapi <path>`.

The frontend generates its API types from this file.
"""

import json
import sys
from pathlib import Path

from app.main import app


def main() -> None:
    target = Path(sys.argv[1])
    schema = json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"
    target.write_text(schema, encoding="utf-8", newline="\n")
    print(f"OpenAPI schema written to {target}")


if __name__ == "__main__":
    main()
