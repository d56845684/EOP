#!/usr/bin/env bash
# 跑 e2e 對遠端環境（staging / dev / ngrok tunnel 等）。
#
# Usage:
#   ./run-remote.sh <BASE_URL> [playwright args...]
#
# 必填 env：
#   E2E_ADMIN_EMAIL       super-admin email
#   E2E_ADMIN_PASSWORD    super-admin password
#
# 選填 env：
#   E2E_RUN_ID            固定 runId（debug 用，平常自動產生）
#   E2E_KEEP_ACCOUNTS     true 跳過 teardown，方便看資料
#   E2E_BOOTSTRAP_PASSWORD  e2e 動態建立 employee/teacher/student 帳號的密碼
#                           (預設 E2eTestPwd123!)
#   E2E_EMAIL_DOMAIN      e2e 帳號 email 網域 (預設 eop-test.com)
#
# 也可以把 env 寫進 ./.env.e2e（已被 .gitignore 排除），會自動載入。
#
# 範例：
#   E2E_ADMIN_PASSWORD=xxx ./run-remote.sh https://staging.example.com
#   E2E_ADMIN_PASSWORD=xxx ./run-remote.sh https://staging.example.com --project=admin --grep "頁面載入"
#   E2E_ADMIN_PASSWORD=xxx E2E_KEEP_ACCOUNTS=true ./run-remote.sh https://staging.example.com

set -euo pipefail

usage() {
  sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//' >&2
  exit 2
}

cd "$(dirname "$0")"

# 載入 .env.e2e（如果存在）
if [[ -f .env.e2e ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.e2e
  set +a
fi

BASE_URL="${1:-${E2E_BASE_URL:-}}"
[[ "${BASE_URL}" =~ ^https?:// ]] || usage
shift || true

: "${E2E_ADMIN_EMAIL:?E2E_ADMIN_EMAIL not set (required)}"
: "${E2E_ADMIN_PASSWORD:?E2E_ADMIN_PASSWORD not set (required)}"

# 不在非 localhost 下偷跑 docker exec 清 redis（global-setup 內部已保護，這裡只是提示）
if [[ "$BASE_URL" != *"localhost"* ]]; then
  echo "[run-remote] target = $BASE_URL (remote)"
  echo "[run-remote] note: rate-limit redis flush is skipped on remote"
fi

echo "[run-remote] admin = $E2E_ADMIN_EMAIL"
echo "[run-remote] runId = ${E2E_RUN_ID:-<auto>}  keep_accounts=${E2E_KEEP_ACCOUNTS:-false}"

# 不把密碼 echo 進 log
E2E_BASE_URL="$BASE_URL" \
E2E_ADMIN_EMAIL="$E2E_ADMIN_EMAIL" \
E2E_ADMIN_PASSWORD="$E2E_ADMIN_PASSWORD" \
E2E_RUN_ID="${E2E_RUN_ID:-}" \
E2E_KEEP_ACCOUNTS="${E2E_KEEP_ACCOUNTS:-}" \
E2E_BOOTSTRAP_PASSWORD="${E2E_BOOTSTRAP_PASSWORD:-}" \
E2E_EMAIL_DOMAIN="${E2E_EMAIL_DOMAIN:-}" \
npx playwright test "$@"
