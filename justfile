# study_vector — 顶层 just 命令集
#
# 跨语言编排：检查工具链 / 启停 / 验证 / 状态查询
# 各子项目自己的命令请进入对应目录用 just（如 backends/python/justfile）
#
# 常用：
#   just                    # 列出所有顶层 recipe
#   just check              # 验证工具链
#   just init               # 全量安装依赖
#   just dev-api            # 启动后端（前台）
#   just dev-ui             # 启动前端（前台）
#   just status             # 看所有服务状态
#   just verify             # 跑完整验收（lint + test + e2e）
#
# Windows 注意事项：
#   * just 默认每行启动一个独立 PowerShell 进程，所以 `Push-Location / cmd / Pop-Location`
#     三行写法**不能**让目录状态延续到下一行。
#   * 因此涉及"切目录后跑子命令"的 recipe 全部写成**单行**，用 `;` 把多个 PowerShell
#     语句拼到同一次 `-Command` 调用里——同一进程内状态会延续。
#   * 之前试过的 `set windows-powershell := true` 在 just 1.53.0 上无效（已被官方 deprecate）。

set shell := ["powershell.exe", "-NoProfile", "-Command"]

# ───────────────────────── 默认 ─────────────────────────
default:
    @just --list

# ───────────────────────── 工具链 ─────────────────────────

# 验证工具链是否就绪
check:
    python scripts/check_toolchain.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# ───────────────────────── 网络编排（Milvus） ─────────────────────────

# 创建 study_vector_study_vector_net 网络
create-network:
    docker network create study_vector_study_vector_net 2>&1 | Out-Null
    Write-Host "✅ 网络 study_vector_study_vector_net 已就绪" -ForegroundColor Green

# 启动 Milvus（用本仓库的 compose）；如果 Milvus 已存在则跳过
milvus-up:
    Push-Location deploy; try { docker compose up -d milvus etcd minio 2>&1 | Out-Null } catch { Write-Host "（Milvus 容器已存在或启动失败，可忽略）" -ForegroundColor Yellow }; Pop-Location
    Write-Host "💡 若要检查 Milvus 健康，单独运行：docker ps --filter name=milvus" -ForegroundColor Cyan

# ───────────────────────── 初始化 / 安装 ─────────────────────────

# 全量安装（Python 依赖 + 前端依赖 + 后端 .env）
init: check
    Write-Host "📦 安装后端依赖…" -ForegroundColor Cyan
    Push-Location backends/python; just init; Pop-Location
    Write-Host "📦 安装前端依赖…" -ForegroundColor Cyan
    Push-Location frontend; npm install 2>&1 | Select-Object -Last 5; Pop-Location
    Write-Host "✅ 全部依赖就绪" -ForegroundColor Green

# 只安装后端
init-api:
    Push-Location backends/python; just init; Pop-Location

# 只安装前端
init-ui:
    Push-Location frontend; npm install 2>&1 | Select-Object -Last 5; Pop-Location

# ───────────────────────── 开发态启停 ─────────────────────────

# 启动后端（开发模式，宿主演示）
dev-api:
    Push-Location backends/python; just run; Pop-Location

# 启动前端（开发模式）
dev-ui:
    Push-Location frontend; npm run dev -- --host 127.0.0.1 --port 5173; Pop-Location

# ───────────────────────── 测试 / 验证 ─────────────────────────

# 跑后端测试
test-api:
    Push-Location backends/python; just test; Pop-Location

# 跑前端 E2E（依赖 dev-api + dev-ui 已起）
e2e:
    Push-Location frontend; node e2e/smoke.mjs; Pop-Location

# 完整验收：后端 lint+test + 前端 E2E
verify: check
    Write-Host "▶ 后端 lint + test…" -ForegroundColor Cyan
    Push-Location backends/python; just ci; Pop-Location
    Write-Host "▶ 前端 E2E…" -ForegroundColor Cyan
    Push-Location frontend; node e2e/smoke.mjs; Pop-Location
    Write-Host "✅ 全部验收通过" -ForegroundColor Green

# ───────────────────────── 状态 / 停止 ─────────────────────────

# 显示所有服务状态
status:
    Write-Host ""
    Write-Host "▶ Docker 容器" -ForegroundColor Cyan
    docker ps --filter "name=milvus" --filter "name=study_vector" 2>&1 | Out-String
    Write-Host ""
    Write-Host "▶ API 探活" -ForegroundColor Cyan
    try { (Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -UseBasicParsing -TimeoutSec 3).Content | Out-String } catch { Write-Host "  API 未运行" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "▶ 集合列表" -ForegroundColor Cyan
    try { $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/collections" -UseBasicParsing -TimeoutSec 3; $resp.Content.Substring(0, [Math]::Min(300, $resp.Content.Length)) | Out-String } catch { Write-Host "  （取不到集合列表）" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "▶ 前端探活" -ForegroundColor Cyan
    try { $__r = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 3; Write-Host ("  http://127.0.0.1:5173  HTTP=" + $__r.StatusCode) -ForegroundColor Green } catch { Write-Host "  前端未运行" -ForegroundColor Yellow }

# 停所有 study_vector 启动的容器
stop:
    docker rm -f study_vector_api 2>&1 | Out-Null
    docker rm -f study_vector_frontend 2>&1 | Out-Null
    Write-Host "✅ 已停 study_vector 容器" -ForegroundColor Green

# ───────────────────────── Docker 化部署 ─────────────────────────

# 用 Docker 编排启动整套（milvus + api + frontend）
up:
    Push-Location deploy; docker compose up -d; Pop-Location
    Write-Host "✅ 已启动 deploy/docker-compose.yml 全部服务" -ForegroundColor Green

# 用 Docker 编排停整套
down:
    Push-Location deploy; docker compose down; Pop-Location
    Write-Host "✅ 已停 deploy/docker-compose.yml 全部服务" -ForegroundColor Green
