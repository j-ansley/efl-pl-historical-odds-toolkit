# efl-pl historical odds toolkit

small cli toolkit for Premier League and English Football League data  
(csvs → duckdb, rolling form tables, promotion / relegation sims)

---

## quick demo

```bash
python -m footy.cli 2024 --leagues epl,ch,l1,l2
python -m footy.form 2024 --leagues epl
python -m footy.odds relegate 2024 --leagues epl --date 2024-02-01 --sims 3000
```

---

## setup

```bash
git clone https://github.com/j-ansley/efl-pl-historical-odds-toolkit
cd efl-pl-historical-odds-toolkit
python -m venv .venv

# on mac/linux
source .venv/bin/activate

# on Windows
.venv\Scripts\activate

pip install -r requirements.txt
pip install -e .
```

---

## how it works

- **footy.cli**: download CSVs → populate/overwrite `data/footy.duckdb`  
- **footy.form**: filter one season, roll last-N matches, sum points  
- **footy.odds**: Poisson attack/defence, Monte-Carlo remaining fixtures  

---

## examples

```bash
python -m footy.cli 2023 --leagues EPL,CH
python -m footy.form 2023 --top 10 --window 5
python -m footy.odds promote 2023 --leagues CH --date 2023-02-01 --sims 2000
```

---

## nice-to-have

- playoff odds simulation

---

## ad-hoc SQL server

see DuckDB → https://duckdb.org/

---

## contact

Jack Ansley — https://www.linkedin.com/in/jack-ansley-4aa98a171/
