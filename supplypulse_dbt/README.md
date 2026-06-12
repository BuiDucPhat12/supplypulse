# supplypulse_dbt

The transformation layer of [SupplyPulse](../README.md): 17 staging views →
21 intermediate tables → 5 marts, plus 1 seed and 29 data tests (73 resources total).

```
bronze (raw TEXT)            -- loaded by scripts/load_bronze.py
  → staging   (views)        -- rename, cast, light cleaning, 1:1 with source tables
  → intermediate (tables)    -- planner logic: calendars, transit times, backlog,
                             --   ASN coverage, late shipments, supply reconstruction
  → analytics (marts)        -- shortage report, 120-day inventory simulation,
                             --   vendor performance, consumption, detail supply
```

Model-by-model documentation lives in [`../docs/DATA_LINEAGE.md`](../docs/DATA_LINEAGE.md).

## Usage

```bash
dbt deps                                               # install dbt_utils
dbt build --profiles-dir ../profiles --target local    # run + test everything
dbt test --select marts                                # just the mart tests
```

Targets: `local` (host machine / CI, connects to localhost) and `dev`
(default, used inside the Airflow containers where the host is `postgres`).
