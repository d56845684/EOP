#!/bin/bash
# =============================================================
# 01-create-rds.sh — 建立 AWS RDS PostgreSQL 實例
# Region: ap-northeast-1 | Instance: db.t3.micro (Free Tier)
# =============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REGION="ap-northeast-1"
DB_INSTANCE_ID="eop-postgres"
DB_NAME="postgres"
DB_USER="postgres"
DB_ENGINE="postgres"
DB_ENGINE_VERSION="15"
DB_INSTANCE_CLASS="db.t3.micro"
DB_STORAGE=20
DB_STORAGE_TYPE="gp3"
SG_NAME="eop-rds-sg"
SUBNET_GROUP_NAME="eop-db-subnet-group"
ENDPOINT_FILE="${SCRIPT_DIR}/.rds-endpoint"

echo "=== EOP RDS 建立腳本 ==="
echo "Region: ${REGION}"
echo "Instance: ${DB_INSTANCE_ID}"

# ---- 1. 取得 VPC ID（使用預設 VPC）----
echo ""
echo "[1/6] 取得預設 VPC..."
VPC_ID=$(aws ec2 describe-vpcs \
    --region "${REGION}" \
    --filters "Name=isDefault,Values=true" \
    --query "Vpcs[0].VpcId" \
    --output text)

if [ "${VPC_ID}" = "None" ] || [ -z "${VPC_ID}" ]; then
    echo "❌ 找不到預設 VPC，請確認 ${REGION} 有預設 VPC 或手動指定。"
    exit 1
fi
echo "   VPC ID: ${VPC_ID}"

# ---- 2. 取得 VPC CIDR ----
VPC_CIDR=$(aws ec2 describe-vpcs \
    --region "${REGION}" \
    --vpc-ids "${VPC_ID}" \
    --query "Vpcs[0].CidrBlock" \
    --output text)
echo "   VPC CIDR: ${VPC_CIDR}"

# ---- 3. 建立 Security Group ----
echo ""
echo "[2/6] 建立 Security Group: ${SG_NAME}..."
SG_ID=$(aws ec2 describe-security-groups \
    --region "${REGION}" \
    --filters "Name=group-name,Values=${SG_NAME}" "Name=vpc-id,Values=${VPC_ID}" \
    --query "SecurityGroups[0].GroupId" \
    --output text 2>/dev/null || true)

if [ "${SG_ID}" = "None" ] || [ -z "${SG_ID}" ]; then
    SG_ID=$(aws ec2 create-security-group \
        --region "${REGION}" \
        --group-name "${SG_NAME}" \
        --description "EOP RDS PostgreSQL - VPC internal only" \
        --vpc-id "${VPC_ID}" \
        --query "GroupId" \
        --output text)
    echo "   建立完成: ${SG_ID}"

    # 允許 VPC CIDR 的 5432 inbound
    aws ec2 authorize-security-group-ingress \
        --region "${REGION}" \
        --group-id "${SG_ID}" \
        --protocol tcp \
        --port 5432 \
        --cidr "${VPC_CIDR}" >/dev/null
    echo "   已新增 inbound rule: ${VPC_CIDR} → 5432/tcp"
else
    echo "   已存在: ${SG_ID}（跳過建立）"
fi

# ---- 4. 取得 Subnet IDs，建立 DB Subnet Group ----
echo ""
echo "[3/6] 建立 DB Subnet Group: ${SUBNET_GROUP_NAME}..."

SUBNET_IDS=$(aws ec2 describe-subnets \
    --region "${REGION}" \
    --filters "Name=vpc-id,Values=${VPC_ID}" \
    --query "Subnets[].SubnetId" \
    --output text)

# 轉為逗號分隔的 JSON array
SUBNET_LIST=$(echo "${SUBNET_IDS}" | tr '\t' '\n' | awk '{print "\"" $0 "\""}' | paste -sd, -)

EXISTING_SUBNET_GROUP=$(aws rds describe-db-subnet-groups \
    --region "${REGION}" \
    --query "DBSubnetGroups[?DBSubnetGroupName=='${SUBNET_GROUP_NAME}'].DBSubnetGroupName" \
    --output text 2>/dev/null || true)

if [ -z "${EXISTING_SUBNET_GROUP}" ] || [ "${EXISTING_SUBNET_GROUP}" = "None" ]; then
    aws rds create-db-subnet-group \
        --region "${REGION}" \
        --db-subnet-group-name "${SUBNET_GROUP_NAME}" \
        --db-subnet-group-description "EOP DB Subnet Group" \
        --subnet-ids ${SUBNET_IDS} >/dev/null
    echo "   建立完成"
else
    echo "   已存在（跳過建立）"
fi

# ---- 5. 設定密碼 ----
echo ""
echo "[4/6] 設定 RDS Master 密碼..."
if [ -n "${RDS_MASTER_PASSWORD:-}" ]; then
    DB_PASSWORD="${RDS_MASTER_PASSWORD}"
    echo "   使用環境變數 RDS_MASTER_PASSWORD"
else
    read -s -p "   請輸入 Master 密碼（至少 8 字元）: " DB_PASSWORD
    echo ""
    if [ ${#DB_PASSWORD} -lt 8 ]; then
        echo "❌ 密碼至少需要 8 個字元"
        exit 1
    fi
fi

# ---- 6. 建立 RDS 實例 ----
echo ""
echo "[5/6] 建立 RDS 實例: ${DB_INSTANCE_ID}..."

EXISTING_RDS=$(aws rds describe-db-instances \
    --region "${REGION}" \
    --query "DBInstances[?DBInstanceIdentifier=='${DB_INSTANCE_ID}'].DBInstanceStatus" \
    --output text 2>/dev/null || true)

if [ -n "${EXISTING_RDS}" ] && [ "${EXISTING_RDS}" != "None" ]; then
    echo "   RDS 實例已存在（狀態: ${EXISTING_RDS}）"
else
    aws rds create-db-instance \
        --region "${REGION}" \
        --db-instance-identifier "${DB_INSTANCE_ID}" \
        --db-instance-class "${DB_INSTANCE_CLASS}" \
        --engine "${DB_ENGINE}" \
        --engine-version "${DB_ENGINE_VERSION}" \
        --master-username "${DB_USER}" \
        --master-user-password "${DB_PASSWORD}" \
        --allocated-storage "${DB_STORAGE}" \
        --storage-type "${DB_STORAGE_TYPE}" \
        --db-name "${DB_NAME}" \
        --vpc-security-group-ids "${SG_ID}" \
        --db-subnet-group-name "${SUBNET_GROUP_NAME}" \
        --no-publicly-accessible \
        --backup-retention-period 7 \
        --no-multi-az \
        --no-auto-minor-version-upgrade >/dev/null

    echo "   建立請求已送出，等待 RDS 就緒..."
fi

# ---- 7. 等待 RDS available ----
echo ""
echo "[6/6] 等待 RDS 進入 available 狀態（可能需要 5-10 分鐘）..."
aws rds wait db-instance-available \
    --region "${REGION}" \
    --db-instance-identifier "${DB_INSTANCE_ID}"
echo "   RDS 已就緒！"

# ---- 8. 取得 Endpoint 並寫入檔案 ----
RDS_ENDPOINT=$(aws rds describe-db-instances \
    --region "${REGION}" \
    --db-instance-identifier "${DB_INSTANCE_ID}" \
    --query "DBInstances[0].Endpoint.Address" \
    --output text)

echo "${RDS_ENDPOINT}" > "${ENDPOINT_FILE}"

echo ""
echo "=== 完成 ==="
echo "RDS Endpoint: ${RDS_ENDPOINT}"
echo "Endpoint 已寫入: ${ENDPOINT_FILE}"
echo ""
echo "下一步: ./deploy/02-run-migrations.sh"
