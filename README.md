# SupplyPulse

> Real-Time Supply Chain Intelligence Platform — streaming + batch + ML + BI on an open-source stack.
> **Source:** SAP SE16 table extracts (SD + MM modules) from Bosch operational system.

## TL;DR

SupplyPulse là portfolio project của một **Analytics Engineer** giải quyết bài toán chuỗi cung ứng có thật ở Bosch:
- Lấy bảng SE16 (VBAK, VBAP, EKKO, EKPO, MARA, MARC, ...) làm nguồn
- Đổ vào lakehouse (Postgres bronze → silver → gold)
- Transform bằng dbt
- Forecast nhu cầu + phát hiện bất thường streaming
- Serve qua FastAPI + Streamlit cockpit

> Project được build **đi từ con số 0**, từng bước có giải thích chọn tool — xem `../SupplyPulse_Learning_Journey.md`.

## Status

Đang ở **Phase 0 — Setup**. Repo còn trống có chủ đích — sẽ tự build từng bước.

## Quick links

- `../SupplyPulse_Blueprint.md` — high-level design
- `../SupplyPulse_Learning_Journey.md` — lộ trình học step-by-step
- `docs/sap_source_design.md` — thiết kế nguồn SAP (cần điền)
- `docs/architecture.md` — tóm tắt kỹ thuật

## License

MIT
