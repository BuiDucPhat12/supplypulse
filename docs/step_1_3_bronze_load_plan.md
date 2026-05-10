# Step 1.3 — Bronze Layer: Load CSV → Postgres

## Context

Step 1.2 đã tạo 22 CSV synthetic (114,615 rows) tại `data/raw/se16/<TABLE>/<TABLE>_20241231.csv`.
Step 1.3 đưa các CSV đó vào Postgres như Bronze layer — raw ingest, không transform, không clean.

**Mục tiêu:** Có 1 Postgres chạy local (Docker), 22 bảng trong schema `bronze`, loader idempotent.

---

## Files sẽ tạo mới

```
supplypulse/
├── docker-compose.yml              # Postgres 15 container + volume
├── .env.example                    # Template credentials (commit)
├── .env                            # Actual credentials (gitignored)
├── sql/
│   └── bronze/
│       └── create_tables.sql       # DDL 22 bảng trong schema bronze
├── scripts/
│   └── load_bronze.py              # Idempotent loader CSV → Postgres
└── tests/
    └── test_bronze_load.py         # Row count assertions
```

---

## Chi tiết từng file

### 1. `docker-compose.yml`

- Image: `postgres:15-alpine`
- Named volume: `pgdata` — data persist khi container restart/rm
- Port: `5432:5432`
- Credentials đọc từ `.env`: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB=supplypulse`

### 2. `.env.example` + `.env`

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=supplypulse
POSTGRES_USER=supplypulse
POSTGRES_PASSWORD=supplypulse123
```

`.env` được gitignore (đã có rule `*.env` trong `.gitignore`).

### 3. `sql/bronze/create_tables.sql`

- `CREATE SCHEMA IF NOT EXISTS bronze;`
- 22 bảng: `bronze."VBAK"`, `bronze."VBAP"`, ...
- **Tất cả cột dùng `TEXT`** — Bronze = raw 100%, không ép kiểu, tránh load error nếu CSV có giá trị bẩn
- DDL idempotent: `DROP TABLE IF EXISTS ... CASCADE` trước `CREATE TABLE`

### 4. `scripts/load_bronze.py`

- Stack: `SQLAlchemy 2.0` + `psycopg2-binary` + `pandas` (đã có) + `python-dotenv`
- Với mỗi table:
  1. `TRUNCATE bronze."<TABLE>"` — xoá data cũ (idempotent)
  2. `pd.read_csv(...)` với `dtype=str` — giữ nguyên raw string
  3. `df.to_sql(...)` vào schema `bronze`, `if_exists='append'`, `chunksize=1000`
- Output: `[1/22] VBAK: 6000 rows ✓` cho mỗi bảng

### 5. `tests/test_bronze_load.py`

- `pytest` + SQLAlchemy connect Postgres
- 22 test cases: assert `COUNT(*)` mỗi bảng khớp expected (đọc từ CSV)
- Skip toàn bộ nếu Postgres không chạy

---

## Dependencies cần thêm

```toml
# pyproject.toml
sqlalchemy>=2.0
psycopg2-binary>=2.9
python-dotenv>=1.0
```

---

## Sequence thực hiện

| # | Việc làm | Command |
|---|---|---|
| 1 | Thêm deps | `uv add sqlalchemy psycopg2-binary python-dotenv` |
| 2 | Tạo `.env.example` + `.env` | — |
| 3 | Tạo `docker-compose.yml` | — |
| 4 | Tạo `sql/bronze/create_tables.sql` | — |
| 5 | Tạo `scripts/load_bronze.py` | — |
| 6 | Tạo `tests/test_bronze_load.py` | — |
| 7 | Spin up Postgres | `docker compose up -d` |
| 8 | Chạy DDL | `docker exec ... psql ... < sql/bronze/create_tables.sql` |
| 9 | Chạy loader | `python scripts/load_bronze.py` |
| 10 | Chạy tests | `pytest tests/test_bronze_load.py -v` |
| 11 | Commit | `git add ... && git commit` |

---

## Verification

```powershell
# Postgres đang chạy
docker compose ps

# Loader output mong đợi
# [1/22] VBAK: 6000 rows ✓
# ...
# [22/22] TFACT: 50 rows ✓
# Total: 114,615 rows loaded.

# Tests pass
pytest tests/test_bronze_load.py -v
# 22 passed

# Spot check
docker exec -it supplypulse-postgres-1 psql -U supplypulse -d supplypulse \
  -c 'SELECT COUNT(*) FROM bronze."VBAK";'
# count = 6000
```

---

## Quyết định thiết kế

| Quyết định | Lựa chọn | Lý do |
|---|---|---|
| Postgres schema | `bronze` (không phải `public`) | Tách biệt với silver/gold sau này |
| Data types Bronze | Tất cả `TEXT` | Raw = không ép kiểu, load không fail |
| Loader library | SQLAlchemy + pandas to_sql | pandas đã có, SQLAlchemy là standard stack |
| Idempotent pattern | TRUNCATE + re-insert | Chạy lại bất kỳ lúc nào, kết quả như nhau |
| Credentials | `.env` + `python-dotenv` | Không hardcode, gitignored |

---

## Hướng dẫn từng bước

### Bước 1 — Kiểm tra Postgres đang chạy

```powershell
docker compose ps
```

Nếu container chưa up: `docker compose up -d`, chờ ~5 giây rồi kiểm tra lại.

> **Tại sao làm trước?** DDL và loader đều cần Postgres. Fail sớm tốt hơn fail giữa chừng.

---

### Bước 2 — Lấy danh sách cột từ CSV

Chạy lệnh Python một dòng để in ra tên bảng và danh sách cột:

```powershell
python -c "
import pandas as pd
from pathlib import Path
for f in sorted(Path('data/raw/se16').rglob('*.csv')):
    cols = pd.read_csv(f, nrows=0).columns.tolist()
    print(f.stem.split('_')[0], cols)
"
```

Copy output — đây là input để viết DDL ở Bước 3.

---

### Bước 3 — Viết `sql/bronze/create_tables.sql`

Cấu trúc file:

```sql
CREATE SCHEMA IF NOT EXISTS bronze;

DROP TABLE IF EXISTS bronze."VBAK" CASCADE;
CREATE TABLE bronze."VBAK" (
    MANDT TEXT,
    VBELN TEXT,
    -- ... các cột còn lại từ output Bước 2
);

-- lặp lại cho 20 bảng còn lại
```

**Quy tắc:**
- Dùng `DROP TABLE IF EXISTS ... CASCADE` trước mỗi `CREATE TABLE` → idempotent
- **Tất cả cột là `TEXT`** — không dùng `DATE`, `INTEGER`, `NUMERIC`
- Tên bảng dùng double-quote để giữ nguyên chữ hoa: `bronze."VBAK"`

**Verify:** Đếm số `CREATE TABLE` trong file — phải đúng 21.

> **Tại sao tất cả TEXT?** Bronze = raw. Nếu ép kiểu và CSV có giá trị bẩn, loader fail. TEXT không bao giờ fail. Ép kiểu đúng là việc của Silver layer.

---

### Bước 4 — Apply DDL vào Postgres

```powershell
docker exec -i $(docker compose ps -q postgres) psql -U supplypulse -d supplypulse < sql/bronze/create_tables.sql
```

Verify có đủ 21 bảng:

```powershell
docker exec -it $(docker compose ps -q postgres) psql -U supplypulse -d supplypulse -c "\dt bronze.*"
```

---

### Bước 5 — Viết `scripts/load_bronze.py`

Logic theo thứ tự:

1. **Load env** — dùng `python-dotenv`, tạo connection string:
   ```
   postgresql+psycopg2://<user>:<password>@<host>:<port>/<db>
   ```

2. **Tìm CSV** — `Path('data/raw/se16').rglob('*.csv')`, extract tên bảng từ filename:
   ```
   VBAK_20241231.csv → "VBAK"
   ```

3. **Với mỗi bảng:**
   - `TRUNCATE bronze."<TABLE>"` — xoá data cũ
   - `pd.read_csv(path, dtype=str)` — đọc CSV, giữ nguyên string
   - `df.to_sql(table, engine, schema='bronze', if_exists='append', index=False, chunksize=1000)`
   - Print: `[1/21] VBAK: 6000 rows ✓`

4. **Cuối** — print tổng rows.

**Key patterns:**
- `dtype=str` trong `read_csv` — không parse date/number tự động
- `if_exists='append'` — KHÔNG dùng `'replace'` (replace sẽ drop bảng, mất DDL TEXT bạn đã viết)
- SQLAlchemy 2.0: dùng `with engine.begin() as conn: conn.execute(text(...))` — không dùng `engine.execute()` (deprecated)

---

### Bước 6 — Chạy loader

```powershell
python scripts/load_bronze.py
```

Expected output:
```
[1/21] VBAK: 6000 rows ✓
[2/21] VBAP: 18000 rows ✓
...
[21/21] TFACT: 50 rows ✓
Total: 114,615 rows loaded.
```

---

### Bước 7 — Viết `tests/test_bronze_load.py`

Cấu trúc:

1. **Fixture `engine`** (scope=session): kết nối Postgres, `pytest.skip` toàn bộ nếu không connect được:
   ```python
   from sqlalchemy.exc import OperationalError
   try:
       with eng.connect() as conn:
           conn.execute(text("SELECT 1"))
   except OperationalError:
       pytest.skip("Postgres not running")
   ```

2. **21 test functions** — mỗi bảng 1 test:
   - Đọc CSV, đếm rows
   - `SELECT COUNT(*) FROM bronze."<TABLE>"`
   - Assert hai số bằng nhau

---

### Bước 8 — Chạy tests và commit

```powershell
pytest tests/test_bronze_load.py -v
# Expected: 21 passed
```

Commit:
```powershell
git add sql/bronze/create_tables.sql scripts/load_bronze.py tests/test_bronze_load.py
git commit -m "feat: load 21 synthetic CSV tables into bronze schema (Step 1.3)"
```

---

## Self-check trước khi sang Step 1.4

| # | Câu hỏi |
|---|---|
| Q1 | Tại sao Bronze dùng tất cả `TEXT`, không phải kiểu đúng của từng cột? |
| Q2 | `if_exists='append'` vs `if_exists='replace'` — sự khác biệt là gì? |
| Q3 | Nếu chạy `load_bronze.py` hai lần, data có bị nhân đôi không? Tại sao? |
| Q4 | SQLAlchemy 2.0 bỏ `engine.execute()` — thay bằng gì và tại sao? |
