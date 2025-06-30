"""
footy/cli.py
~~~~~~~~~~~~
Standalone CLI for my EFL-PL Historical Odds Toolkit.

Example use:
    python -m footy.cli 2024                 # pull latest EPL + EFL
    python -m footy.cli 1998-2005 --leagues CH,L1
"""

import re
from pathlib import Path
import typer

# helpers live in fetch.py
from .fetch import download_csv, ingest_to_duckdb, TIER_MAP

app = typer.Typer(help="Grab season CSVs and build a DuckDB in ./data/")

# ----------------------------------------------------------------------
# main command – I don't bother with sub-commands yet
# ----------------------------------------------------------------------
@app.callback()
def main(
    seasons: str = typer.Argument(
        ...,
        help="Season or range, e.g. 1998-2005 or just 2024",
    ),
    leagues: str = typer.Option(
        "EPL,CH,L1,L2",
        help="Comma-separated tiers (EPL, CH, L1, L2)",
    ),
):
    """
    Pull down the CSVs I need and whack them into a single DuckDB file.
    """
    db_path = Path("data/footy.duckdb")

    # ---- Parse season range "1998-2005" (inclusive) or single "2024" ----
    years = re.findall(r"\d{4}", seasons)  # grab all 4-digit numbers
    start, end = int(years[0]), int(years[-1])
    year_range = range(start, end + 1)

    # normalise league list to uppercase
    chosen = [lg.strip().upper() for lg in leagues.split(",")]

    csv_paths: list[Path] = []
    for yr in year_range:
        # football-data codes seasons like "9899", "2425"
        code = f"{str(yr)[-2:]}{str(yr + 1)[-2:]}"
        for lg in chosen:
            tier = TIER_MAP[lg]                       # EPL → E0, etc.
            dest = Path("data/raw") / f"{tier}_{code}.csv"
            csv_paths.append(download_csv(code, tier, dest))

    # smash everything into DuckDB
    ingest_to_duckdb(csv_paths, db_path)


# ----------------------------------------------------------------------
# allows: python -m footy.cli ...
# ----------------------------------------------------------------------
if __name__ == "__main__":
    typer.run(main)
