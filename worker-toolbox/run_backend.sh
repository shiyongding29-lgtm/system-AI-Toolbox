#!/bin/bash
cd "$(dirname "$0")"

# 加载 .env 文件
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# 检查必需的环境变量
if [ -z "$OPENAI_API_KEY" ]; then
  echo "ERROR: OPENAI_API_KEY not set. Create .env file or export the variable."
  exit 1
fi

export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.deepseek.com/v1}"
export OPENAI_MODEL="${OPENAI_MODEL:-deepseek-chat}"

echo "OPENAI_BASE_URL=$OPENAI_BASE_URL"
echo "OPENAI_MODEL=$OPENAI_MODEL"
echo "OPENAI_API_KEY=${OPENAI_API_KEY:0:12}..."

# 默认不启用热重载（--reload 在 macOS 上多次引发 reloader 卡死/死锁）。
# 需要开发热重载时用：RELOAD=1 bash run_backend.sh
RELOAD_FLAG=""
if [ "${RELOAD:-0}" = "1" ]; then
  RELOAD_FLAG="--reload"
  echo "已启用热重载 (RELOAD=1)"
else
  echo "热重载已关闭（改动 .py 后需手动重启）"
fi

/opt/anaconda3/bin/python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 $RELOAD_FLAG
