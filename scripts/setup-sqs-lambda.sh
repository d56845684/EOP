#!/bin/bash
# 建立 AWS 資源：SQS Queue + DLQ + IAM Role + Lambda
# 使用前請確認已設定 AWS CLI credentials
set -euo pipefail

REGION="${AWS_REGION:-ap-northeast-1}"
FUNCTION_NAME="zoom-recording-downloader"
QUEUE_NAME="zoom-recording-download"
DLQ_NAME="zoom-recording-download-dlq"
ROLE_NAME="zoom-recording-lambda-role"

echo "=== Region: $REGION ==="

# 1. 建立 DLQ
echo "--- 建立 DLQ: $DLQ_NAME ---"
DLQ_URL=$(aws sqs create-queue \
  --queue-name "$DLQ_NAME" \
  --region "$REGION" \
  --query 'QueueUrl' --output text 2>/dev/null || true)

if [ -z "$DLQ_URL" ]; then
  DLQ_URL=$(aws sqs get-queue-url --queue-name "$DLQ_NAME" --region "$REGION" --query 'QueueUrl' --output text)
fi
echo "DLQ URL: $DLQ_URL"

DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names QueueArn \
  --region "$REGION" \
  --query 'Attributes.QueueArn' --output text)

# 2. 建立主 Queue（含 redrive policy）
echo "--- 建立主 Queue: $QUEUE_NAME ---"
QUEUE_URL=$(aws sqs create-queue \
  --queue-name "$QUEUE_NAME" \
  --region "$REGION" \
  --attributes "{
    \"VisibilityTimeout\": \"960\",
    \"MessageRetentionPeriod\": \"86400\",
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$DLQ_ARN\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\"
  }" \
  --query 'QueueUrl' --output text 2>/dev/null || true)

if [ -z "$QUEUE_URL" ]; then
  QUEUE_URL=$(aws sqs get-queue-url --queue-name "$QUEUE_NAME" --region "$REGION" --query 'QueueUrl' --output text)
fi
echo "Queue URL: $QUEUE_URL"

QUEUE_ARN=$(aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names QueueArn \
  --region "$REGION" \
  --query 'Attributes.QueueArn' --output text)

# 3. 建立 IAM Role
echo "--- 建立 IAM Role: $ROLE_NAME ---"
TRUST_POLICY='{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}'

ROLE_ARN=$(aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document "$TRUST_POLICY" \
  --query 'Role.Arn' --output text 2>/dev/null || \
  aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)

echo "Role ARN: $ROLE_ARN"

# 附加基本 Lambda 執行 + SQS 權限
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" 2>/dev/null || true

INLINE_POLICY="{
  \"Version\": \"2012-10-17\",
  \"Statement\": [{
    \"Effect\": \"Allow\",
    \"Action\": [
      \"sqs:ReceiveMessage\",
      \"sqs:DeleteMessage\",
      \"sqs:GetQueueAttributes\"
    ],
    \"Resource\": \"$QUEUE_ARN\"
  }]
}"

aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "sqs-receive" \
  --policy-document "$INLINE_POLICY"

echo "等待 IAM Role 生效..."
sleep 10

# 4. 建立 Lambda Function
echo "--- 建立 Lambda: $FUNCTION_NAME ---"
LAMBDA_DIR="$(cd "$(dirname "$0")/../lambda/zoom-recording-downloader" && pwd)"

# 先打包
if [ ! -f "$LAMBDA_DIR/function.zip" ]; then
  echo "請先執行 deploy.sh 打包 Lambda"
  exit 1
fi

aws lambda create-function \
  --function-name "$FUNCTION_NAME" \
  --runtime "python3.12" \
  --role "$ROLE_ARN" \
  --handler "handler.handler" \
  --zip-file "fileb://$LAMBDA_DIR/function.zip" \
  --timeout 900 \
  --memory-size 1024 \
  --ephemeral-storage '{"Size": 2048}' \
  --region "$REGION" \
  --no-cli-pager 2>/dev/null || echo "Lambda 已存在，跳過建立"

# Reserved concurrency
aws lambda put-function-concurrency \
  --function-name "$FUNCTION_NAME" \
  --reserved-concurrent-executions 3 \
  --region "$REGION" \
  --no-cli-pager

# 5. SQS event source mapping
echo "--- 設定 SQS → Lambda 觸發 ---"
aws lambda create-event-source-mapping \
  --function-name "$FUNCTION_NAME" \
  --event-source-arn "$QUEUE_ARN" \
  --batch-size 1 \
  --region "$REGION" \
  --no-cli-pager 2>/dev/null || echo "Event source mapping 已存在，跳過"

echo ""
echo "=== 完成 ==="
echo "SQS_QUEUE_URL=$QUEUE_URL"
echo ""
echo "請將上面的 SQS_QUEUE_URL 加入 .env"
echo "另外需設定 Lambda 環境變數："
echo "  GOOGLE_DRIVE_FOLDER_ID=<your-folder-id>"
echo "  GOOGLE_SA_CREDENTIALS=<base64-encoded-service-account-json>"
