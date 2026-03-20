#!/bin/bash
# 打包 + 部署 Lambda: zoom-recording-downloader
set -euo pipefail

FUNCTION_NAME="zoom-recording-downloader"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
ZIP_FILE="$SCRIPT_DIR/function.zip"

echo "=== 開始打包 Lambda: $FUNCTION_NAME ==="

# 清理
rm -rf "$BUILD_DIR" "$ZIP_FILE"
mkdir -p "$BUILD_DIR"

# 安裝依賴
pip install -r "$SCRIPT_DIR/requirements.txt" -t "$BUILD_DIR" --quiet

# 複製 handler
cp "$SCRIPT_DIR/handler.py" "$BUILD_DIR/"

# 打包
cd "$BUILD_DIR"
zip -r "$ZIP_FILE" . -q

echo "=== 打包完成: $(du -h "$ZIP_FILE" | cut -f1) ==="

# 部署
echo "=== 部署至 AWS Lambda ==="
aws lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --zip-file "fileb://$ZIP_FILE" \
  --no-cli-pager

echo "=== 部署完成 ==="

# 清理 build
rm -rf "$BUILD_DIR"
