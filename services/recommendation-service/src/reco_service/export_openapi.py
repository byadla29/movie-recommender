"""Print this service's OpenAPI document as stable, sorted JSON.

Used by scripts/export-openapi.sh to refresh contracts/openapi/. CI regenerates it and fails
if the committed file differs, so every API change is visible in code review.
"""

import json
import os
import sys


def main() -> None:
    # Building the app needs settings, but never connects to the database.
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://unused@localhost/unused")
    from reco_service.main import create_app

    spec = create_app().openapi()
    sys.stdout.write(json.dumps(spec, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
