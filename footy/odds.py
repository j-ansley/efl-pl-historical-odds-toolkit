"""
promotion and relegation odds calculations based on my own info and info found in https://soccermatics.readthedocs.io/en/latest/
references
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Dict, List

import duckdb
import numpy as np
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

app = typer.Typer(help="promotion / relegation odds cli")

# league constants so we can use their preferred shorthand instead of the boring E1, E2, etc.
DIV_CODE   = {"EPL": "E0", "CH": "E1", "L1": "E2", "L2": "E3"}
MAX_GAMES  = {"EPL": 38,  "CH": 46,  "L1": 46,  "L2": 46}
RELEG_SLOTS = {"EPL": 3,  "CH": 3,  "L1": 4,  "L2": 2}
PROMO_SLOTS = {"EPL": 0,  "CH": 2,  "L1": 2,  "L2": 2}

def season_dataframe(db_path: Path, league: str, season_end: int) -> pd.DataFrame:
    #return dataframe for one league + season
    # these dates are what we consider the start and and of the season.
    season_start = f"{season_end-1}-07-01"
    season_finish = f"{season_end}-06-30"

    con = duckdb.connect(db_path, read_only=True)
    df = con.execute(
        """
        SELECT Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR
        FROM results
        WHERE Div = ?
        """,
        [DIV_CODE[league]],
    ).fetchdf()

    #returned dataframe columns
    #date        -> original date string  dd/mm/yy or dd/mm/yyyy
    #hometeam    -> club at home
    #awayteam    -> club away
    #fthg        -> full-time home goals  (int)
    #ftag        -> full-time away goals  (int)
    #ftr         -> full-time result 'H' home win, 'D' draw, 'A' away win
    #match_date  -> pandas datetime64 version of date (already dayfirst-parsed)
    #rows are limited to the season window 1 jul (prev yr) … 30 jun (season_end)
    df["match_date"] = pd.to_datetime(df["Date"].str.strip(), dayfirst=True, errors="coerce")
    return df[df["match_date"].between(season_start, season_finish)].reset_index(drop=True)

    #format:
    #date     -> match day ("14/08/04") or ("22/11/2024")
    #hometeam -> club name at home
    #awayteam -> club name away
    #fthg     -> full-time home goals (int)
    #ftag     -> full-time away goals (int)
    #ftr      -> full-time result: 'H' (home win), 'D' (draw), 'A' (away win)
def poisson_parameters(matches: pd.DataFrame) -> pd.DataFrame:
    #compute attack / defence strengths (soccermatics style)
    league_avg_home = matches["FTHG"].mean()
    league_avg_away = matches["FTAG"].mean()

    attack_factor = (
        matches.groupby("HomeTeam")["FTHG"]
        .mean()
        .div(league_avg_home)
        .rename("atk")
    )
    defence_factor = (
        matches.groupby("AwayTeam")["FTAG"]
        .mean()
        .div(league_avg_away)
        .rename("def")
    )
    return pd.concat([attack_factor, defence_factor], axis=1).fillna(1.0)

#simulate rest of season
def simulate_rest_of_season(
    current_points: pd.Series,
    remaining_fixtures: List[tuple[str, str]],
    strength_table: pd.DataFrame,
    league_avg_home: float,
    league_avg_away: float,
) -> pd.Series:
    #points for all games that have already been played
    points = current_points.copy()

    #For each of the remaining matchups, calculate a 'lambda' to represent their expected 'strength' against each other
    # this is meant to be a representation of how the two teams stack up (Think Madden or Fifa Ratings). Then it will be
    # fed into the poisson algorithm to simulate roughly how the game would go. Then add to either the home or away clubs
    # point totals. (Or both in case of a draw)
    for home_club, away_club in remaining_fixtures:
        lambda_home = (
            league_avg_home
            * strength_table.at[home_club, "atk"]
            * strength_table.at[away_club, "def"]
        )
        lambda_away = (
            league_avg_away
            * strength_table.at[away_club, "atk"]
            * strength_table.at[home_club, "def"]
        )

        home_goals = np.random.poisson(lambda_home)
        away_goals = np.random.poisson(lambda_away)

        if home_goals > away_goals:
            points[home_club] += 3
        elif home_goals < away_goals:
            points[away_club] += 3
        else:
            points[home_club] += 1
            points[away_club] += 1

    return points

# monte-carlo wrapper that spits out {club: chance%}
def odds_probability_table(
    league: str,
    season_end: int,
    snapshot: str | None,
    num_sims: int,
) -> Dict[str, float]:
    db_file = Path("data/footy.duckdb")
    season_df = season_dataframe(db_file, league, season_end)

    snapshot_date = snapshot or datetime.today().strftime("%Y-%m-%d")
    played_mask = season_df["match_date"] <= snapshot_date
    played_df = season_df.loc[played_mask]
    remaining_df = season_df.loc[~played_mask]

    #points so far
    point_lookup = {"H": (3, 0), "D": (1, 1), "A": (0, 3)}
    pts_rows: list[tuple[str, int]] = []
    for _, row in played_df.iterrows():
        pts_home, pts_away = point_lookup[row["FTR"]]
        pts_rows.append((row["HomeTeam"], pts_home))
        pts_rows.append((row["AwayTeam"], pts_away))

    points_so_far = (
        pd.DataFrame(pts_rows, columns=["club", "pts"])
        .groupby("club")["pts"]
        .sum()
        .reindex(season_df["HomeTeam"].unique(), fill_value=0)
    )

    #poisson attack/defence factors
    strength_df = poisson_parameters(played_df if not played_df.empty else season_df)

    avg_home_goals = played_df["FTHG"].mean() or season_df["FTHG"].mean()
    avg_away_goals = played_df["FTAG"].mean() or season_df["FTAG"].mean()

    remaining_fixtures = list(zip(remaining_df["HomeTeam"], remaining_df["AwayTeam"]))

    tally: Dict[str, int] = {club: 0 for club in points_so_far.index}

    for _ in range(num_sims):
        final_pts = (
            simulate_rest_of_season(
                points_so_far,
                remaining_fixtures,
                strength_df,
                avg_home_goals,
                avg_away_goals,
            )
            .sort_values(ascending=False)
        )

        #promotion slots
        for club in final_pts.head(PROMO_SLOTS[league]).index:
            tally[club] += 1

        #relegation slots
        for club in final_pts.tail(RELEG_SLOTS[league]).index:
            tally[club] += 1

    return {club: round(100 * count / num_sims, 1) for club, count in tally.items()}

#print helper
def print_rich_table(title: str, probability: Dict[str, float]):
    table = Table(title=title)
    table.add_column("club")
    table.add_column("chance %", justify="right")
    for club, pct in sorted(probability.items(), key=lambda x: -x[1]):
        if pct > 0:
            table.add_row(club, f"{pct}")
    rprint(table)

#cli commands
@app.command()
def promote(
    season: int = typer.Argument(..., help="season end year, e.g. 2024"),
    leagues: str = typer.Option("CH,L1,L2", help="comma list"),
    date: str = typer.Option(None, help="snapshot YYYY-MM-DD (default today)"),
    sims: int = typer.Option(5000, help="monte-carlo runs"),
):
    for league_code in [code.strip().upper() for code in leagues.split(",")]:
        probs = odds_probability_table(league_code, season, date, sims)
        print_rich_table(f"{league_code} promotion odds — {season}", probs)

@app.command()
def relegate(
    season: int = typer.Argument(..., help="season end year, e.g. 2024"),
    leagues: str = typer.Option("EPL,CH,L1,L2", help="comma list"),
    date: str = typer.Option(None, help="snapshot YYYY-MM-DD (default today)"),
    sims: int = typer.Option(5000, help="monte-carlo runs"),
):
    for league_code in [code.strip().upper() for code in leagues.split(",")]:
        probs = odds_probability_table(league_code, season, date, sims)
        print_rich_table(f"{league_code} relegation odds — {season}", probs)

#allow: python -m footy.odds promote ...
if __name__ == "__main__":
    app()
