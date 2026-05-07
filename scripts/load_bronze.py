import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)

engine = create_engine(DB_URL)

csv_files = sorted(Path("data/raw/se16").rglob("*.csv"))

total_rows = 0

for i, path in enumerate(csv_files, start=1):
    table = path.stem.split("_")[0]
    df = pd.read_csv(path, dtype=str)
    df.columns = df.columns.str.lower()

    with engine.begin() as conn:
        conn.execute(text(f'TRUNCATE bronze."{table}"'))
        df.to_sql(table, conn, schema="bronze", if_exists="append", index=False, chunksize=1000)

    total_rows += len(df)
    print(f"[{i}/{len(csv_files)}] {table}: {len(df)} rows ✓")

print(f"\nTotal: {total_rows:,} rows loaded.")
