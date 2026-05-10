# Bronze Layer — Key Concepts

## Tại sao Bronze dùng tất cả TEXT?

Bronze = raw layer, không ép kiểu. Nếu CSV có giá trị bẩn mà ép DATE/INTEGER → loader fail.
TEXT không bao giờ fail. Ép kiểu đúng là việc của Silver layer.

## Idempotent loader — TRUNCATE + insert

Chạy `load_bronze.py` nhiều lần → kết quả như nhau, không bị nhân đôi data.
Vì mỗi lần chạy đều TRUNCATE bảng trước khi insert.

## `if_exists='append'` vs `if_exists='replace'`

- `append` — thêm data vào bảng đã tồn tại. Giữ nguyên DDL.
- `replace` — **DROP TABLE rồi CREATE lại** → mất toàn bộ DDL đã viết (tất cả cột TEXT).

Đó là lý do phải dùng `append` sau TRUNCATE thủ công, không dùng `replace`.

## pandas `to_sql` vs PostgreSQL `COPY`

- `to_sql` — INSERT từng row/chunk. Đủ cho prototype và data nhỏ.
- `COPY FROM STDIN` (psycopg2 `copy_expert`) — nhanh hơn 10-50 lần. Dùng cho production large dataset.

Câu trả lời phỏng vấn: *"Bronze loader tôi dùng pandas `to_sql` — đủ cho prototype. Production thì chuyển sang `COPY FROM STDIN` vì nhanh hơn 10-50 lần với large dataset."*
