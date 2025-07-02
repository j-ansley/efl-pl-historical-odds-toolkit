"""
footy/form.py
-------------
rolling n-match form table pulled from duckdb

examples
--------
python -m footy.form 2024 --top 12                    #epl, 5-match window
python -m footy.form 2024 --window 10 --leagues l2    #league two, 10-match
python -m footy.form 2005 --leagues ch,l1             #retro champ + l1
"""

from pathlib import Path
from typing import List, Tuple

import duckdb
import pandas as pd
import typer
from rich import print as rprint
from rich.table import Table
import warnings

#silence pandas “could not infer format” chatter
warnings.filterwarnings(
    "ignore",
    message="Could not infer format, so each element will be parsed individually",
    category=UserWarning,
)

app = typer.Typer(help="show rolling-form tables")

#map nicer league codes to football-data div codes
DIV_CODE = {"EPL": "E0", "CH": "E1", "L1": "E2", "L2": "E3"}

#------------------------------------------------------------------
#helpers
#------------------------------------------------------------------
def season_dataframe(db: Path, league: str, season_end: int) -> pd.DataFrame:
    #return tidy df -> match_date | club | pts for chosen league+season
    season_start = f"{season_end-1}-07-01"
    season_finish = f"{season_end}-06-30"

    con = duckdb.connect(db, read_only=True)
    raw = con.execute(
        """
        select distinct
               Date,        --keep original case so pandas cols are 'Date'
               HomeTeam,
               AwayTeam,
               FTR
        from   results
        where  Div = ?
        """,
        [DIV_CODE[league]],
    ).fetchdf()

    #parse date (pandas deals with dd/mm/yy and dd/mm/yyyy)
    raw["match_date"] = pd.to_datetime(
        raw["Date"].str.strip(), dayfirst=True, errors="coerce"
    )

    #put each match into two rows with points already attached
    pts_map = {"H": (3, 0), "D": (1, 1), "A": (0, 3)}
    rows: List[Tuple] = []
    for _, row in raw.iterrows():
        home_pts, away_pts = pts_map[row["FTR"]]
        rows.append((row["match_date"], row["HomeTeam"], home_pts))
        rows.append((row["match_date"], row["AwayTeam"], away_pts))

    tidy_df = pd.DataFrame(rows, columns=["match_date", "club", "pts"])
    mask = tidy_df["match_date"].between(season_start, season_finish)
    tidy = (
        tidy_df.loc[mask]
        .sort_values("match_date")
        .reset_index(drop=True)
    )
    return tidy


def rolling_form(tidy: pd.DataFrame, window: int, table_size: int) -> pd.DataFrame:
    #take last n rows per club then sum pts
    last_chunk = tidy.groupby("club").tail(window)
    sums = (
        last_chunk.groupby("club")["pts"]
        .sum()
        .sort_values(ascending=False)
        .head(table_size)
    )
    return sums.reset_index()


def print_table(title: str, rows: pd.DataFrame) -> None:
    table = Table(title=title)
    table.add_column("pos", justify="right")
    table.add_column("club")
    table.add_column("pts", justify="right")
    for idx, (club, pts) in enumerate(rows.itertuples(index=False), start=1):
        table.add_row(str(idx), club, str(int(pts)))
    rprint(table)

@app.command()
def main(
    season: int = typer.Argument(..., help="season end year, e.g. 2024"),
    top: int = typer.Option(10, help="rows to show"),
    window: int = typer.Option(5, help="rolling-match window"),
    leagues: str = typer.Option("EPL", help="comma list epl,ch,l1,l2"),
):
    db = Path("data/footy.duckdb")

    for lg in [code.strip().upper() for code in leagues.split(",")]:
        tidy = season_dataframe(db, lg, season)
        rows = rolling_form(tidy, window, top)
        print_table(f"{lg} form — {season} (last {window})", rows)


if __name__ == "__main__":
    app()
