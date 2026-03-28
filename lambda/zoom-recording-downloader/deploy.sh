#!/bin/bash
# 打包 + 部署 Lambda: zoom-recording-downloader
# 所有設定（AWS 憑證 + Lambda 環境變數）從 .env.lambda 讀取
# 不依賴本地 ~/.aws/config
set -euo pipefail

FUNCTION_NAME="zoom-recording-downloader"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
ZIP_FILE="$SCRIPT_DIR/function.zip"
ENV_FILE="$SCRIPT_DIR/.env.lambda"

# ── 檢查 .env.lambda ──
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: 找不到 $ENV_FILE"
  echo "請複製 .env.lambda.example 為 .env.lambda 並填入實際值："
  echo "  cp .env.lambda.example .env.lambda"
  exit 1
fi

# 讀取 .env.lambda（忽略註解和空行）
load_env_var() {
  grep "^$1=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d'=' -f2-
}

# ── 讀取 AWS 設定 ──
export AWS_ACCESS_KEY_ID=$(load_env_var "AWS_ACCESS_KEY_ID")
export AWS_SECRET_ACCESS_KEY=$(load_env_var "AWS_SECRET_ACCESS_KEY")
AWS_REGION=$(load_env_var "AWS_REGION")
AWS_REGION="${AWS_REGION:-ap-northeast-1}"

if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
  echo "ERROR: .env.lambda 缺少 AWS_ACCESS_KEY_ID 或 AWS_SECRET_ACCESS_KEY"
  exit 1
fi

# ── 讀取 Lambda 環境變數 ──
GOOGLE_DRIVE_FOLDER_ID=$(load_env_var "GOOGLE_DRIVE_FOLDER_ID")
GOOGLE_SA_CREDENTIALS=$(load_env_var "GOOGLE_SA_CREDENTIALS")

if [ -z "$GOOGLE_DRIVE_FOLDER_ID" ]; then
  echo "ERROR: .env.lambda 缺少 GOOGLE_DRIVE_FOLDER_ID"
  exit 1
fi
if [ -z "$GOOGLE_SA_CREDENTIALS" ]; then
  echo "ERROR: .env.lambda 缺少 GOOGLE_SA_CREDENTIALS"
  exit 1
fi

echo "=== Lambda Deploy: $FUNCTION_NAME ==="
echo "Region:       $AWS_REGION"
echo "AWS Key:      ${AWS_ACCESS_KEY_ID:0:8}..."
echo "Drive Folder: $GOOGLE_DRIVE_FOLDER_ID"
echo "SA Creds:     $(echo "$GOOGLE_SA_CREDENTIALS" | cut -c1-20)... ($(echo -n "$GOOGLE_SA_CREDENTIALS" | wc -c | tr -d ' ') bytes)"
echo ""

# ── Step 1: 打包 ──
echo "--- Step 1: 打包 ---"
rm -rf "$BUILD_DIR" "$ZIP_FILE"
mkdir -p "$BUILD_DIR"

pip install -r "$SCRIPT_DIR/requirements.txt" -t "$BUILD_DIR" --quiet
cp "$SCRIPT_DIR/handler.py" "$BUILD_DIR/"

cd "$BUILD_DIR"
zip -r "$ZIP_FILE" . -q
echo "打包完成: $(du -h "$ZIP_FILE" | cut -f1)"

# ── Step 2: 更新程式碼 ──
echo ""
echo "--- Step 2: 更新程式碼 ---"
aws lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --zip-file "fileb://$ZIP_FILE" \
  --region "$AWS_REGION" \
  --no-cli-pager

echo "等待 Lambda 更新完成..."
aws lambda wait function-updated \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" 2>/dev/null || sleep 5

# ── Step 3: 更新環境變數 ──
echo ""
echo "--- Step 3: 更新環境變數 ---"
aws lambda update-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --environment "{
    \"Variables\": {
      \"GOOGLE_DRIVE_FOLDER_ID\": \"$GOOGLE_DRIVE_FOLDER_ID\",
      \"GOOGLE_SA_CREDENTIALS\": \"$GOOGLE_SA_CREDENTIALS\"
    }
  }" \
  --no-cli-pager

# ── 清理 ──
rm -rf "$BUILD_DIR"

echo ""
echo "=== 部署完成 ==="
