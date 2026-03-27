"""Load one run artifact and print its hero asset paths."""

import sys

from kie_api import get_run_summary, load_run_artifact


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python examples/print_run_summary.py /absolute/path/to/run_dir")

    run_dir = sys.argv[1]
    summary = get_run_summary(run_dir)
    run = load_run_artifact(run_dir)

    print(summary.model_dump())
    print(
        {
            "hero_original": summary.hero_original,
            "hero_web": summary.hero_web,
            "hero_thumb": summary.hero_thumb,
            "run_id": run.run_id,
        }
    )


if __name__ == "__main__":
    main()
