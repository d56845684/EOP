#!/bin/bash
# 打包 + 部署 Lambda: eop-notification-email-sender
# 使用方式:
#   bash deploy.sh --profile EOP-admin-dennis   # 直接指定
#   bash deploy.sh                               # 互動式選擇
set -euo pipefail

FUNCTION_NAME="eop-notification-email-sender"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
ZIP_FILE="$SCRIPT_DIR/function.zip"
ENV_FILE="$SCRIPT_DIR/.env.lambda"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ── AWS Profile 選擇 ──
source "$PROJECT_ROOT/scripts/aws-profile-select.sh" "$@"

# ── 檢查 .env.lambda ──
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: 找不到 $ENV_FILE"
  echo "請複製 .env.lambda.example 為 .env.lambda 並填入 Lambda 環境變數"
  exit 1
fi

load_env_var() {
  grep "^$1=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d'=' -f2-
}

AWS_REGION=$(load_env_var "AWS_REGION")
AWS_REGION="${AWS_REGION:-ap-northeast-1}"

SES_SENDER_EMAIL=$(load_env_var "SES_SENDER_EMAIL")

if [ -z "$SES_SENDER_EMAIL" ]; then
  echo "ERROR: .env.lambda 缺少 SES_SENDER_EMAIL"; exit 1
fi

echo "=== Lambda Deploy: $FUNCTION_NAME ==="
echo "Region:       $AWS_REGION"
echo "SES Sender:   $SES_SENDER_EMAIL"
echo ""

# ── Step 1: 打包 ──
echo "--- Step 1: 打包 ---"
rm -rf "$BUILD_DIR" "$ZIP_FILE"
mkdir -p "$BUILD_DIR"

# 此 Lambda 無額外依賴（boto3 由 Lambda runtime 內建）
cp "$SCRIPT_DIR/lambda_function.py" "$BUILD_DIR/"

cd "$BUILD_DIR"
zip -r "$ZIP_FILE" . -q
echo "打包完成: $(du -h "$ZIP_FILE" | cut -f1)"

# ── Step 2: 更新程式碼 ──
echo ""
echo "--- Step 2: 更新程式碼 ---"
aws $AWS_OPTS lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --zip-file "fileb://$ZIP_FILE" \
  --region "$AWS_REGION" \
  --no-cli-pager

echo "等待 Lambda 更新完成..."
aws $AWS_OPTS lambda wait function-updated \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" 2>/dev/null || sleep 5

# ── Step 3: 更新環境變數 ──
echo ""
echo "--- Step 3: 更新環境變數 ---"
aws $AWS_OPTS lambda update-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --environment "{
    \"Variables\": {
      \"SES_SENDER_EMAIL\": \"$SES_SENDER_EMAIL\"
    }
  }" \
  --no-cli-pager

# ── 清理 ──
rm -rf "$BUILD_DIR"

echo ""
echo "=== 部署完成 ==="
