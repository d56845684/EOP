#!/bin/bash
# 建立 AWS 資源：Email 通知 SQS Queue + DLQ + IAM Role + Lambda
# 使用方式:
#   bash scripts/setup-notification-sqs-lambda.sh --profile EOP-admin-dennis
#   bash scripts/setup-notification-sqs-lambda.sh
set -euo pipefail

# ── AWS Profile 選擇 ──
source "$(dirname "$0")/aws-profile-select.sh" "$@"

REGION="${AWS_REGION:-ap-northeast-1}"
FUNCTION_NAME="eop-notification-email-sender"
QUEUE_NAME="eop-notification-email"
DLQ_NAME="eop-notification-email-dlq"
ROLE_NAME="eop-notification-lambda-role"

echo "=== Email 通知 SQS + Lambda 建立 ==="
echo "Region: $REGION"
echo ""

# ────────────────────────────────────────
# 1. 建立 DLQ
# ────────────────────────────────────────
echo "--- [1/5] 建立 DLQ: $DLQ_NAME ---"
DLQ_URL=$(aws $AWS_OPTS sqs create-queue \
  --queue-name "$DLQ_NAME" \
  --region "$REGION" \
  --query 'QueueUrl' --output text 2>/dev/null || true)

if [ -z "$DLQ_URL" ]; then
  DLQ_URL=$(aws $AWS_OPTS sqs get-queue-url --queue-name "$DLQ_NAME" --region "$REGION" --query 'QueueUrl' --output text)
fi
echo "DLQ URL: $DLQ_URL"

DLQ_ARN=$(aws $AWS_OPTS sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names QueueArn \
  --region "$REGION" \
  --query 'Attributes.QueueArn' --output text)

# ────────────────────────────────────────
# 2. 建立主 Queue（含 redrive policy）
# ────────────────────────────────────────
echo "--- [2/5] 建立主 Queue: $QUEUE_NAME ---"
QUEUE_URL=$(aws $AWS_OPTS sqs create-queue \
  --queue-name "$QUEUE_NAME" \
  --region "$REGION" \
  --attributes "{
    \"VisibilityTimeout\": \"60\",
    \"MessageRetentionPeriod\": \"86400\",
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$DLQ_ARN\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\"
  }" \
  --query 'QueueUrl' --output text 2>/dev/null || true)

if [ -z "$QUEUE_URL" ]; then
  QUEUE_URL=$(aws $AWS_OPTS sqs get-queue-url --queue-name "$QUEUE_NAME" --region "$REGION" --query 'QueueUrl' --output text)
fi
echo "Queue URL: $QUEUE_URL"

QUEUE_ARN=$(aws $AWS_OPTS sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names QueueArn \
  --region "$REGION" \
  --query 'Attributes.QueueArn' --output text)

# ────────────────────────────────────────
# 3. 建立 IAM Role
# ────────────────────────────────────────
echo "--- [3/5] 建立 IAM Role: $ROLE_NAME ---"
TRUST_POLICY='{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}'

ROLE_ARN=$(aws $AWS_OPTS iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document "$TRUST_POLICY" \
  --query 'Role.Arn' --output text 2>/dev/null || \
  aws $AWS_OPTS iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)

echo "Role ARN: $ROLE_ARN"

# 基本 Lambda 執行權限
aws $AWS_OPTS iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" 2>/dev/null || true

# SQS 讀取 + SES 寄送權限
INLINE_POLICY="{
  \"Version\": \"2012-10-17\",
  \"Statement\": [
    {
      \"Sid\": \"SQSReceive\",
      \"Effect\": \"Allow\",
      \"Action\": [
        \"sqs:ReceiveMessage\",
        \"sqs:DeleteMessage\",
        \"sqs:GetQueueAttributes\"
      ],
      \"Resource\": \"$QUEUE_ARN\"
    },
    {
      \"Sid\": \"SESSend\",
      \"Effect\": \"Allow\",
      \"Action\": [\"ses:SendEmail\", \"ses:SendRawEmail\"],
      \"Resource\": \"*\"
    }
  ]
}"

aws $AWS_OPTS iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "sqs-ses-access" \
  --policy-document "$INLINE_POLICY"

echo "等待 IAM Role 生效..."
sleep 10

# ────────────────────────────────────────
# 4. 建立 Lambda Function
# ────────────────────────────────────────
echo "--- [4/5] 建立 Lambda: $FUNCTION_NAME ---"
LAMBDA_DIR="$(cd "$(dirname "$0")/../lambda/notification_email_sender" && pwd)"

# 先打包
if [ ! -f "$LAMBDA_DIR/function.zip" ]; then
  echo "打包 Lambda..."
  cd "$LAMBDA_DIR"
  zip -j function.zip lambda_function.py
  cd -
fi

# 從 .env.lambda 讀取環境變數
ENV_FILE="$LAMBDA_DIR/.env.lambda"
SES_SENDER_EMAIL="noreply@eop-system.com"
if [ -f "$ENV_FILE" ]; then
  _val=$(grep "^SES_SENDER_EMAIL=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d'=' -f2-)
  [ -n "$_val" ] && SES_SENDER_EMAIL="$_val"
fi

aws $AWS_OPTS lambda create-function \
  --function-name "$FUNCTION_NAME" \
  --runtime "python3.12" \
  --role "$ROLE_ARN" \
  --handler "lambda_function.lambda_handler" \
  --zip-file "fileb://$LAMBDA_DIR/function.zip" \
  --timeout 30 \
  --memory-size 128 \
  --environment "{\"Variables\":{\"SES_SENDER_EMAIL\":\"$SES_SENDER_EMAIL\"}}" \
  --region "$REGION" \
  --no-cli-pager 2>/dev/null || echo "Lambda 已存在，跳過建立"

# ────────────────────────────────────────
# 5. SQS → Lambda event source mapping
# ────────────────────────────────────────
echo "--- [5/5] 設定 SQS → Lambda 觸發 ---"
aws $AWS_OPTS lambda create-event-source-mapping \
  --function-name "$FUNCTION_NAME" \
  --event-source-arn "$QUEUE_ARN" \
  --batch-size 10 \
  --function-response-types ReportBatchItemFailures \
  --region "$REGION" \
  --no-cli-pager 2>/dev/null || echo "Event source mapping 已存在，跳過"

echo ""
echo "=== 完成 ==="
echo ""
echo "NOTIFICATION_SQS_QUEUE_URL=$QUEUE_URL"
echo ""
echo "請將上面的 NOTIFICATION_SQS_QUEUE_URL 加入 .env"
echo "並設定 NOTIFICATION_ENABLED=true 啟用通知"
echo ""
echo "⚠️  SES 注意事項："
echo "  - 新帳號預設在 Sandbox，只能寄給已驗證的 Email"
echo "  - 驗證寄件者: aws ses verify-email-identity --email-address $SES_SENDER_EMAIL"
echo "  - 申請 Production: AWS Console → SES → Account dashboard → Request production access"
