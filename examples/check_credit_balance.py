from __future__ import annotations

import sys
from pprint import pprint

from kie_api import get_credit_balance
from kie_api.exceptions import MissingConfigurationError


def main() -> None:
    try:
        result = get_credit_balance()
    except MissingConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        print("Load your key first, for example:", file=sys.stderr)
        print("  cp .env.example .env.live", file=sys.stderr)
        print("  set -a && source .env.live && set +a", file=sys.stderr)
        raise SystemExit(1) from exc
    pprint(result.model_dump())


if __name__ == "__main__":
    main()
