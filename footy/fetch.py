"""
fetch.py — download season CSVs and build DuckDB
"""

from pathlib import Path
import requests
import pandas as pd
import duckdb
import typer

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{tier}.csv"
TIER_MAP = {"EPL": "E0", "CH": "E1", "L1": "E2", "L2": "E3"}


def download_csv(season_code: str, tier_code: str, dest: Path) -> Path:
    """Download one CSV if not on disk."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        typer.echo(f"✓ {dest.name} (cached)")
        return dest
    url = BASE_URL.format(season=season_code, tier=tier_code)
    typer.echo(f"⇢ {dest.name}")
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def ingest_to_duckdb(csv_paths: list[Path], db_path: Path):
    """Concatenate CSVs → DuckDB table `results`."""
    frames = [pd.read_csv(p) for p in csv_paths]
    big = pd.concat(frames, ignore_index=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    duckdb.connect(db_path).execute(
        "CREATE OR REPLACE TABLE results AS SELECT * FROM big"
    )
    typer.echo(f"✅ DuckDB ready: {db_path}")
