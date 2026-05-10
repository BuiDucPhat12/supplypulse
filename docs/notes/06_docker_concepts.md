# Docker — Key Concepts

## docker exec

Chạy command bên trong container **đang chạy**.

```
docker exec [flags] <container> <command>
```

| Phần | Ý nghĩa |
|------|---------|
| `-i` | Interactive — giữ stdin mở |
| `-t` | Allocate terminal — hiển thị đẹp |
| `-it` | Kết hợp cả 2 — dùng khi gõ tay |
| `supplypulse-postgres-1` | Tên container (docker-compose tự đặt: `<project>-<service>-<index>`) |

### Các case thường dùng

```powershell
# Vào shell container
docker exec -it supplypulse-postgres-1 bash

# Vào psql interactive
docker exec -it supplypulse-postgres-1 psql -U supplypulse -d supplypulse

# Chạy 1 câu SQL rồi thoát
docker exec -it supplypulse-postgres-1 psql -U supplypulse -d supplypulse -c "SELECT 1"

# Kiểm tra tables trong schema
docker exec -it supplypulse-postgres-1 psql -U supplypulse -d supplypulse -c "\dt bronze.*"

# Dùng trong script/CI — bỏ -t để output plain text
docker exec supplypulse-postgres-1 psql -U supplypulse -d supplypulse -c "SELECT count(*) FROM bronze.vbak"
```

### Khi nào bỏ `-it`?

| Flag | Giữ khi | Bỏ khi |
|------|---------|--------|
| `-t` | Gõ tay, muốn output đẹp | Pipe kết quả vào script (`\| grep`, `> file`) |
| `-i` | Cần nhập input | Chỉ chạy 1 lệnh, không cần input |

---

## docker ps

```powershell
docker ps          # liệt kê container đang chạy
docker ps -a       # liệt kê tất cả (kể cả stopped)
```

---

## docker compose

```powershell
docker compose up -d          # khởi động tất cả services (detached)
docker compose up -d postgres # khởi động 1 service cụ thể
docker compose down           # dừng và xoá containers
docker compose logs postgres  # xem logs của service
```

---

## Tên container trong docker-compose

Mặc định docker-compose đặt tên: `<project-name>-<service-name>-<index>`

Ví dụ: service tên `postgres` trong folder `supplypulse` → container tên `supplypulse-postgres-1`.

Kiểm tra tên thật: `docker ps`
