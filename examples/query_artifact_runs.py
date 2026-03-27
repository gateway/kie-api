"""Query recent artifact runs from outputs/index.jsonl."""

from kie_api import get_latest_successful_run, list_recent_runs, list_runs_by_model


def main() -> None:
    recent = list_recent_runs(limit=10)
    print("recent")
    for entry in recent:
        print(entry.model_dump())

    print("by model")
    for entry in list_runs_by_model("nano-banana-2", limit=5):
        print(entry.model_dump())

    latest = get_latest_successful_run()
    print("latest successful")
    print(latest.model_dump() if latest else None)


if __name__ == "__main__":
    main()
