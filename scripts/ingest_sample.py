from pathlib import Path

from app.main import run_ingest


if __name__ == "__main__":
    sample = Path(__file__).resolve().parent.parent / "data" / "sample_gtm_notes.md"
    print(run_ingest(str(sample)))

