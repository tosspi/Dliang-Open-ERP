@echo off
REM 大亮ERP：在已创建 .venv 的前提下启动 Uvicorn（适合任务计划程序「开机/登录启动」）。
REM 手动开发调试请仍用 README 中的 uvicorn ... --reload
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\activate.bat" (
  echo [错误] 未找到 .venv\Scripts\activate.bat
  echo 请先在项目根目录执行: python -m venv .venv
  echo 并安装依赖: pip install -r requirements.txt
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
uvicorn app.main:app --host 0.0.0.0 --port 8000
