#!/bin/bash
# AWS Profile 互動式選擇器（上下箭頭 + Enter）
# 被其他腳本 source 使用，設定 AWS_OPTS 變數
#
# 用法（在其他腳本中）:
#   source "$(dirname "$0")/aws-profile-select.sh" "$@"
#   # 之後 $AWS_OPTS 即可用於 aws $AWS_OPTS ...

# ── 解析 --profile 參數 ──
PROFILE=""
REMAINING_ARGS=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --profile) PROFILE="$2"; shift 2 ;;
    *) REMAINING_ARGS+=("$1"); shift ;;
  esac
done
if [ ${#REMAINING_ARGS[@]} -gt 0 ]; then
  set -- "${REMAINING_ARGS[@]}"
else
  set --
fi

# ── 互動式選擇 ──
if [ -z "$PROFILE" ]; then
  CRED_FILE="${HOME}/.aws/credentials"
  if [ ! -f "$CRED_FILE" ]; then
    echo "ERROR: 找不到 ~/.aws/credentials"; exit 1
  fi

  PROFILES=($(grep '^\[' "$CRED_FILE" | sed 's/\[//;s/\]//' | grep -v '^#'))

  if [ ${#PROFILES[@]} -eq 0 ]; then
    echo "ERROR: ~/.aws/credentials 內無 profile"; exit 1
  fi

  if [ ${#PROFILES[@]} -eq 1 ]; then
    PROFILE="${PROFILES[0]}"
    echo "自動選擇唯一的 profile: $PROFILE"
  else
    # 箭頭鍵選擇 UI
    selected=0
    total=${#PROFILES[@]}

    # 隱藏游標
    tput civis 2>/dev/null || true

    draw_menu() {
      # 清除之前的行
      for ((i=0; i<total+2; i++)); do
        tput cuu1 2>/dev/null && tput el 2>/dev/null
      done 2>/dev/null || true

      echo "  AWS Profile 選擇（↑↓ 移動, Enter 確認）:"
      echo ""
      for i in "${!PROFILES[@]}"; do
        if [ "$i" -eq "$selected" ]; then
          echo -e "  \033[1;36m❯ ${PROFILES[$i]}\033[0m"
        else
          echo "    ${PROFILES[$i]}"
        fi
      done
    }

    # 初次繪製（先印空行佔位再畫）
    echo "  AWS Profile 選擇（↑↓ 移動, Enter 確認）:"
    echo ""
    for i in "${!PROFILES[@]}"; do
      if [ "$i" -eq "$selected" ]; then
        echo -e "  \033[1;36m❯ ${PROFILES[$i]}\033[0m"
      else
        echo "    ${PROFILES[$i]}"
      fi
    done

    while true; do
      # 讀取按鍵
      IFS= read -rsn1 key
      case "$key" in
        $'\x1b')
          read -rsn2 rest
          case "$rest" in
            '[A') # 上
              ((selected > 0)) && ((selected--))
              ;;
            '[B') # 下
              ((selected < total-1)) && ((selected++))
              ;;
          esac
          draw_menu
          ;;
        '') # Enter
          break
          ;;
      esac
    done

    # 恢復游標
    tput cnorm 2>/dev/null || true

    PROFILE="${PROFILES[$selected]}"
  fi

  # ── 二次確認 ──
  echo ""
  echo -e "  選擇的 Profile: \033[1;33m$PROFILE\033[0m"
  echo ""
  read -p "  確認使用此 Profile? (Y/n): " confirm
  confirm="${confirm:-Y}"
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "已取消"; exit 0
  fi
fi

AWS_OPTS="--profile $PROFILE"

# ── 驗證 ──
echo ""
echo -n "  驗證 AWS 連線... "
if ! aws $AWS_OPTS sts get-caller-identity --no-cli-pager > /dev/null 2>&1; then
  echo "FAIL"
  echo "  ERROR: profile '$PROFILE' 無法連線 AWS（憑證可能過期或無效）"
  exit 1
fi
ARN=$(aws $AWS_OPTS sts get-caller-identity --query 'Arn' --output text 2>/dev/null)
echo "OK"
echo "  身份: $ARN"
echo ""
