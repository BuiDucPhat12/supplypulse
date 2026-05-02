# Notes 01 — Python environment, uv, và các khái niệm mới (Step 0.1)

> Mục đích: file này là **tài liệu ôn tập / cheatsheet phỏng vấn**.
> Đọc khi: (1) chuẩn bị phỏng vấn, (2) onboard máy mới, (3) ôn lại sau vài tháng.
> Cấu trúc: từ "vì sao" → đến "làm gì" → đến "câu hỏi phỏng vấn".

---

## 1. Bức tranh lớn — vì sao phải quan tâm environment isolation?

**3 vấn đề kinh điển khi không có virtual environment:**

| Vấn đề | Ví dụ thực tế |
|---|---|
| **Dependency conflict** | Project A cần `pandas==1.5`, Project B cần `pandas==2.1`. Nếu cài global, 1 trong 2 sẽ vỡ. |
| **Pollution môi trường hệ thống** | `pip install` global → khi gỡ project, package vẫn còn. Theo thời gian: hàng trăm package thừa. |
| **"Works on my machine"** | Dev A cài `numpy==1.24` (mặc định khi chạy `pip install numpy` 2023). Dev B cài 2024 thì là `numpy==1.26` → behavior khác. |

**Giải pháp:** mỗi project = 1 virtual environment **riêng** + lock file pin chính xác version.

---

## 2. uv là gì? Thay thế cái gì?

**uv** (Astral, viết bằng Rust, ra mắt 2024) là **all-in-one Python toolchain** thay thế:

| Tool cũ | uv thay thế cho việc gì |
|---|---|
| `pyenv` / `pyenv-win` | Cài và quản lý Python version |
| `pip` | Cài package |
| `pipx` | Cài CLI tool toàn cục có isolation |
| `virtualenv` / `venv` | Tạo virtual environment |
| `poetry` / `pipenv` | Resolve + lock dependencies |
| `pip-tools` (pip-compile) | Generate lock file |

**3 lý do chọn uv:**
1. **Tốc độ:** nhanh hơn pip 10-100×. Cài 50 package trong 2 giây thay vì 2 phút.
2. **One-binary:** không cần cài 5 tool riêng. Một `uv` lo hết.
3. **Tương lai:** Astral cũng làm `ruff` — đang trở thành chuẩn de facto của Python 2024+.

**Vì sao không Anaconda:** nặng (~3GB), conflict version, không phổ biến trong production data eng. Cộng đồng modern (FAANG, startup) chuyển hẳn sang `uv`.

**Vì sao không poetry:** poetry vẫn ổn nhưng chậm hơn uv 10×, cộng đồng đang migrate sang uv.

---

## 3. Quản lý Python version với uv

```powershell
uv python install 3.11        # cài Python 3.11.x mới nhất
uv python list                 # liệt kê các version đã cài + sẵn sàng download
uv python pin 3.11             # tạo file .python-version trong folder
```

**Điểm quan trọng:** uv cài Python vào storage riêng của nó (`~/.local/share/uv/python/`) — **không đụng** Python hệ thống (3.10.7 của bạn vẫn còn nguyên).

**File `.python-version`:** chứa 1 dòng (vd `3.11`). Khi bạn `cd` vào project, uv tự pick version này.

---

## 4. Virtual environment

### Bản chất `.venv/`

Folder `.venv/` chứa:
- `Scripts/python.exe` (Windows) hoặc `bin/python` (Linux/Mac) — **bản copy** của Python interpreter
- `Lib/site-packages/` — nơi `uv add` / `pip install` cài package vào (KHÔNG cài vào hệ thống)
- `pyvenv.cfg` — metadata trỏ về Python gốc

### Vì sao KHÔNG commit `.venv/`?

1. **Platform-specific:** venv của Windows không chạy được trên Linux (`.dll` vs `.so`)
2. **Dung lượng:** 100-500MB tuỳ package
3. **Có thể tái tạo:** `uv sync` từ `pyproject.toml` + `uv.lock` là tạo lại được y hệt

→ Trong `.gitignore` luôn có dòng `.venv/`.

### Activate / Deactivate

```powershell
.\.venv\Scripts\Activate.ps1     # PowerShell
deactivate                        # thoát
```

**Activate làm gì:** chỉ thay đổi PATH của shell hiện tại, ưu tiên `.venv\Scripts\` trước. Không "chạy" gì cả.

**Cách verify đang ở venv nào:**
```powershell
where.exe python                 # phải trỏ vào .venv của project hiện tại
```

> ⚠️ Bug phổ biến: VS Code auto-activate venv của project khác (vd venv course cũ). Luôn check `where.exe python` trước khi `uv add`.

---

## 5. `pyproject.toml` — single source of truth

### Cấu trúc của file (đầy đủ sau Step 0.1)

```toml
[project]
name = "supplypulse"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []                 # runtime deps - sẽ thêm dần

[dependency-groups]
dev = [
  "ruff>=0.4",
  "black>=24",
  "pytest>=8",
  "pre-commit>=3",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM"]
ignore = ["E501"]

[tool.black]
line-length = 100
target-version = ["py311"]
```

### So sánh với `requirements.txt` cũ

| | `pyproject.toml` | `requirements.txt` |
|---|---|---|
| Tuổi | PEP 518 (2016+), PEP 621 (2020) | ~2012, không có PEP chính thức |
| Format | TOML có structure | Plain text 1 dòng / package |
| Chứa | Metadata + deps + tool config | Chỉ deps |
| Lock file | Đi kèm `uv.lock` / `poetry.lock` | Phải tự `pip freeze` (không pin transitive) |
| Tách runtime / dev | Có (`[dependency-groups]`) | Phải tạo `requirements-dev.txt` riêng |
| Industry direction | Tương lai | Legacy, giữ vì Heroku/Lambda layer cũ |

### Cách thêm package

```powershell
uv add pandas                    # runtime dependency
uv add --dev pytest              # dev-only dependency
uv remove pandas                  # gỡ
```

uv tự update `pyproject.toml` + `uv.lock`.

---

## 6. Lock file (`uv.lock`) — cốt lõi của reproducibility

### Vấn đề muốn giải

`pyproject.toml` ghi: *"tôi cần `pandas>=2.0`"*. Nhưng `pandas>=2.0` có thể là `2.0.0`, `2.0.5`, `2.1.3`... Sau 6 tháng pandas ra `2.5.0`, đồng nghiệp clone về có thể bị behavior khác.

### Lock file pin **chính xác**

`uv.lock` ghi:
```
pandas==2.1.3                    # pinned version
pandas--hash=sha256:abc123...    # checksum để verify file integrity
+ tất cả transitive deps (numpy, python-dateutil, pytz...)
```

→ Mọi máy clone về sẽ cài **chính xác** versions này.

### Workflow chuẩn

```powershell
# 1. Bạn declare
uv add pandas

# 2. uv resolve + tạo/update uv.lock
# (tự động chạy)

# 3. Commit cả pyproject.toml VÀ uv.lock
git add pyproject.toml uv.lock
git commit -m "chore: add pandas"

# 4. Đồng nghiệp pull, chạy:
uv sync                          # cài đúng version trong lock
```

### Khi cần update package

```powershell
uv lock --upgrade-package pandas    # update chỉ pandas
uv lock --upgrade                    # update toàn bộ (cẩn thận)
```

> 💡 **Nguyên tắc vàng:** Lock file là *artifact*, không phải source. Đừng sửa tay. Để uv generate.

---

## 7. Code quality tools (4 cái cài ở Step 0.1)

### 7.1 `ruff`

- **Là gì:** linter + formatter viết bằng Rust
- **Thay thế:** flake8, isort, autoflake, pyupgrade, pylint (1 phần)
- **Tốc độ:** nhanh hơn flake8 ~100×
- **Hai chế độ chính:**
  ```powershell
  ruff check .                   # lint (tìm lỗi, không sửa)
  ruff check --fix .             # lint + auto-fix
  ruff format .                  # format code (giống black)
  ```

### 7.2 `black`

- **Là gì:** code formatter "không cãi nhau"
- **Triết lý:** *"the uncompromising code formatter"* — không có option, mọi codebase look giống nhau
- **Vì sao vẫn dùng cùng ruff:** ruff-format đã giống black 99% nhưng vẫn còn 1% edge case. Có cả 2 = double safety. Sau khi quen, có thể bỏ black.

### 7.3 `pytest`

- **Là gì:** test framework chuẩn vàng của Python
- **Thay thế:** unittest (built-in nhưng verbose)
- **Cú pháp đơn giản nhất:**
  ```python
  def test_addition():
      assert 1 + 1 == 2
  ```
- Chạy: `pytest`

### 7.4 `pre-commit`

- **Là gì:** framework chạy hook trước mỗi `git commit`
- **Vai trò:** chặn commit code dở (chưa format, chưa lint, file lớn, có private key...)
- **File config:** `.pre-commit-config.yaml` (sẽ làm ở Step 0.2)

---

## 8. Ruff rule codes (giải mã `select = ["E", "F", "I", "N", "UP", "B", "SIM"]`)

| Code | Source | Bắt cái gì | Ví dụ |
|---|---|---|---|
| `E` | pycodestyle | PEP 8 style | `E501` line too long, `E711` `if x == None` |
| `F` | pyflakes | logic error | `F401` unused import, `F841` unused variable |
| `I` | isort | import order | imports lộn xộn, không alphabetical |
| `N` | pep8-naming | naming convention | `N802` function `Hello` thay vì `hello` |
| `UP` | pyupgrade | code outdated | `UP006` `List[int]` thay vì `list[int]` (Python 3.9+) |
| `B` | flake8-bugbear | bug-prone pattern | `B008` mutable default argument |
| `SIM` | flake8-simplify | có thể đơn giản hơn | `SIM108` if-else thay bằng ternary |

**Bonus codes (không bật mặc định nhưng nên biết):**
- `D` — docstring (Google/NumPy style)
- `S` — security (bandit)
- `RUF` — ruff-specific rules

---

## 9. Cross-platform gotchas (Windows ↔ Linux)

### 9.1 Line endings

| OS | Convention |
|---|---|
| Windows | CRLF (`\r\n`) |
| Linux/Mac | LF (`\n`) |

**Vấn đề:** Windows dev commit CRLF → Linux CI báo "diff toàn bộ file".

**Fix 2 lớp:**
1. Git config: `git config --global core.autocrlf true` (Windows) → tự convert khi commit/checkout
2. VS Code: `"files.eol": "\n"` trong settings.json → save = LF

### 9.2 Path separator

- Windows: `C:\Users\...` (backslash)
- Linux: `/home/...` (forward slash)

**Khi viết code Python:** dùng `pathlib.Path` thay vì string concat:
```python
from pathlib import Path
data_dir = Path("data") / "raw" / "se16"        # cross-platform
```

### 9.3 Encoding

- Windows mặc định cp1252 / cp936 (tùy locale)
- Linux/Mac UTF-8

**Khi viết file:** luôn explicit:
```python
with open("file.txt", "w", encoding="utf-8") as f:
    ...
```

PowerShell: `Set-Content -Encoding UTF8`.

---

## 10. PowerShell mini-cheatsheet (đã dùng trong Step 0.1)

| Lệnh / Cú pháp | Ý nghĩa |
|---|---|
| `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` | Cho phép chạy script .ps1 (mặc định Windows chặn) |
| `@'...'@ \| Set-Content -Path file.txt -Encoding UTF8` | Here-string: viết multi-line vào file, giữ nguyên format |
| `Get-Content file.txt` | = `cat file.txt` ở Linux |
| `where.exe python` | Tìm executable. **Bắt buộc dùng `where.exe`** vì PowerShell có alias `where` cho Where-Object |
| `$env:USERNAME` | Biến env (= `$USER` ở Linux) |
| `mkdir foo -Force` | Tạo folder, không lỗi nếu đã tồn tại |
| `Remove-Item file.txt` | = `rm file.txt` |
| `Get-ChildItem` | = `ls` |

---

## 11. VS Code project settings — `.vscode/settings.json`

### Vì sao **commit** file này lên Git?

Để cả team (kể cả future-you sang máy mới) auto có config giống nhau: cùng formatter, cùng auto-organize-imports khi save, cùng line ending. Onboard 0 setup.

### Setting quan trọng nhất bạn đã làm

| Setting | Tác dụng |
|---|---|
| `python.defaultInterpreterPath` | Trỏ vào venv project, không pick nhầm Python hệ thống |
| `python.terminal.activateEnvironment` | Mỗi terminal mới tự `activate` venv (đỡ gõ tay) |
| `editor.formatOnSave` (cho `[python]`) | Save = auto format |
| `source.organizeImports: explicit` | Save = sort imports tự động |
| `files.eol: "\n"` | Force LF, không CRLF |
| `files.trimTrailingWhitespace: true` | Save = xoá space cuối dòng |
| `terminal.integrated.defaultProfile.windows: "PowerShell"` | Mặc định mở PowerShell, không cmd |

---

## 12. Interview-ready answers — Self-check Step 0.1 mở rộng

### Q1. Vì sao không nên `pip install` global?

**Trả lời chuẩn:** Vì 3 lý do:
1. **Conflict:** dependency của project A có thể đè project B (numpy 1.24 vs 1.26).
2. **Pollute hệ thống:** package thừa tích tụ, gỡ project nhưng package vẫn còn.
3. **Không reproducible:** mỗi máy có set package khác nhau → "works on my machine".

→ Giải pháp: virtual environment per-project + lock file.

### Q2. Khác biệt `pyproject.toml` vs `requirements.txt`?

**Trả lời chuẩn:** `pyproject.toml` là single source of truth (PEP 518/621): chứa metadata project, runtime deps, dev deps, và config tool (ruff, black, pytest) trong 1 file structured TOML. `requirements.txt` là format cũ chỉ có flat list package, không có metadata, không pin transitive deps. Modern Python ecosystem đang migrate hết sang `pyproject.toml`; `requirements.txt` chỉ còn vì backward compat (Heroku, Lambda).

### Q3. `.venv` có nên commit lên Git không?

**Trả lời chuẩn:** Không. Vì (1) platform-specific (Windows venv không chạy trên Linux), (2) dung lượng lớn, (3) tái tạo được từ `uv sync`. Đó là lý do `.gitignore` luôn có `.venv/`.

### Q4. Đồng nghiệp clone repo, làm sao recreate môi trường?

**Trả lời chuẩn:**
```bash
git clone <repo>
cd <repo>
uv sync
```

Bí mật: file `uv.lock` (commit cùng pyproject.toml) pin chính xác version của tất cả package + transitive dependencies + checksum. `uv sync` đọc lock file → tạo .venv y hệt máy bạn.

### Q5 (follow-up). Lock file vs requirements.txt là một được không?

**Trả lời:** Không. `pip freeze > requirements.txt` không pin transitive đầy đủ và không có hash checksum. Lock file (`uv.lock`, `poetry.lock`, `Pipfile.lock`) là declarative + có integrity check.

### Q6 (follow-up). Khi nào cần update lock file?

**Trả lời:** Khi (1) thêm package mới (`uv add` tự update), (2) muốn upgrade package (`uv lock --upgrade-package`), (3) security advisory yêu cầu bump. Sau update phải test lại + commit `uv.lock`.

### Q7 (follow-up). uv khác poetry chỗ nào?

**Trả lời:** uv (Astral, Rust) nhanh hơn poetry 10×, cài thẳng Python interpreter (poetry không), 1 binary thay 5 tool. Poetry vẫn mature hơn về plugin nhưng đang lép vế dần. Modern stack 2024+ chọn uv.

### Q8 (follow-up). Vì sao chọn ruff thay flake8 + isort + black?

**Trả lời:** ruff làm cả 3 việc trong 1 binary, nhanh hơn 100× vì viết bằng Rust và dùng AST shared. Setup đơn giản (1 config block). Maintained bởi Astral cùng team uv.

---

## 13. Daily commands cheatsheet

```powershell
# Bật venv (mỗi lần mở terminal mới nếu VS Code chưa tự activate)
.\.venv\Scripts\Activate.ps1

# Thêm package
uv add pandas
uv add --dev pytest

# Sync với lock file (sau khi pull về có lock file mới)
uv sync

# Update package
uv lock --upgrade-package pandas

# Lint + format
ruff check --fix .
ruff format .

# Test
pytest -q

# Verify đúng venv
where.exe python
python --version
```

---

## 14. Đọc thêm (nếu rảnh, không bắt buộc)

- **uv docs:** https://docs.astral.sh/uv/
- **PEP 518** (pyproject.toml): https://peps.python.org/pep-0518/
- **PEP 621** (project metadata): https://peps.python.org/pep-0621/
- **Astral blog:** https://astral.sh/blog (theo dõi update uv + ruff)
- **Ruff rules:** https://docs.astral.sh/ruff/rules/

---

## 15. TL;DR — 1 đoạn nhớ thuộc

> uv là all-in-one toolchain Python (Rust, 2024+) thay thế pyenv + pip + pipx + venv + poetry. Mỗi project có `pyproject.toml` (declare deps + tool config) và `uv.lock` (pin chính xác version). `.venv/` chứa Python interpreter copy + package, **không commit lên Git**. Reproducibility được bảo đảm bởi lock file: `uv sync` trên máy mới tạo lại venv y hệt. Code quality stack: ruff (lint+format), black (format backup), pytest (test), pre-commit (git hook chặn code dở).
