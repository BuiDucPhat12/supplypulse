# dbt — Key Concepts

## dbt là gì?

Transform data bằng SQL. Vị trí trong pipeline:
```
Bronze (raw) → [dbt] → Silver (staging) → Gold (marts)
```

## dbt vs Spark

| | dbt | Spark |
|--|--|--|
| Làm gì | Transform bằng SQL trong database | Xử lý data lớn phân tán |
| Chạy ở đâu | Trong database (Postgres, BigQuery...) | Cluster riêng |
| Scale | Giới hạn bởi database | Petabyte-scale |
| Dùng khi | Transform, modeling, mart | ETL khổng lồ, ML pipeline |

## 3 khái niệm cốt lõi

| Khái niệm | Ý nghĩa |
|-----------|---------|
| **Model** | 1 file `.sql` = 1 bảng/view trong database |
| **`ref()`** | Tham chiếu model khác → dbt tự build DAG dependency |
| **`source()`** | Tham chiếu bảng raw (Bronze) → dbt track lineage |
| **Materialization** | `view` / `table` / `incremental` / `ephemeral` |

## `ref()` vs `source()`

- `{{ source('bronze', 'VBAK') }}` — trỏ vào bảng Bronze (nguồn raw)
- `{{ ref('stg_vbak') }}` — trỏ vào model dbt khác (staging/mart)

## Cấu trúc project

```
supplypulse_dbt/
├── models/
│   ├── staging/        ← rename SAP fields → tên đọc được
│   │   ├── sources.yml ← khai báo Bronze tables
│   │   └── stg_vbak.sql
│   └── marts/          ← business logic, aggregation
├── dbt_project.yml     ← config chính
└── profiles.yml        ← connection (lưu ở C:\Users\Admin\.dbt\)
```

## Pattern staging model chuẩn

```sql
with source as (
    select * from {{ source('bronze', 'VBAK') }}
),

renamed as (
    select
        vbeln as sales_order_id,
        erdat as created_date,
        ...
    from source
)

select * from renamed
```

**Quy tắc:**
- Bỏ `MANDT` — không có business value
- Rename theo Silver name (sap_source_design.md)
- Giữ TEXT, chưa cast — cast ở mart layer
- Dùng `source()` không hardcode tên bảng

## threads

Số query dbt chạy song song. Mặc định 4 cho local dev.

## Dependency conflict — dbt-core vs black

- `dbt-core==1.9.4` cần `pathspec>=0.9,<0.13`
- `black>=26.1.0` cần `pathspec>=1.0.0` → conflict
- Fix: dùng `black==25.12.0` (version cuối cùng tương thích)

## Chạy dbt

Phải cd vào folder `supplypulse_dbt/` trước:
```powershell
cd supplypulse_dbt
uv run dbt debug    # test connection
uv run dbt run      # build models
uv run dbt test     # chạy tests
uv run dbt docs serve  # xem lineage graph
```

---

## Config dbt — profiles.yml vs dbt_project.yml

| File | Vai trò | Lưu ở đâu |
|------|---------|-----------|
| `profiles.yml` | Kết nối database (host, user, pass, schema default) | `C:\Users\Admin\.dbt\` — ngoài repo, không commit |
| `dbt_project.yml` | Config project: folder structure, materialization, schema per layer | Trong repo, commit được |

**`schema` trong profiles.yml** = schema dbt ghi output nếu model không có config override. Không được để là `bronze` vì bronze là raw layer — dbt chỉ đọc bronze, không ghi vào đó.

---

## Layer architecture trong Postgres

```
Bronze   ← Python loader ghi vào (load_bronze.py). dbt chỉ ĐỌC qua source()
Staging  ← dbt tạo (views). Rename + cast, không có logic nặng
Analytics ← dbt tạo (tables). Business logic, aggregation, mart
```

dbt không quản lý bronze. `source()` là cách dbt khai báo "tôi đọc từ bảng này nhưng không tạo ra nó".

---

## Materialization: view vs table

| | View | Table |
|--|------|-------|
| Lưu trữ | Chỉ lưu câu SQL | Lưu rows vật lý trên disk |
| Khi query | Postgres chạy lại SQL từ đầu | Đọc rows đã tính sẵn |
| Dùng cho | Staging (trung gian, không ai query trực tiếp) | Marts (BI tools query nhiều lần) |
| Storage | Không tốn | Tốn disk |
| Freshness | Luôn fresh (recompute mỗi lần) | Chỉ fresh khi `dbt run` chạy lại |

**Nguyên tắc:** layer bị query nhiều bởi người dùng/tools → `table`. Layer chỉ là bước trung gian trong pipeline → `view`.

---

## Schema naming: folder name ≠ schema name

- `marts/` = tên folder trong code (tổ chức nội bộ của data team)
- `analytics` = tên schema trong Postgres (những gì analyst/BI nhìn thấy)

Tách biệt 2 khái niệm này: **folder name = cách bạn tổ chức code, schema name = cách người dùng cuối nhìn thấy data**.

---

## generate_schema_name macro (quan trọng)

**Vấn đề:** khi dbt_project.yml có `+schema: staging`, dbt mặc định tạo schema tên `staging_staging` (ghép `target.schema` + custom schema). Không phải `staging`.

**Fix:** override macro `generate_schema_name` trong `macros/` để trả về custom schema name trực tiếp.

```
macros/generate_schema_name.sql  ← override macro mặc định của dbt
```

Logic macro: nếu có `custom_schema_name` thì dùng nó, không thì dùng `target.schema`.

**⚠️ dbt docs cảnh báo:** không nên bỏ prefix `target.schema` trong môi trường team — mọi người sẽ ghi đè schema của nhau. Chỉ an toàn khi solo hoặc dùng `generate_schema_name_for_env` với target `prod`.

**Solo project → Option A (simple override):**
```sql
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
```

---

## dbt Environments (target)

**target** = 1 named config trong profiles.yml trỏ đến 1 database connection cụ thể.

```yaml
supplypulse_dbt:
  target: dev          # target active mặc định
  outputs:
    dev:
      schema: phat_dev # mỗi dev có schema riêng
    prod:
      schema: staging  # production dùng schema chung
```

- Chạy mặc định: `dbt run` → dùng target `dev`
- Chạy target khác: `dbt run --target prod`

| Environment | Mục đích | Schema |
|-------------|----------|--------|
| `dev` | Đang code, test local | `phat_staging`, `phat_analytics` (có prefix) |
| `prod` | CI/CD, pipeline thật | `staging`, `analytics` (không prefix) |

**Project solo:** chỉ cần 1 target. Tên `prod`/`dev` chỉ là label, không có magic — chỉ là điều kiện macro check.

---

## Jinja2 trong dbt

dbt dùng **Jinja2** (Python templating engine) để viết macro và SQL động.

**Syntax cơ bản:**

| Syntax | Dùng để |
|--------|---------|
| `{%- ... -%}` | Block logic (if, set, for) — không in ra output |
| `{{ ... }}` | In giá trị ra output |
| `{%- set x = value -%}` | Khai báo biến |

**Biến global dbt tự inject — không cần khai báo:**

| Biến | Lấy từ đâu | Ví dụ |
|------|-----------|-------|
| `target.schema` | `profiles.yml` → `schema:` | `"staging"` |
| `target.name` | `profiles.yml` → `target:` | `"dev"` |
| `target.host` | `profiles.yml` → `host:` | `"localhost"` |

Trong macro `generate_schema_name`: `custom_schema_name` là tham số dbt tự truyền vào — lấy từ `+schema:` trong `dbt_project.yml`.
