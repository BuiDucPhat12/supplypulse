# Notes 02 — Git workflow, Conventional Commits, GitHub, pre-commit (Step 0.2)

> Mục đích: ôn tập + cheatsheet phỏng vấn cho mọi thứ liên quan tới Git workflow.
> Format: vì sao → khái niệm → command → câu hỏi phỏng vấn.

---

## 1. Git là gì? Vì sao Git thắng SVN/CVS?

**Git** = Distributed Version Control System (DVCS) do Linus Torvalds viết năm 2005 cho Linux kernel.

| | Git (DVCS) | SVN/CVS (Centralized VCS) |
|---|---|---|
| Repo | Mỗi máy có **full history** | Chỉ server có history |
| Commit khi mất mạng | ✅ được, push sau | ❌ phải online |
| Branch | Cheap, milisec, ai cũng tạo | Đắt, ít dùng |
| Tốc độ | Nhanh (local op) | Chậm (network mỗi lần) |
| Workflow | Linh hoạt: trunk, gitflow, fork-based... | Cố định, top-down |

→ Git win vì *(1)* offline-first, *(2)* branch rẻ, *(3)* phù hợp open-source (fork → PR).

---

## 2. 3 cấu trúc dữ liệu cốt lõi của Git

| Object | Vai trò | Ví dụ |
|---|---|---|
| **Blob** | Lưu nội dung 1 file (binary blob) | content của `README.md` |
| **Tree** | Snapshot của 1 folder (chứa blobs + sub-trees) | snapshot folder `supplypulse/` |
| **Commit** | Snapshot toàn project tại 1 thời điểm + parent + author + message | commit hash `a1b2c3d` |

**Hash:** mỗi object có ID là SHA-1 (hoặc SHA-256 ở bản mới) của content. → Immutability + integrity.

**Branch** = chỉ là *con trỏ* đến 1 commit. Tạo branch = tạo file 41 byte. **Đó là vì sao branch trong Git rẻ.**

---

## 3. Conventional Commits — chuẩn hoá commit message

### Vì sao quan trọng (recruiter signal)

- ✅ Recruiter scroll commit history → thấy `feat`, `fix`, `chore` → bạn pro
- ✅ Tự động generate CHANGELOG (tools: `standard-version`, `release-please`)
- ✅ Auto bump semantic version (`feat:` → minor, `fix:` → patch, `BREAKING CHANGE:` → major)
- ❌ Random message *"asdf"*, *"update"*, *"fix bug"* → newbie signal

### Format đầy đủ

```
<type>(<scope>): <subject>

<body>

<footer>
```

- **type** (bắt buộc): 1 trong 7 type ở dưới
- **scope** (tuỳ chọn): module/folder ảnh hưởng (vd `dbt`, `api`, `simulator`)
- **subject** (bắt buộc): ngắn ≤ 72 ký tự, imperative ("add" không "added"), không chấm cuối
- **body** (tuỳ chọn): giải thích *vì sao*, không phải *làm gì*
- **footer** (tuỳ chọn): `BREAKING CHANGE:`, `Closes #123`, `Co-authored-by:`

### 7 type chính + ví dụ

| Type | Ý nghĩa | Ví dụ tốt |
|---|---|---|
| `feat` | Feature mới | `feat(dbt): add mart_supplier_otd model` |
| `fix` | Sửa bug | `fix(loader): prevent duplicate inserts on retry` |
| `docs` | Docs only | `docs(architecture): add Azure mapping table` |
| `chore` | Việc lặt vặt (config, deps, build) | `chore: bump dbt to 1.7.4` |
| `refactor` | Đổi structure không đổi behavior | `refactor(api): split routes into modules` |
| `test` | Thêm/sửa test | `test(loader): cover idempotency case` |
| `ci` | Sửa CI/CD | `ci: cache uv deps in github actions` |

### Type ít gặp hơn (nên biết)

| Type | Khi nào |
|---|---|
| `perf` | Tối ưu performance |
| `style` | Format code (rất hiếm vì pre-commit lo rồi) |
| `build` | Sửa build system (Dockerfile, Makefile) |
| `revert` | Revert commit cũ (`git revert`) |

### BREAKING CHANGE

Commit có thay đổi không tương thích phải đánh dấu rõ:

```
feat(api)!: switch /forecast to v2 schema

BREAKING CHANGE: response field `prediction` renamed to `yhat`.
```

→ Tools tự bump major version (1.x.x → 2.0.0).

### Anti-patterns

❌ `Update files` — không cho biết update gì
❌ `Fixed bug` — bug nào?
❌ `feat: added new feature` — quá generic
❌ `WIP` — không bao giờ commit WIP lên main

---

## 4. Branch strategy

### 4.1 Ba strategy phổ biến

#### a. Trunk-based (recommend cho project nhỏ + solo dev — chọn cho SupplyPulse)

```
main: ────●────●────●────●────●────●────►
              \       /  \         /
              feat/A     feat/B
```

- Branch `main` luôn deploy được
- Feature branch sống ngắn (≤3 ngày), merge xong xoá ngay
- Không có long-lived branch

#### b. GitHub Flow

Giống trunk-based + bắt buộc PR review trước merge. Tốt cho team 5-20 người.

#### c. GitFlow (cũ, phức tạp)

```
main      ────●────────────●─────►
develop   ──●────●────●────●────►
              \      /
              feat/X
              \
              release/1.0
              \
              hotfix/1.0.1
```

- 5+ branch (main, develop, feat, release, hotfix)
- Phù hợp release theo version (vd software trên-prem có version riêng)
- **Overkill cho web/cloud** → ngày càng ít team dùng

### 4.2 Naming convention branch

| Prefix | Khi nào |
|---|---|
| `feat/` | Tính năng mới — `feat/01-sap-source-design` |
| `fix/` | Bug fix — `fix/loader-duplicate-rows` |
| `docs/` | Chỉ docs — `docs/architecture-update` |
| `chore/` | Config, deps — `chore/bump-uv` |
| `refactor/` | Refactor — `refactor/split-api-routes` |

Số đầu (vd `01-`) optional, giúp sort thứ tự visually.

---

## 5. `.gitignore` — patterns cần thuộc

### Quy tắc cơ bản

```gitignore
# Comment

# Ignore file cụ thể
.env
secrets.yaml

# Ignore extension
*.pyc
*.log

# Ignore folder (anywhere)
__pycache__/
.venv/
node_modules/

# Ignore folder ở root only
/build/

# Negate (không ignore)
*.log
!important.log

# Wildcard
data/raw/*.csv
docs/**/*.tmp
```

### Bắt buộc trong Python project

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.mypy_cache/
*.egg-info/
.env
.coverage
htmlcov/
```

### Bắt buộc cho data project

```gitignore
data/raw/
data/processed/
*.parquet
*.duckdb
*.csv         # cẩn thận, có thể bạn muốn commit 1 vài seed CSV
mlruns/
```

### Quy tắc vàng

> **Khi nghi ngờ → ignore.** Commit nhầm `.env` chứa API key = thảm hoạ. Có nhiều bot scan GitHub leak credentials trong vài phút.

→ Dùng `git secrets` hoặc `detect-private-key` hook (đã có trong pre-commit của bạn) để chặn.

---

## 6. GitHub authentication — 3 cách + so sánh

| Cách | Khi nào | Pros | Cons |
|---|---|---|---|
| **OAuth qua GCM** (recommend) | Laptop cá nhân Windows | Click 1 lần là xong, GCM tự refresh token | Cần browser |
| **PAT thủ công** | CI/CD, server không có browser | Universal, không phụ thuộc GCM | Phải tạo + rotate thủ công, dễ leak |
| **SSH key** | Power user, dùng nhiều máy | Không cần password mỗi push, nhanh | Setup hơi rườm, phải copy public key lên GitHub |

### Git Credential Manager (GCM) hoạt động sao?

1. Bạn `git push` lần đầu
2. Git Credential Manager intercept request
3. Mở browser → trang OAuth của GitHub
4. Bạn login web bình thường + click Authorize
5. GitHub trả về **OAuth token** (1 dạng PAT do server tạo)
6. GCM lưu token vào **Windows Credential Manager** (mã hoá DPAPI)
7. Lần push sau: GCM đọc token từ Credential Manager → push thẳng, không hỏi

→ Bản chất: **GCM tạo PAT giúp bạn**, lưu giúp, refresh giúp. Bạn chỉ login web 1 lần.

### Khi nào MỚI cần PAT thủ công

- CI/CD (GitHub Actions push từ container)
- Server SSH-less (build server, scheduler)
- Browser flow fail (proxy doanh nghiệp chặn OAuth)

### Lệnh kiểm tra credential helper

```powershell
git config --global credential.helper
# Output: manager hoặc manager-core → đang dùng GCM
```

---

## 7. pre-commit framework

### 7.1 Là gì?

`pre-commit` (Python package) là framework chạy **hook scripts** trước mỗi `git commit`. Mỗi hook là 1 check (lint, format, security scan...). Nếu hook fail → block commit.

### 7.2 Git hooks 101

Git native có 13 hooks ở `.git/hooks/`:

| Hook | Khi chạy |
|---|---|
| `pre-commit` | Trước khi commit (chính) |
| `commit-msg` | Sau khi nhập message, trước khi commit (vd validate Conventional Commit) |
| `pre-push` | Trước khi push lên remote |
| `post-merge` | Sau khi merge (vd auto chạy `uv sync`) |
| `prepare-commit-msg` | Trước khi editor mở để bạn nhập message |
| `pre-rebase`, `post-checkout`, ... | Ít dùng |

→ Hook native chỉ là shell script trong `.git/hooks/`. **Khó share với team** (vì `.git/` không track Git).

→ Framework `pre-commit` (Python) giải quyết: config trong `.pre-commit-config.yaml` (commit lên Git), `pre-commit install` setup hook script tự động.

### 7.3 Cấu trúc `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.10                     # version pin (KHÔNG dùng "latest")
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

- `repo`: GitHub repo của hook
- `rev`: pin version cho reproducibility (giống lock file)
- `hooks.id`: tên hook (xem trong `.pre-commit-hooks.yaml` của repo đó)
- `args`: args truyền cho hook

### 7.4 Hooks tốt thường dùng

#### Pre-commit hooks built-in (`pre-commit/pre-commit-hooks`)

| Hook | Tác dụng |
|---|---|
| `end-of-file-fixer` | File phải kết thúc bằng newline |
| `trailing-whitespace` | Xoá space cuối dòng |
| `check-yaml` / `check-toml` / `check-json` | Parse OK |
| `check-added-large-files` | Chặn file > X KB |
| `check-merge-conflict` | Chặn `<<<<<<<` markers |
| `detect-private-key` | Chặn SSH/PEM key |
| `mixed-line-ending` | Force LF/CRLF nhất quán |

#### Python hooks

| Repo | Hook | Tác dụng |
|---|---|---|
| `astral-sh/ruff-pre-commit` | `ruff`, `ruff-format` | Lint + format |
| `psf/black-pre-commit-mirror` | `black` | Format (backup) |
| `pre-commit/mirrors-mypy` | `mypy` | Type check |
| `PyCQA/bandit` | `bandit` | Security audit |

### 7.5 Lifecycle

```
git commit
    ↓
pre-commit hooks chạy
    ↓
Pass? → tiếp tục commit
Fail? → chặn lại, in lỗi
   ↓
Auto-fix nếu có (vd ruff-fix)
   ↓
Bạn `git add` lại file đã fix → commit lại
```

### 7.6 Bypass hook (chỉ khi cần thiết)

```bash
git commit --no-verify -m "wip: trying something"
```

→ Skip toàn bộ pre-commit. **Đừng lạm dụng** — bạn sẽ commit code dở.

---

## 8. Pull Request workflow (kể cả khi solo)

### Vì sao solo dev cũng nên dùng PR?

1. **Code review tự thân:** mở PR, đọc lại diff trên GitHub UI → bắt được bug tốt hơn xem trên IDE
2. **CI run trước merge:** GitHub Actions test pass mới merge → main luôn xanh
3. **History rõ ràng:** mỗi PR = 1 unit công việc, dễ revert
4. **Practice cho team setting:** quen workflow trước khi đi làm

### Quy trình chuẩn

```
1. git checkout -b feat/01-sap-source-design
2. ... làm việc ...
3. git add . && git commit -m "feat(docs): add SAP source design"
4. git push -u origin feat/01-sap-source-design
5. Trên GitHub: click "Compare & Pull Request"
6. Viết PR description (tự đọc lại diff)
7. Đợi CI xanh
8. Click "Squash and merge" hoặc "Rebase and merge"
9. Xoá branch
10. git checkout main && git pull
```

### Squash vs Rebase vs Merge (interview question)

| Strategy | Kết quả |
|---|---|
| **Merge commit** | Giữ nguyên history nhánh + 1 merge commit | History "branchy", có thể rối |
| **Squash merge** | Tất cả commit nhánh gom thành 1 commit duy nhất trên main | History sạch, mất chi tiết từng commit |
| **Rebase + fast-forward** | Đặt commit nhánh trên đầu main, linear history | Sạch nhất, nhưng rewrite history (cần care) |

**Recommendation cho solo dev:** Squash merge — main rất sạch, mỗi feature 1 commit có message Conventional.

---

## 9. Semantic Versioning (SemVer)

### Format: `MAJOR.MINOR.PATCH`

```
2.4.1
│ │ └── PATCH: bug fix, không thay API
│ └──── MINOR: thêm feature, backward compatible
└────── MAJOR: breaking change
```

### Map từ Conventional Commit

| Commit | Version bump |
|---|---|
| `fix:` | PATCH (1.0.0 → 1.0.1) |
| `feat:` | MINOR (1.0.0 → 1.1.0) |
| `feat!:` hoặc `BREAKING CHANGE:` footer | MAJOR (1.0.0 → 2.0.0) |
| `chore:`, `docs:`, `test:`, `style:` | Không bump |

### Pre-1.0 special

Versions `0.x.x` được coi là "in development" — API có thể thay đổi bất cứ lúc nào. SupplyPulse hiện ở `0.1.0` → `0.2.0` trong Phase 1.

---

## 10. Daily Git commands cheatsheet

### Status / inspect

```bash
git status                          # state hiện tại
git log --oneline                   # history compact
git log --graph --all --oneline     # đẹp + thấy branch
git diff                            # change chưa stage
git diff --staged                   # change đã stage
git show HEAD                       # commit gần nhất
git blame file.py                   # ai sửa dòng nào
```

### Stage / commit

```bash
git add file.py                     # stage 1 file
git add .                           # stage all
git add -p                          # interactive: pick từng hunk
git commit -m "feat: ..."           # commit
git commit --amend                  # sửa commit cuối (chưa push)
```

### Branch

```bash
git branch                          # list local
git branch -a                       # list all (kèm remote)
git checkout -b feat/x              # tạo + switch
git switch feat/x                   # switch (lệnh mới, rõ nghĩa hơn)
git branch -d feat/x                # xoá local
git push origin --delete feat/x     # xoá remote
```

### Sync với remote

```bash
git fetch                           # tải về, không merge
git pull                            # = fetch + merge (cẩn thận!)
git pull --rebase                   # = fetch + rebase (linear history)
git push                            # push current branch
git push -u origin feat/x           # push lần đầu, set upstream
```

### Undo

```bash
git restore file.py                 # discard change chưa stage
git restore --staged file.py        # unstage
git reset HEAD~1                    # undo 1 commit cuối, giữ change
git reset --hard HEAD~1             # undo + xoá change (DANGEROUS)
git revert <hash>                   # tạo commit ngược (an toàn)
```

### Stash (lưu tạm work)

```bash
git stash                           # cất change đang làm dở
git stash pop                       # lấy ra
git stash list                      # xem stash
```

---

## 11. Common pitfalls + fixes

### 11.1 Lỡ commit `.env` chứa secret

```bash
# Xoá file khỏi history (rewrite, force push)
pip install git-filter-repo
git filter-repo --path .env --invert-paths
git push --force
```

→ **Sau đó BẮT BUỘC rotate secret đó** (assume nó đã leak).

### 11.2 Commit nhầm vào main thay vì feature branch

```bash
git checkout -b feat/x              # tạo branch tại commit hiện tại
git checkout main
git reset --hard HEAD~1             # main lùi 1 commit
git checkout feat/x
```

### 11.3 Pre-commit hook bị stuck "Initializing environment"

```bash
pre-commit clean                    # xoá cache
pre-commit install --install-hooks  # reinstall
```

### 11.4 `git push` báo `rejected (non-fast-forward)`

→ Remote đã có commit mới mà local chưa có.

```bash
git pull --rebase origin main
# Resolve conflict nếu có
git push
```

---

## 12. Self-check Q&A — phỏng vấn ready

### Q1. 7 type chính trong Conventional Commits?

`feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci` (+ optional: `perf`, `style`, `build`, `revert`).

### Q2. Vì sao `pre-commit` chạy được trước `git commit`?

Vì `pre-commit install` đã ghi 1 script vào `.git/hooks/pre-commit`. Git native sẽ chạy mọi script ở đường dẫn đó **trước khi commit thực sự được tạo**. Nếu script exit code != 0, commit bị abort.

### Q3. Lần đầu push GitHub bị `Authentication failed`. Lý do?

3 khả năng:
1. Đang dùng password GitHub (không còn được support từ 2021)
2. PAT hết hạn
3. Git Credential Manager chưa setup → `git config --global credential.helper` rỗng

### Q4. Khi nào nên rebase, khi nào nên merge?

- **Rebase** khi: cập nhật feature branch với main mới nhất (giữ history linear), trước khi mở PR
- **Merge** khi: integrate PR vào main (merge commit hoặc squash merge, KHÔNG rebase nhánh đã share với người khác)
- **Quy tắc vàng:** đừng rebase nhánh đã push public (rewrite history phá người khác)

### Q5 (follow-up). Khác biệt `git fetch` vs `git pull`?

`git fetch` chỉ tải data từ remote về local, không merge. `git pull` = `fetch` + `merge` (hoặc rebase nếu config). `pull` tiện nhưng đôi khi merge tự động không như ý → seniors thường `fetch` rồi inspect trước.

### Q6 (follow-up). `git reset --hard` vs `git revert`?

- `reset --hard` rewrite history (xoá commit), nguy hiểm nếu commit đã push
- `revert` tạo commit ngược, history vẫn còn cả 2, an toàn cho shared branch

### Q7 (follow-up). Squash merge có nhược điểm gì?

Mất chi tiết từng commit trong feature branch. Khi cần debug bug "tại commit nào" sẽ khó hơn. Trade-off: history main sạch nhưng mất granularity.

### Q8 (follow-up). Vì sao lock version hook trong `.pre-commit-config.yaml`?

Reproducibility. Nếu để `rev: latest`, mỗi máy clone về có thể fetch hook version khác → behavior khác. Pin version giống pin package → ai chạy cũng giống nhau.

---

## 13. TL;DR — 1 đoạn nhớ thuộc

> Git là DVCS — mỗi máy có full history, branch siêu rẻ vì branch chỉ là pointer. **Conventional Commits** (`feat/fix/docs/chore/refactor/test/ci`) chuẩn hoá commit message, tự động bump SemVer, là *cheap signal* mạnh với recruiter. **Branch strategy** chọn trunk-based với feature branch ngắn cho project nhỏ. **GitHub auth** dùng OAuth qua Git Credential Manager (browser flow), không cần PAT thủ công trên laptop. **pre-commit** framework chạy hook trước commit, chặn code dở; pin version hook trong `.pre-commit-config.yaml`. **PR workflow** kể cả solo dev — code review chính mình + CI gate. **Daily commands**: `add` / `commit` / `push` / `pull --rebase` / `switch` / `restore`.

---

## 14. Đọc thêm

- **Git book free:** https://git-scm.com/book/en/v2
- **Conventional Commits spec:** https://www.conventionalcommits.org/
- **SemVer spec:** https://semver.org/
- **pre-commit docs:** https://pre-commit.com/
- **GitHub Flow:** https://docs.github.com/en/get-started/quickstart/github-flow
- **Pro tip:** đọc bài *"How to Write a Git Commit Message"* by Chris Beams — kinh điển 5 phút.
