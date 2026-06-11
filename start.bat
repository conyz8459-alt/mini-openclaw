@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  Mini-OpenClaw 一键启动（Windows）
REM  自动：建虚拟环境 -> 装后端依赖 -> 检查 .env -> 装前端依赖
REM       -> 同时拉起后端(8002) 与 前端(3000)
REM ============================================================

cd /d "%~dp0"
echo [Mini-OpenClaw] 启动中...
echo.

REM ---------- 1. 后端：虚拟环境 ----------
if not exist "backend\.venv" (
    echo [1/5] 创建 Python 虚拟环境...
    python -m venv backend\.venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败，请确认已安装 Python 3.10+ 并加入 PATH。
        pause
        exit /b 1
    )
) else (
    echo [1/5] 已存在虚拟环境，跳过创建。
)

REM ---------- 2. 后端：安装依赖 ----------
echo [2/5] 安装后端依赖（首次较慢，请耐心等待）...
call backend\.venv\Scripts\activate.bat
python -m pip install -q --upgrade pip
python -m pip install -q -r backend\requirements.txt
if errorlevel 1 (
    echo [错误] 后端依赖安装失败。
    pause
    exit /b 1
)

REM ---------- 3. 检查 .env ----------
if not exist "backend\.env" (
    echo [3/5] 未找到 backend\.env，正在从模板复制...
    copy /y "backend\.env.example" "backend\.env" >nul
    echo.
    echo ============================================================
    echo  请先编辑 backend\.env，填入你的模型 API Key（LLM_API_KEY），
    echo  然后重新运行本脚本。
    echo ============================================================
    pause
    exit /b 0
) else (
    echo [3/5] 已存在 backend\.env。
)

REM ---------- 4. 前端：安装依赖 ----------
if not exist "frontend\node_modules" (
    echo [4/5] 安装前端依赖（使用国内镜像源加速）...
    pushd frontend
    call npm install --registry=https://registry.npmmirror.com
    popd
    if errorlevel 1 (
        echo [错误] 前端依赖安装失败，请确认已安装 Node.js 18+。
        pause
        exit /b 1
    )
) else (
    echo [4/5] 前端依赖已存在，跳过安装。
)

REM ---------- 5. 同时启动前后端 ----------
echo [5/5] 启动服务...
echo   后端: http://localhost:8002
echo   前端: http://localhost:3000
echo.
start "Mini-OpenClaw Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate.bat && python app.py"
start "Mini-OpenClaw Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo 已在两个新窗口分别启动前后端。
echo 等待几秒后，浏览器打开 http://localhost:3000 即可使用。
echo （关闭那两个窗口即可停止服务）
pause
