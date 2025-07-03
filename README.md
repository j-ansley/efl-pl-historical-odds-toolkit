efl-pl historical odds toolkit
==============================

small cli toolkit for Premier League and English Football League Data  
(csvs ⟶ duckdb, rolling form tables, promotion / relegation sims)

--------------------------------------------------
quick demo
--------------------------------------------------

python -m footy.cli 2024 --leagues epl,ch,l1,l2
python -m footy.form 2024 --leagues epl
python -m footy.odds relegate 2024 --leagues epl --date 2024-02-01 --sims 3000

--------------------------------------------------
setup
--------------------------------------------------

git clone https://github.com/j-ansley/efl-pl-historical-odds-toolkit
cd efl-pl-historical-odds-toolkit
python -m venv .venv
source .venv/bin/activate        # windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .

--------------------------------------------------
how it works
--------------------------------------------------

* **footy.cli**   download csvs → create / overwrite `data/footy.duckdb`
* **footy.form**  filter one season, roll last-N matches, sum points
* **footy.odds**  poisson attack/defence, monte-carlo remaining fixtures

--------------------------------------------------
nice-to-have
--------------------------------------------------

* playoff odds simulation  
* pytest + github actions  
* optional `--db` flag for multi-season side-by-side

--------------------------------------------------
references
--------------------------------------------------

* football-data csvs – https://www.football-data.co.uk/  
* soccermatics poisson demo – https://soccermatics.readthedocs.io/en/latest/  
* ad-hoc sql server (duckdb) – https://duckdb.org/

--------------------------------------------------
contact
--------------------------------------------------
linkedin – https://www.linkedin.com/in/jack-ansley-4aa98a171/
