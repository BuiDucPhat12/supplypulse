# SAP SE16 Source Design

> **Owner:** Bui Duc
> **Status:** DRAFT — bạn tự điền các phần `<...>` bên dưới.
> **Mục đích:** trước khi viết bất kỳ dòng code nào, chốt rõ source: bảng nào, field nào, volume bao nhiêu, refresh ra sao.

---

## 0. Quyết định scope

**Module SAP focus** *(tick những module bạn sẽ dùng)*:

- [ ] **SD** — Sales & Distribution (sales order, delivery, billing)
- [ ] **MM** — Materials Management (purchase order, GR, vendor)
- [ ] **PP** — Production Planning (production order, BOM, routing)
- [ ] **WM/EWM** — Warehouse Management (stock movement, bin)
- [ ] **FI/CO** — Finance / Controlling (chỉ nếu thực sự cần)

> **Khuyến nghị cho project SupplyPulse:** SD + MM (bao trọn vòng order-to-cash + procure-to-pay) là đủ phong phú để làm forecast + anomaly + SLA risk.

**Lý do chọn của bạn (1-3 câu):**

```
<điền>
```

---

## 1. Danh sách bảng SE16

Điền theo template; xoá dòng không dùng, thêm dòng mới nếu cần.

### 1.1 Sales & Distribution (SD)

| Table | Tên đầy đủ            | Loại     | Key                | Volume ước tính | Refresh | Ghi chú |
| ----- | --------------------- | -------- | ------------------ | --------------- | ------- | ------- |
| VBAK  | Sales Order Header    | TX (fact)| VBELN              | <X>/day         | hourly  |         |
| VBAP  | Sales Order Item      | TX       | VBELN, POSNR       | <X>/day         | hourly  |         |
| LIKP  | Delivery Header       | TX       | VBELN              | <X>/day         | hourly  |         |
| LIPS  | Delivery Item         | TX       | VBELN, POSNR       | <X>/day         | hourly  |         |
| VBFA  | Document Flow         | TX       | VBELV, VBELN       |                 | hourly  | OTC chain |
| KNA1  | Customer General      | MD (dim) | KUNNR              | small           | daily   |         |

### 1.2 Materials Management (MM)

| Table | Tên đầy đủ           | Loại | Key            | Volume | Refresh | Ghi chú          |
| ----- | -------------------- | ---- | -------------- | ------ | ------- | ---------------- |
| EKKO  | PO Header            | TX   | EBELN          |        | hourly  |                  |
| EKPO  | PO Item              | TX   | EBELN, EBELP   |        | hourly  |                  |
| EKET  | PO Schedule Line     | TX   | EBELN, EBELP, ETENR |   | hourly  | dùng cho lead time |
| MKPF  | Material Doc Header  | TX   | MBLNR, MJAHR   |        | hourly  | GR / GI events   |
| MSEG  | Material Doc Item    | TX   | MBLNR, MJAHR, ZEILE |   | hourly  |                  |
| MARA  | Material Master      | MD   | MATNR          | small  | daily   |                  |
| MARC  | Material Plant Data  | MD   | MATNR, WERKS   |        | daily   |                  |
| MARD  | Storage Loc Stock    | MD   | MATNR, WERKS, LGORT | | hourly  | inventory level  |
| LFA1  | Vendor Master        | MD   | LIFNR          | small  | daily   |                  |

### 1.3 (Optional) Production Planning (PP)

| Table | Tên đầy đủ        | Loại | Key | Volume | Refresh |
| ----- | ----------------- | ---- | --- | ------ | ------- |
| AUFK  | Order Master Data | TX   | AUFNR |     | hourly  |
| AFKO  | Order Header      | TX   | AUFNR |     | hourly  |
| AFPO  | Order Item        | TX   | AUFNR, POSNR | | hourly |

---

## 2. Field-level design (chi tiết bảng quan trọng)

### Ví dụ: VBAK

| Field   | SAP type | Business meaning             | Bronze keep? | Standardize name (Silver) | PII? |
| ------- | -------- | ---------------------------- | ------------ | ------------------------- | ---- |
| MANDT   | CLNT     | Client (môi trường SAP)      | yes          | client_id                 | no   |
| VBELN   | CHAR(10) | Sales document number        | yes          | sales_order_id            | no   |
| ERDAT   | DATS     | Created on                   | yes          | created_date              | no   |
| ERZET   | TIMS     | Created at (time)            | yes          | created_time              | no   |
| ERNAM   | CHAR(12) | User who created             | yes          | created_by                | yes  |
| AUART   | CHAR(4)  | Sales document type          | yes          | order_type_code           | no   |
| KUNNR   | CHAR(10) | Sold-to customer             | yes          | customer_id               | semi |
| NETWR   | CURR     | Net value of order in doc    | yes          | net_value                 | no   |
| WAERK   | CUKY     | SD document currency         | yes          | currency_code             | no   |
| ...     | ...      | ...                          | ...          | ...                       | ...  |

**Quy tắc đặt tên ở Silver (đề xuất):** `snake_case`, **không** giữ tên SAP gốc; đổi sang nghĩa English business chuẩn.

> Tự điền tương tự cho VBAP, EKKO, EKPO, MARA, MARC. Càng kỹ ở step này, code sau càng nhanh.

---

## 3. Khối lượng & growth

| Bảng | Rows hiện tại (ước) | Rows/day | Bronze size/year | Tốc độ tăng |
| ---- | ------------------- | -------- | ---------------- | ----------- |
| VBAK |                     |          |                  |             |
| VBAP |                     |          |                  |             |
| EKKO |                     |          |                  |             |
| EKPO |                     |          |                  |             |
| MSEG |                     |          |                  |             |

> Ước lượng để biết: dùng full reload hay incremental? Nếu >5M row → bắt buộc incremental.

---

## 4. Cách extract từ SAP

### 4.1 Manual (Phase 1 — học)

1. Log SAP GUI → `SE16` hoặc `SE16N`
2. Nhập tên bảng (vd `VBAK`)
3. Filter ngày (`ERDAT >= 2025-01-01`)
4. *List → Save → Local file → Spreadsheet (XLSX)* hoặc *Unconverted (TXT)*
5. Convert sang CSV (UTF-8, comma) bằng Excel hoặc script
6. Đặt vào `data/raw/se16/<table>/<table>_YYYYMMDD.csv`

### 4.2 Tự động (Phase 5+ — sau khi đã quen)

Có 3 hướng, chọn 1:

- **(A) Theo dõi qua SAP Open Hub Service** → đẩy ra file system / Azure Blob → ingest. (Cần quyền BW)
- **(B) RFC + `pyrfc`** Python library — kết nối trực tiếp SAP qua RFC. (Cần SAP credentials + library nặng)
- **(C) CDC từ database tier (Debezium → Kafka)** — chỉ làm được khi có quyền database (HANA/Oracle), thường không có. *Production-grade nhất nhưng khó nhất.*

> **Cho project portfolio:** đi (A) hoặc (B) là realistic. Bạn ghi rõ "approach C đã được cân nhắc nhưng không khả thi do quyền truy cập" — đây là cách trả lời chững chạc khi recruiter hỏi.

**Quyết định của bạn:**

```
<điền — tôi sẽ đi approach (?) vì ... >
```

---

## 5. Compliance & PII

- [ ] Đã review danh sách field PII (ERNAM, KUNNR có thể chứa thông tin khách hàng)
- [ ] Có quy trình anonymize trước khi đẩy vào lake (hash hoặc faker-replace)
- [ ] Không commit data lên Git
- [ ] Đã hỏi sếp / IT-Compliance ở Bosch nếu dùng data thật cho portfolio? (kể cả dạng đã anonymize)

> **Tuyệt đối không** copy data thật của Bosch lên repo public. Khi cần show ra ngoài, tốt nhất generate synthetic data **đúng schema** trên cùng cấu trúc đã thiết kế.

---

## 6. ERD

> Vẽ tay hoặc dùng dbdiagram.io / drawio. Lưu ảnh `docs/img/erd_sap_source.png`.
> Tối thiểu cần show: VBAK→VBAP→LIKP→LIPS, EKKO→EKPO→EKET, MARA-MARC-MARD.

---

## 7. Open questions (để tôi giúp bạn tiếp ở step kế)

- [ ] Bạn dùng SAP version nào? (S/4HANA hay ECC) — ảnh hưởng tên bảng (vd ACDOCA chỉ có ở S/4)
- [ ] Có bảng custom Z* không? (Bosch hay có)
- [ ] Có dùng calendar / fiscal year đặc biệt không? (T009)

Khi điền xong file này, ping tôi: *"SAP source design xong, qua step kế."*
