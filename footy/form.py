"""
footy/form.py
-------------
Rolling N-match form table pulled from my DuckDB.

Examples
--------
python -m footy.form 2024 --top 10 --window 5
python -m footy.form 2005 --top 10 --window 5
"""

from pathlib import Path
import duckdb
import pandas as pd
import warnings
import typer
from rich.table import Table
from rich import print as rprint

# Quiet the “Could not infer format” chatter from pandas once and for all.
warnings.filterwarnings(
    "ignore",
    message="Could not infer format, so each element will be parsed individually",
    category=UserWarning,
)

app = typer.Typer()


def load_matches(db: Path) -> pd.DataFrame:
    """Grab raw results into a DataFrame."""
    con = duckdb.connect(db, read_only=True)
    return con.execute(
        "SELECT Date, HomeTeam, AwayTeam, FTR FROM results"
    ).fetchdf()


def prepare_season(df: pd.DataFrame, season_end: int) -> pd.DataFrame:
    """Filter rows to a single season window and melt to (match_date, club, pts)."""
    start = f"{season_end - 1}-07-01"
    end = f"{season_end}-06-30"

    # pandas happily parses both DD/MM/YY and DD/MM/YYYY when dayfirst=True
    dates = pd.to_datetime(df["Date"].str.strip(), dayfirst=True, errors="coerce")

    # keep only matches in that Jul-to-Jun window
    mask = dates.between(start, end)
    df = df.loc[mask].copy()
    df["match_date"] = dates.loc[mask]

    # explode each match into two club rows (home + away)
    home = df.rename(columns={"HomeTeam": "club"}).assign(
        pts=lambda x: x["FTR"].map({"H": 3, "D": 1, "A": 0})
    )[["match_date", "club", "pts"]]

    away = df.rename(columns={"AwayTeam": "club"}).assign(
        pts=lambda x: x["FTR"].map({"A": 3, "D": 1, "H": 0})
    )[["match_date", "club", "pts"]]

    return pd.concat([home, away], ignore_index=True)


def rolling_form(df: pd.DataFrame, window: int, top: int):
    """Return top clubs by rolling window points."""
    df = df.sort_values("match_date")
    roll = (
        df.groupby("club")["pts"]
        .rolling(window, min_periods=window)
        .sum()
        .reset_index()
    )
    latest = (
        roll.groupby("club")["pts"].last()
        .sort_values(ascending=False)
        .head(top)
    )
    return latest.items()


@app.callback()
def main(
    season: int = typer.Argument(..., help="Season end year, e.g. 2005 or 2024"),
    top: int = typer.Option(10, help="Rows to show"),
    window: int = typer.Option(5, help="Rolling-match window"),
):
    df_all = load_matches(Path("data/footy.duckdb"))
    df_season = prepare_season(df_all, season)
    rows = rolling_form(df_season, window, top)

    # pretty print
    table = Table(title=f"Top {top} form — {season} (last {window} matches)")
    table.add_column("Pos")
    table.add_column("Club")
    table.add_column("Pts")
    for i, (club, pts) in enumerate(rows, 1):
        table.add_row(str(i), club, str(int(pts)))
    rprint(table)


if __name__ == "__main__":
    typer.run(main)
