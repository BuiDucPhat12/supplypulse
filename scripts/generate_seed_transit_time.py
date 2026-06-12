"""Generate seed_transit_time.csv — thay thế SAP custom table rb04.

Grain: 1 vendor (lifnr) x 1 plant (werks) = 50 x 4 = 200 rows.
Transit time = base theo country + offset nhỏ theo plant (deterministic,
không random — chạy lại luôn ra cùng kết quả).
"""

import csv
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LFA1_CSV = sorted((PROJECT_ROOT / "data" / "raw" / "se16" / "LFA1").glob("LFA1_*.csv"))[-1]
OUT_CSV = PROJECT_ROOT / "supplypulse_dbt" / "seeds" / "seed_transit_time.csv"

EKORG = "1000"
PLANTS = ["1000", "1001", "1002", "1003"]

# Calendar days, theo khoảng cách địa lý từ plant network (Đức)
BASE_TT_BY_COUNTRY = {"DE": 3, "AT": 4, "CH": 5, "JP": 21, "CN": 28}
PLANT_OFFSET = {"1000": 0, "1001": 1, "1002": 2, "1003": 1}


def main() -> None:
    lfa1 = pd.read_csv(LFA1_CSV, dtype=str)
    vendors = lfa1[["LIFNR", "LAND1"]].drop_duplicates().sort_values("LIFNR")

    rows = []
    for _, v in vendors.iterrows():
        base = BASE_TT_BY_COUNTRY[v["LAND1"]]
        for plant in PLANTS:
            rows.append(
                {
                    "lifnr": v["LIFNR"],
                    "ekorg": EKORG,
                    "werks": plant,
                    "transit_time_days": base + PLANT_OFFSET[plant],
                }
            )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["lifnr", "ekorg", "werks", "transit_time_days"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done. {len(rows)} rows -> {OUT_CSV.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
