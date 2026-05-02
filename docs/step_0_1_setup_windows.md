# Step 0.1 — Setup môi trường dev (Windows)

> Mục tiêu: có Python 3.11 + uv + Git + Docker + VS Code chạy được trong project folder, ready để code Phase 1.
> Toàn bộ chạy trong **PowerShell** (mở Windows + X → "Terminal" hoặc "Windows PowerShell").

---

## A. Verify state hiện tại

```powershell
python --version        # nếu không thấy gì hoặc lỗi → bỏ qua, uv sẽ cài
git --version           # nếu lỗi → cài Git ở step B
docker --version        # phải có (đã confirm)
code --version          # phải có (đã confirm)
```

Ghi lại version hiện tại (để biết có cần upgrade không):

```
- Python hiện tại: <điền>
- Git hiện tại:    <điền>
- Docker:          <điền>
```

---

## B. Cài tool còn thiếu

### B.1 Git (nếu chưa có)

```powershell
winget install --id Git.Git -e --source winget
```

Sau khi cài, **đóng PowerShell và mở lại** (PATH refresh).

```powershell
git --version           # phải báo version
```

Cấu hình 1 lần:

```powershell
git config --global user.name "Bui Duc"
git config --global user.email "buiducphat20@gmail.com"
git config --global init.defaultBranch main
git config --global core.autocrlf true
```

> Vì sao `core.autocrlf true`: Windows dùng CRLF, Linux/Mac dùng LF. Setting này tự convert khi commit/checkout, tránh nguyên team bị "diff toàn bộ file" khi 1 người Windows commit.

### B.2 uv (Python + package manager)

Cài bằng winget (sạch nhất):

```powershell
winget install --id=astral-sh.uv -e
```

Hoặc nếu winget không có:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Đóng/mở lại PowerShell** rồi verify:

```powershell
uv --version            # phải >= 0.4.0
```

### B.3 Cài Python 3.11 qua uv

```powershell
uv python install 3.11
uv python list          # phải thấy 3.11.x trong danh sách "downloads"
```

> Vì sao 3.11 (không phải 3.12 hay 3.13):
> - 3.11 là version bền — hầu hết library (PySpark, dbt-core, Prophet, LightGBM) đã support đầy đủ
> - 3.12 OK nhưng 1 vài lib ML chậm theo
> - 3.13 quá mới (oct 2024), nhiều lib chưa kịp support → sẽ gặp install error

---

## C. Bootstrap project

```powershell
cd "D:\Claude Project\Claude_data\Data architect\supplypulse"
```

### C.1 Init project metadata bằng uv

```powershell
uv init --bare --python 3.11
```

> `--bare` = không tạo `README.md`, `.gitignore`, `hello.py` mặc định (vì mình đã có README và .gitignore rồi).
> Lệnh này tạo: `pyproject.toml` + `.python-version`.

Mở `pyproject.toml` xem — chỉ vài dòng:

```toml
[project]
name = "supplypulse"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []
```

### C.2 Tạo virtual environment

```powershell
uv venv
```

Lệnh này tạo folder `.venv\` (đã có trong .gitignore mình tạo trước đó — không lo commit nhầm).

Activate venv:

```powershell
.\.venv\Scripts\Activate.ps1
```

Nếu báo lỗi *"running scripts is disabled on this system"*:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
# rồi thử Activate lại
```

Khi thành công, prompt sẽ có prefix `(supplypulse)`.

### C.3 Add dev dependencies

```powershell
uv add --dev ruff black pytest pre-commit
```

> Vì sao 4 tool này tối thiểu:
> - **ruff**: linter cực nhanh (Rust), thay flake8 + isort + autoflake
> - **black**: formatter, để khỏi cãi nhau "tab vs space" trong code review
> - **pytest**: chuẩn vàng test framework Python
> - **pre-commit**: chạy ruff/black trước mỗi `git commit` → không bao giờ commit code dở

Sau khi chạy, mở `pyproject.toml` lại — sẽ thấy section `[dependency-groups.dev]`.

### C.4 Verify

```powershell
python --version        # 3.11.x
ruff --version
black --version
pytest --version
```

Tất cả phải xuất hiện.

---

## D. VS Code extensions

```powershell
code --install-extension ms-python.python
code --install-extension charliermarsh.ruff
code --install-extension ms-azuretools.vscode-docker
code --install-extension innoverio.vscode-dbt-power-user
code --install-extension mtxr.sqltools
code --install-extension mtxr.sqltools-driver-pg
code --install-extension redhat.vscode-yaml
```

> Mỗi extension giải thích nhanh:
> - **ms-python.python** + **ruff**: highlight + lint + format Python
> - **vscode-docker**: build/run/inspect container ngay trong VS Code
> - **dbt-power-user** (sẽ dùng từ Phase 3): autocomplete `ref()`, lineage view
> - **sqltools + sqltools-driver-pg**: query Postgres trong VS Code, không cần DBeaver
> - **vscode-yaml**: schema validation cho dbt yml, GitHub Actions yml

---

## E. Settings VS Code cho project

Tạo file `.vscode/settings.json`:

```powershell
mkdir .vscode -Force
```

Nội dung `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": ".venv\\Scripts\\python.exe",
  "python.terminal.activateEnvironment": true,
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit",
      "source.fixAll": "explicit"
    }
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/.ruff_cache": true
  }
}
```

> Vì sao commit `.vscode/settings.json` lên Git: cả team (kể cả future-you sang máy mới) auto có format + interpreter giống nhau.

---

## F. (Chưa cần) ruff config

Mở `pyproject.toml`, append:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM"]
ignore = ["E501"]   # line length

[tool.black]
line-length = 100
target-version = ["py311"]
```

> Ý nghĩa rule code: E=pycodestyle, F=pyflakes, I=isort, N=pep8-naming, UP=pyupgrade, B=bugbear, SIM=simplify.
> 4 ngày đầu chỉ cần biết: bật mấy rule này = code chuẩn 80% best practice mà không phải nghĩ.

---

## G. Smoke test cuối (chỉ scope Step 0.1)

```powershell
# Trong project folder, venv đã activate:
python --version                      # phải là 3.11.x
where.exe python                      # path phải trong .venv\Scripts\
ruff --version
black --version
pytest --version

# Test ruff format trên 1 file rác
@'
import os,sys
def Hello(  x ):
    print(  x  )
'@ | Set-Content -Path test_format.py
ruff format test_format.py
ruff check --fix test_format.py
Get-Content test_format.py            # phải đã được clean
Remove-Item test_format.py
```

Nếu tất cả chạy không lỗi → Step 0.1 done.

> **Note:** `git init` / `git status` thuộc Step 0.2. `docker run` thuộc Step 2.1. Đừng test ở đây — sẽ "lỗi" mà thực ra là chưa tới phase.

---

## H. Self-check (trả lời được trước khi sang Step 0.2)

1. **Tại sao không nên `pip install` global?**
   *(gợi ý: dependency conflict giữa các project, không reproducible)*

2. **Khi push lên CI, làm sao đảm bảo cùng version package?**
   *(gợi ý: lock file — `uv.lock` — commit lên Git)*

3. **Khác nhau giữa `pyproject.toml` và `requirements.txt`?**
   *(gợi ý: pyproject.toml = declarative + metadata; requirements.txt = flat list, không có metadata)*

4. **`.venv` có nên commit lên Git không, vì sao?**
   *(gợi ý: KHÔNG — `.venv` là binary + platform-specific, dung lượng lớn, ai cũng tự tạo lại từ lock file)*

---

## I. Báo cáo done

Khi xong:

1. Update `PROGRESS.md`:
   - Đánh dấu Step 0.1 = `done`
   - Kéo Step 0.2 lên `next`

2. Trong chat tiếp theo gõ:
   ```
   Đọc PROGRESS.md. Step 0.1 done. Đẩy tôi qua Step 0.2.
   ```

3. Tôi sẽ kiểm tra bằng vài câu hỏi self-check trước khi sang Step 0.2 (Git workflow + pre-commit + .gitignore chuẩn).
