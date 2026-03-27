"""Rebuild outputs/index.jsonl from existing run folders."""

from kie_api import rebuild_run_index


def main() -> None:
    path = rebuild_run_index()
    print(path)


if __name__ == "__main__":
    main()
