"""
footy/cli.py
~~~~~~~~~~~~
Single-command CLI for EFL-PL Historical Odds Toolkit.

Run it like:
    python -m footy.cli 2024 --leagues EPL,CH
"""

import re
from pathlib import Path
import typer

# local helpers we wrote in fetch.py
from .fetch import download_csv, ingest_to_duckdb, TIER_MAP

# Typer app wrapper (even though we only have one command for now)
app = typer.Typer(help="Grab season CSVs and build a DuckDB in ./data/")

# ----------------------------------------------------------------------
# main() is the only command right now
# ----------------------------------------------------------------------
@app.callback()  # <-- treat main() as the root command, no sub-commands needed
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
    Download CSVs (one per league / season) and merge them into DuckDB.

    Example calls:
      python -m footy.cli 2024                 # latest EPL+EFL
      python -m footy.cli 1997-2000 --leagues CH,L1
    """
    db_path = Path("data/footy.duckdb")

    # ---- Parse season range "1998-2005" or single "2024" ----
    years = re.findall(r"\d{4}", seasons)
    start, end = int(years[0]), int(years[-1])
    year_range = range(start, end + 1)

    # Normalise league list
    selected_leagues = [lg.strip().upper() for lg in leagues.split(",")]

    csv_paths = []
    for yr in year_range:
        # football-data uses "9899", "2425" format
        season_code = f"{str(yr)[-2:]}{str(yr + 1)[-2:]}"
        for lg in selected_leagues:
            tier_code = TIER_MAP[lg]           # EPL -> E0, etc.
            dest = Path("data/raw") / f"{tier_code}_{season_code}.csv"
            # do the download (cached if file exists)
            csv_paths.append(download_csv(season_code, tier_code, dest))

    # slap everything into DuckDB
    ingest_to_duckdb(csv_paths, db_path)


# ----------------------------------------------------------------------
# Make the module runnable:  python -m footy.cli ...
# ----------------------------------------------------------------------
if __name__ == "__main__":
    typer.run(main)
