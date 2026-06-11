# dbt Tests — Hướng dẫn cho SupplyPulse

> Mục tiêu: hiểu 2 loại test, cách khai báo, và apply vào pipeline.

---

## 1. Hai loại test trong dbt

### Generic tests (khai báo trong `.yml`)

Định nghĩa sẵn trong dbt core — chỉ cần khai báo tên, không cần viết SQL.

| Test | Ý nghĩa | Fail khi |
|------|---------|---------|
| `unique` | Không có 2 row cùng giá trị | Có duplicate |
| `not_null` | Không có NULL | Có NULL |
| `accepted_values` | Chỉ có các giá trị cho phép | Có giá trị ngoài list |
| `relationships` | FK tồn tại ở bảng tham chiếu | Có orphan row |

Khai báo trong file `schema.yml` cùng folder với model:

```yaml
models:
  - name: stg_marc
    columns:
      - name: marc_id
        tests:
          - unique
          - not_null
      - name: procurement_type
        tests:
          - accepted_values:
              values: ['F', 'E', 'X']
```

---

### Singular tests (viết SQL trong `tests/` folder)

Test business logic phức tạp mà generic không cover được.
**Quy tắc:** Query trả về **0 rows = pass**, **> 0 rows = fail**.

Ví dụ: kiểm tra `available_stock` không bao giờ âm:

```sql
-- tests/assert_available_stock_not_negative.sql
SELECT marc_id, available_stock
FROM {{ ref('int_pn_infor') }}
WHERE available_stock < 0
```

Nếu có row nào `available_stock < 0` → test fail.

---

## 2. Cách chạy

```bash
dbt test                              # tất cả tests
dbt test --select stg_marc            # chỉ tests của 1 model
dbt test --select staging             # cả layer staging
dbt test --select +mart_shortage_report  # model + tất cả upstream
```

---

## 3. Cấu trúc file `.yml`

Mỗi layer nên có 1 file `schema.yml` riêng:

```
models/
  staging/
    schema.yml        ← tests cho staging models
  intermediate/
    schema.yml        ← tests cho intermediate models
  marts/
    schema.yml        ← tests cho marts
tests/
    assert_*.sql      ← singular tests (business logic)
```

Cấu trúc đầy đủ của 1 `schema.yml`:

```yaml
version: 2

models:
  - name: tên_model
    description: "mô tả ngắn"
    columns:
      - name: tên_cột
        description: "mô tả cột"
        tests:
          - unique
          - not_null
          - accepted_values:
              values: ['A', 'B', 'C']
          - relationships:
              to: ref('bảng_tham_chiếu')
              field: tên_cột_tham_chiếu
```

---

## 4. Tests nên có trong SupplyPulse

### Staging layer — kiểm tra raw data quality

| Model | Column | Tests |
|-------|--------|-------|
| `stg_marc` | `marc_id` | unique, not_null |
| `stg_marc` | `procurement_type` | accepted_values: ['F','E','X'] |
| `stg_ekko` | `po_number` | unique, not_null |
| `stg_ekpo` | `ekpo_id` | unique, not_null |
| `stg_ekpo` | `marc_id` | not_null |
| `stg_vbup` | `goods_movement_status` | accepted_values: ['A','B','C'] |
| `stg_likp` | `delivery_id` | unique, not_null |

### Intermediate layer — kiểm tra business logic

| Model | Column | Tests |
|-------|--------|-------|
| `int_pn_infor` | `marc_id` | unique, not_null |
| `int_pn_infor` | `available_stock` | not_null ← sau fix gen_ekpo |
| `int_factory_calendar` | `plant` + `calendar_date` | unique (composite) |
| `int_working_calendar` | `plant` + `calendar_date` | unique (composite) |
| `int_inbound_deliveries_asn` | `asn_status` | accepted_values: ['future','overdue','pending'] |
| `int_tt_quota` | `marc_id` + `vendor_number` | unique (composite) |

### Marts layer — kiểm tra output cuối

| Model | Column | Tests |
|-------|--------|-------|
| `mart_shortage_report` | `marc_id` | unique, not_null |
| `mart_shortage_report` | `status` | accepted_values: ['Shortage','No Shortage'] |
| `mart_inventory_simulation` | `marc_id` + `calendar_date` | unique (composite) |
| `mart_consumption` | `marc_id` + `consumption_date` | unique (composite) |

---

## 5. Unique composite key

dbt không có built-in composite unique test — cần dùng `dbt_utils` hoặc SQL expression.

**Cách đơn giản nhất** — test trên concatenated key:

```yaml
- name: marc_id
  tests:
    - unique:
        name: unique_marc_id_calendar_date
    # Không work cho composite — dùng cách dưới
```

**Cách đúng** — dùng `dbt_utils.unique_combination_of_columns`:

Thêm package vào `packages.yml`:

```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: 1.3.0
```

Rồi khai báo test:

```yaml
models:
  - name: mart_inventory_simulation
    tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - marc_id
            - calendar_date
```

---

## 6. Singular test mẫu cho SupplyPulse

**Kiểm tra simulated_inventory_qty không NULL:**
```sql
-- tests/assert_simulation_no_null_qty.sql
SELECT marc_id, calendar_date
FROM {{ ref('mart_inventory_simulation') }}
WHERE simulated_inventory_qty IS NULL
```

**Kiểm tra red_days không âm:**
```sql
-- tests/assert_shortage_red_days_not_negative.sql
SELECT marc_id, red_days
FROM {{ ref('mart_shortage_report') }}
WHERE red_days < 0
```

**Kiểm tra max_tt >= 0:**
```sql
-- tests/assert_tt_quota_max_tt_not_negative.sql
SELECT marc_id, vendor_number, max_tt
FROM {{ ref('int_tt_quota') }}
WHERE max_tt < 0
```

---

## 7. Self-check sau khi đọc

1. Generic test `relationships` dùng để kiểm tra điều gì? Cho ví dụ trong SupplyPulse.
2. Tại sao singular test fail khi trả về > 0 rows, không phải khi trả về 0 rows?
3. `int_factory_calendar` có grain là `plant × calendar_date` — test unique cho composite key thì viết yaml như nào?
