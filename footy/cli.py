"""
Single-command CLI: python -m footy.cli SEASONS [--leagues ...]
"""

import re
from pathlib import Path
import typer

from .fetch import download_csv, ingest_to_duckdb, TIER_MAP

def main(
    seasons: str = typer.Argument(..., help="1998-2024 or single 2024"),
    leagues: str = typer.Option("EPL,CH,L1,L2", help="Comma list tiers"),
):
    """Download CSVs and build DuckDB."""
    db = Path("data/footy.duckdb")
    yrs = re.findall(r"\d{4}", seasons)
    start, end = int(yrs[0]), int(yrs[-1])
    csvs = []
    for y in range(start, end + 1):
        code = f"{str(y)[-2:]}{str(y+1)[-2:]}"
        for lg in [x.strip().upper() for x in leagues.split(",")]:
            dest = Path("data/raw") / f"{TIER_MAP[lg]}_{code}.csv"
            csvs.append(download_csv(code, TIER_MAP[lg], dest))
    ingest_to_duckdb(csvs, db)

if __name__ == "__main__":
    typer.run(main)
