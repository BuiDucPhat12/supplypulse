# Apache Airflow — Hướng dẫn cho SupplyPulse

> Mục tiêu: hiểu Airflow hoạt động như thế nào, tại sao dùng nó, và apply vào pipeline của SupplyPulse.

---

## 1. Airflow là gì và tại sao dùng

**Vấn đề không có Airflow:**
Bạn phải tự tay chạy theo thứ tự:
```
python generate_synthetic_data.py
python load_bronze.py
dbt build
```
Nếu `load_bronze.py` fail → `dbt build` vẫn chạy → data sai mà không biết.
Không có retry, không có log tập trung, không có schedule.

**Airflow giải quyết:**
- Định nghĩa thứ tự task bằng code (DAG)
- Tự retry khi fail
- Log từng task riêng biệt
- Chạy theo schedule (daily, hourly, v.v.)
- UI để monitor

---

## 2. Kiến trúc Airflow

Airflow gồm 3 thành phần chính:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Webserver     │     │    Scheduler    │     │  Metadata DB    │
│  (localhost:    │◄────│  (đọc DAG,      │────►│  (Postgres —    │
│   8080)         │     │   trigger task) │     │   lưu state)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

| Thành phần | Vai trò |
|-----------|---------|
| **Webserver** | UI để xem DAG, trigger thủ công, đọc log |
| **Scheduler** | Đọc DAG files, quyết định khi nào trigger task |
| **Metadata DB** | Lưu trạng thái mọi DAG run và task run (dùng Postgres) |
| **Worker** | Thực thi task (mặc định chạy trong scheduler — SequentialExecutor) |

---

## 3. Khái niệm cốt lõi

### DAG (Directed Acyclic Graph)
File Python định nghĩa pipeline: gồm các tasks và thứ tự chạy.
"Directed" = có chiều. "Acyclic" = không có vòng lặp.

```python
# daily_pipeline.py
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    dag_id='daily_pipeline',
    start_date=datetime(2024, 1, 1),
    schedule='@daily',
    catchup=False,
) as dag:
    ...
```

### Task
Một đơn vị công việc trong DAG. Mỗi task chạy độc lập, có state riêng (success/failed/skipped).

### Operator
Template để tạo task. Operator phổ biến:

| Operator | Dùng khi |
|----------|---------|
| `BashOperator` | Chạy shell command / script |
| `PythonOperator` | Gọi Python function trực tiếp |
| `EmptyOperator` | Placeholder (không làm gì) |

### Dependency (`>>`)
Ký hiệu `>>` định nghĩa thứ tự chạy:
```python
task_a >> task_b >> task_c
# task_a chạy trước, xong mới chạy task_b, xong mới chạy task_c
```

### Schedule
Cron expression hoặc preset:
| Preset | Ý nghĩa |
|--------|---------|
| `@daily` | Mỗi ngày lúc 00:00 UTC |
| `@hourly` | Mỗi giờ |
| `None` | Chỉ trigger thủ công |
| `'0 6 * * *'` | Mỗi ngày lúc 6:00 sáng (cron) |

---

## 4. DAG `daily_pipeline` của SupplyPulse

Pipeline cần chạy theo thứ tự:

```
generate_data >> load_bronze >> dbt_build >> notify
```

Nếu `load_bronze` fail → `dbt_build` không chạy → không có data sai trong warehouse.

```python
generate_data = BashOperator(
    task_id='generate_data',
    bash_command='python /opt/airflow/scripts/generate_synthetic_data.py',
)

load_bronze = BashOperator(
    task_id='load_bronze',
    bash_command='python /opt/airflow/scripts/load_bronze.py',
)

dbt_build = BashOperator(
    task_id='dbt_build',
    bash_command='cd /opt/airflow/supplypulse_dbt && dbt build',
)

notify = BashOperator(
    task_id='notify',
    bash_command='echo "Pipeline hoàn thành: $(date)"',
)

generate_data >> load_bronze >> dbt_build >> notify
```

---

## 5. Airflow trong Docker

SupplyPulse chạy Airflow qua Docker để nhất quán với Postgres.

Cần thêm 3 services vào `docker-compose.yaml`:

```
airflow-init      ← chạy 1 lần: tạo DB schema + admin user
airflow-webserver ← UI tại port 8080
airflow-scheduler ← đọc DAG và trigger task
```

Folder `dags/` trong project được **mount** vào container:
```yaml
volumes:
  - ./dags:/opt/airflow/dags
  - ./scripts:/opt/airflow/scripts
  - ./supplypulse_dbt:/opt/airflow/supplypulse_dbt
```

Khi bạn edit file DAG → scheduler tự pick up sau vài giây (không cần restart).

---

## 6. `catchup=False` — quan trọng

Mặc định Airflow **backfill** — tức là nếu DAG có `start_date=2024-01-01` và hôm nay là 2026-05-31, nó sẽ cố chạy **~900 lần** để catch up.

Với SupplyPulse dùng synthetic data → không cần backfill → luôn đặt `catchup=False`.

---

## 7. `start_date` vs `schedule_interval`

Một hiểu lầm phổ biến: DAG với `start_date=2024-01-01` và `schedule='@daily'` sẽ **không** chạy vào ngày 2024-01-01 mà chạy vào **2024-01-02** (sau khi interval đầu tiên kết thúc).

Airflow chạy DAG **sau** khi period kết thúc, không phải **đầu** period.

Ví dụ: `@daily` với `start_date=2024-01-01` → lần chạy đầu tiên = ngày 2024-01-02, đại diện cho ngày 2024-01-01.

---

## 8. Docker setup chi tiết — cách SupplyPulse dùng

### LocalExecutor vs SequentialExecutor

| | SequentialExecutor | LocalExecutor |
|---|---|---|
| Parallelism | Không (1 task tại 1 thời điểm) | Có (subprocess) |
| Metadata DB | SQLite (built-in) | Postgres/MySQL (bắt buộc) |
| Dùng khi | Demo nhanh, không cần parallel | Development có Postgres sẵn |

SupplyPulse dùng **LocalExecutor** vì đã có Postgres container — không cần thêm DB riêng.

### YAML anchor `x-airflow-common`

Ba services Airflow (init, webserver, scheduler) dùng chung config (image, env, volumes). YAML anchor tránh lặp:

```yaml
x-airflow-common: &airflow-common   # ← định nghĩa anchor, phải ở top-level
  image: apache/airflow:2.9.3
  environment: ...
  volumes: ...

services:
  airflow-webserver:
    <<: *airflow-common             # ← merge toàn bộ config từ anchor
    command: webserver
    ports:
      - "8080:8080"
```

`x-` prefix là convention Docker Compose — các key bắt đầu bằng `x-` bị bỏ qua khi parse services, nhưng YAML anchor vẫn hoạt động.

### `_PIP_ADDITIONAL_REQUIREMENTS`

Biến env đặc biệt của Airflow Docker image: tự động `pip install` khi container khởi động.

```yaml
_PIP_ADDITIONAL_REQUIREMENTS: "dbt-postgres==1.9.0 faker pandas sqlalchemy"
```

### Kết nối dbt → Postgres bên trong container

`profiles.yml` local dùng `host: localhost` — không dùng được trong container (localhost = chính container đó).

Giải pháp: tạo `profiles/profiles.yml` riêng với `host: postgres` (tên Docker service), mount vào container:

```yaml
volumes:
  - ./profiles:/opt/airflow/dbt_profiles

environment:
  DBT_PROFILES_DIR: /opt/airflow/dbt_profiles
```

Khi chạy dbt build trong BashOperator:
```bash
dbt build --profiles-dir /opt/airflow/dbt_profiles
```

---

## 9. Cons của cách làm hiện tại

| Vấn đề | Chi tiết | Fix production |
|--------|----------|----------------|
| **`_PIP_ADDITIONAL_REQUIREMENTS` chậm** | Install lại mỗi lần container start (~2-3 phút) | Viết `Dockerfile` extends `apache/airflow:2.9.3`, `RUN pip install ...` — build 1 lần |
| **Không có healthcheck** | `depends_on: condition: service_started` chỉ check container up, không check Postgres ready → airflow-init có thể connect trước Postgres sẵn sàng | Thêm `healthcheck` cho postgres service, dùng `condition: service_healthy` |
| **Password hardcode** | `--password admin` trong `airflow-init` command | Dùng `AIRFLOW_ADMIN_PASSWORD` env var từ `.env` |
| **`airflow-init` chạy lại mỗi `docker compose up`** | `restart: "no"` chỉ ngăn auto-restart, không ngăn `up` khởi chạy lại | Production dùng init container pattern với health probe hoặc Helm chart |
| **Không có `airflow_db` riêng** | Airflow metadata DB chung Postgres instance với data warehouse | Production tách riêng 2 Postgres instances |

---

## 10. Hướng đi lên Production

Cách làm hiện tại đủ để chạy local và demo portfolio. Khi cần nâng lên production, migration path theo thứ tự ưu tiên:

### Bước 1 — Dockerfile (thay `_PIP_ADDITIONAL_REQUIREMENTS`)
```dockerfile
# Dockerfile
FROM apache/airflow:2.9.3
RUN pip install --no-cache-dir \
    dbt-postgres==1.9.0 \
    faker \
    pandas \
    sqlalchemy
```
```yaml
# docker-compose.yaml — thay image: bằng build:
airflow-webserver:
  build: .        # ← build từ Dockerfile
  # xóa _PIP_ADDITIONAL_REQUIREMENTS
```
**Lợi ích:** start container tức thì, không tải lại packages mỗi lần.

### Bước 2 — Healthcheck cho Postgres
Hiện tại `condition: service_started` chỉ check container up, không check DB ready.
```yaml
postgres:
  image: postgres:15-alpine
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
    interval: 5s
    retries: 5

# Airflow services dùng:
depends_on:
  postgres:
    condition: service_healthy   # ← đổi từ service_started
```

### Bước 3 — Tách Airflow metadata DB riêng
Hiện tại Airflow và data warehouse chung 1 Postgres instance (database `airflow` vs `supplypulse`). Production nên tách:
```yaml
postgres-airflow:
  image: postgres:15-alpine
  environment:
    POSTGRES_DB: airflow
    POSTGRES_USER: airflow
    POSTGRES_PASSWORD: ${AIRFLOW_DB_PASSWORD}
```

### Bước 4 — Secrets management
Hiện tại password hardcode trong `docker-compose.yaml` và `.env`. Production dùng:
- Docker Secrets (`secrets:` block trong compose)
- Hoặc Airflow Connections UI (lưu credentials trong metadata DB, không trong file)

### Bước 5 — CeleryExecutor + Redis (nếu scale)
LocalExecutor đủ cho 1 máy. Khi cần chạy trên nhiều worker:
```
LocalExecutor → CeleryExecutor + Redis broker + multiple workers
```
Nhưng với SupplyPulse (1 pipeline/ngày) → LocalExecutor là đủ mãi mãi.

---

## 11. Self-check

1. Airflow **Scheduler** và **Webserver** khác nhau chỗ nào?
2. `catchup=False` là gì? Nếu bỏ đi, chuyện gì xảy ra với SupplyPulse?
3. Tại sao `generate_data >> load_bronze >> dbt_build` quan trọng hơn chạy 3 script trong 1 BashOperator duy nhất?
4. DAG file để ở đâu để Airflow tự nhận? Tại sao không cần restart container khi sửa DAG?
5. Tại sao `profiles/profiles.yml` dùng `host: postgres` thay vì `host: localhost`?
