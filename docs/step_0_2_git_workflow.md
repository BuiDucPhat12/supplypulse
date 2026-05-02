# Step 0.2 — Git workflow + pre-commit + GitHub

> Mục tiêu: project có git repo local, push lên GitHub public, có pre-commit hook chặn commit code dở, biết Conventional Commits để commit history đẹp như changelog.

---

## A. Lý thuyết: Conventional Commits (5 phút đọc)

**Vấn đề cũ:** commit messages kiểu *"fix bug"*, *"update"*, *"asdf"* — sau 6 tháng không ai biết commit nào làm gì.

**Giải pháp:** quy ước format chuẩn, máy đọc được, người đọc nhanh.

### Format

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### Các `type` thường dùng (nhớ 7 cái này)

| Type | Khi nào dùng | Ví dụ |
|---|---|---|
| `feat` | Thêm tính năng mới | `feat(dbt): add mart_supplier_otd model` |
| `fix` | Sửa bug | `fix(simulator): handle empty kafka batch` |
| `docs` | Chỉ sửa docs/README | `docs: add SAP source design` |
| `chore` | Việc lặt vặt (config, dep update) | `chore: bump dbt to 1.7.4` |
| `refactor` | Đổi structure không đổi behavior | `refactor(api): split routes into modules` |
| `test` | Thêm/sửa test | `test(loader): add idempotency test` |
| `ci` | Sửa CI pipeline | `ci: add dbt build to github actions` |

### Quy tắc:
- **Subject** ngắn gọn (≤ 72 ký tự), không chấm cuối câu, dùng imperative ("add" không phải "added")
- **Scope** (optional, trong ngoặc): module/folder bị ảnh hưởng — `dbt`, `simulator`, `airflow`...
- **Body** (optional): giải thích *vì sao*, không phải *làm gì* (code đã nói "làm gì")

### Ví dụ tốt vs xấu

❌ `fix bug`
✅ `fix(loader): prevent duplicate inserts when CSV has trailing blank rows`

❌ `update dbt`
✅ `feat(dbt): add stg_vbak with field renaming for SAP-to-business mapping`

❌ `asdf` (đừng cười, ai cũng từng làm)
✅ `chore(env): pin Python to 3.11 via pyenv`

> **Tại sao đáng làm:** recruiter mở GitHub bạn, scroll commit history. Conventional commits = bạn pro. Random messages = bạn newbie. **Đây là cheap signal cực mạnh.**

---

## B. `git init` + first commit local

### B.1 Init repo

```powershell
cd "D:\Claude Project\Claude_data\Data architect\supplypulse"
git init -b main
```

`-b main`: branch mặc định là `main` (không phải `master` — modern convention từ 2020).

### B.2 Audit `.gitignore`

Mở `.gitignore` (đã có sẵn). Verify nó có ít nhất:

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.env
.DS_Store
```

Nếu thiếu, thêm vào. Đảm bảo `.venv/` và `.env` ở đó — KHÔNG bao giờ commit chúng.

### B.3 Sanity check

```powershell
git status
```

Đảm bảo:
- ✅ Thấy `.gitignore`, `README.md`, `pyproject.toml`, `uv.lock`, `.python-version`, `docs/...`, `.vscode/settings.json` trong "Untracked files"
- ❌ KHÔNG thấy `.venv/` hoặc `__pycache__/` (nếu thấy → .gitignore chưa work, fix trước khi commit)

### B.4 Stage + first commit

```powershell
git add .
git status                                    # double-check không có .venv
git commit -m "chore: initial project scaffold with uv + ruff + black + pytest"
```

Verify:

```powershell
git log --oneline
```

Phải thấy 1 dòng commit của bạn.

---

## C. pre-commit hooks (chặn code dở trước khi commit)

### C.1 Concept (1 phút)

`pre-commit` là framework chạy linter/formatter **tự động** trước mỗi `git commit`. Nếu code có lỗi → block commit. Bạn không bao giờ commit code chưa format hay vi phạm lint rule.

### C.2 Tạo `.pre-commit-config.yaml`

```powershell
@'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
        args: ["--maxkb=5000"]
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.10
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/psf/black-pre-commit-mirror
    rev: 24.4.2
    hooks:
      - id: black
'@ | Set-Content -Path .pre-commit-config.yaml -Encoding UTF8
```

> **Giải thích từng hook:**
> - `end-of-file-fixer`: file phải kết thúc bằng newline (Unix convention)
> - `trailing-whitespace`: xoá space ở cuối dòng
> - `check-yaml/check-toml`: parse được không (catch syntax error sớm)
> - `check-added-large-files`: chặn commit file >5MB (sợ commit nhầm CSV)
> - `check-merge-conflict`: chặn commit khi còn `<<<<<<<` markers
> - `detect-private-key`: chặn commit nhầm SSH/API key (cứu mạng nhiều dev)
> - `ruff` + `ruff-format`: lint + format Python
> - `black`: backup formatter (cùng style với ruff-format, nhưng chạy double cho chắc — sẽ bỏ sau khi quen ruff)

### C.3 Install hook

```powershell
pre-commit install
```

Output: `pre-commit installed at .git\hooks\pre-commit`.

### C.4 Test hook

```powershell
# Chạy thử trên toàn repo (lần đầu sẽ download các hook, chậm 1-2 phút)
pre-commit run --all-files
```

Lần đầu hooks sẽ download repos. Có thể fail vài chỗ (vd `end-of-file-fixer` sửa file thiếu newline). Đó là **đúng behavior** — nó tự fix, bạn `git add` lại rồi chạy `pre-commit run --all-files` lại lần 2 phải pass.

### C.5 Commit lại sau khi pre-commit fix

```powershell
git add .
git commit -m "chore: add pre-commit hooks (ruff, black, file checks)"
```

Lần này commit phải **đi qua pre-commit** trước (bạn sẽ thấy nó in các check pass).

---

## D. Tạo GitHub repo + push

### D.1 Tạo repo trên GitHub (web)

1. Vào https://github.com/new
2. Repository name: `supplypulse`
3. Description: *"Real-Time Supply Chain Intelligence Platform — Analytics Engineer portfolio"*
4. Visibility: **Public** (đã chọn)
5. ❌ **KHÔNG** tick "Add README", "Add .gitignore", "Choose license" — vì bạn đã có local rồi, tránh conflict
6. Click "Create repository"

GitHub sẽ show 1 trang với hướng dẫn — copy 2 lệnh ở section *"…or push an existing repository from the command line"*. Sẽ trông như:

```
git remote add origin https://github.com/<your-username>/supplypulse.git
git branch -M main
git push -u origin main
```

### D.2 Authentication: Personal Access Token (PAT)

GitHub không cho push qua password từ 2021. Bạn cần PAT (token).

1. Vào https://github.com/settings/tokens?type=beta
2. Click *"Generate new token"* → *"Fine-grained personal access token"*
3. Token name: `supplypulse-laptop`
4. Expiration: 90 ngày
5. Repository access: chọn `Only select repositories` → `supplypulse`
6. Permissions:
   - Repository permissions: **Contents: Read and write**, **Metadata: Read-only** (auto), **Pull requests: Read and write**
7. Generate, **copy token ngay** (không show lại được)

### D.3 Push

```powershell
git remote add origin https://github.com/<your-username>/supplypulse.git
git push -u origin main
```

Khi prompt username/password:
- Username: GitHub username của bạn
- Password: **paste PAT** (không phải password GitHub)

Tip: Windows credential manager sẽ nhớ PAT cho lần sau. Một lần khổ, mãi mãi sướng.

### D.4 Verify

Mở https://github.com/<your-username>/supplypulse — phải thấy code, README hiển thị đẹp.

---

## E. Branch strategy

**Convention chọn:** trunk-based với feature branch ngắn hạn.

- `main`: luôn deploy được, không commit trực tiếp
- `feat/*`, `fix/*`, `docs/*`: branch ngắn (1-3 ngày), merge qua PR vào `main`

### E.1 Tạo branch đầu tiên cho Phase 1

```powershell
git checkout -b feat/01-sap-source-design
```

Branch này bạn sẽ làm việc khi điền `docs/sap_source_design.md` ở Step 1.1.

### E.2 Push branch lên GitHub

```powershell
git push -u origin feat/01-sap-source-design
```

GitHub sẽ tạo branch tương ứng, có nút "Compare & Pull Request".

---

## F. Self-check

1. **Conventional Commits — 7 type chính là gì?**
2. **Vì sao `pre-commit` chặy được trước `git commit`?** (gợi ý: hook là gì, ở đâu trong `.git/`)
3. **Lần đầu push GitHub bị `Authentication failed`. Lý do?** (gợi ý: PAT vs password)
4. **Khi nào nên rebase, khi nào nên merge?** (gợi ý: linear history vs preserve branch)

---

## G. Update PROGRESS.md

Khi push lên GitHub thành công + có 1 branch `feat/01-sap-source-design`:
- Step 0.2 → `done`
- Step 1.1 (SAP source design) → `**next**`
- Thêm vào *Artifacts*: link GitHub repo

---

## H. Báo done

Mở chat mới gõ:
> *"Đọc PROGRESS.md. Step 0.2 done, link repo: github.com/&lt;user&gt;/supplypulse. Đẩy tôi qua Step 1.1."*
