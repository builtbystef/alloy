"""Export the OpenAPI schema without starting a server.

    uv run --package alloy-api python -m alloy_api.openapi [-o PATH]

`packages/api-client` runs this to generate its TypeScript types.
"""

import argparse
import json
import sys
from pathlib import Path

from alloy_api.main import app


def schema_json() -> str:
    return json.dumps(app.openapi(), indent=2) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-o", "--output", type=Path, help="write here instead of stdout")
    args = parser.parse_args(argv)

    if args.output is None:
        sys.stdout.write(schema_json())
    else:
        args.output.write_text(schema_json())


if __name__ == "__main__":
    main()
