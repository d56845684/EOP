#!/bin/bash
# ngrok tunnel for Zoom webhook development
# Usage:
#   ./scripts/ngrok.sh start   - Start ngrok tunnel (port 8001)
#   ./scripts/ngrok.sh stop    - Stop ngrok
#   ./scripts/ngrok.sh status  - Show current tunnel URL
#   ./scripts/ngrok.sh url     - Print tunnel URL only

PORT=80

case "$1" in
  start)
    if pgrep -x ngrok > /dev/null; then
      echo "ngrok is already running:"
      curl -s http://localhost:4040/api/tunnels | python3 -c "
import json,sys
for t in json.load(sys.stdin)['tunnels']:
    print(f\"  {t['public_url']}\")" 2>/dev/null
      exit 0
    fi
    ngrok http $PORT --log=stdout > /tmp/ngrok.log 2>&1 &
    sleep 2
    URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import json,sys
for t in json.load(sys.stdin)['tunnels']:
    if t['proto']=='https': print(t['public_url'])" 2>/dev/null)
    if [ -n "$URL" ]; then
      echo "ngrok started"
      echo "  Tunnel:  $URL"
      echo "  Webhook: $URL/api/v1/zoom/webhook"
      echo "  Monitor: http://localhost:4040"
    else
      echo "Failed to start ngrok. Check /tmp/ngrok.log"
      exit 1
    fi
    ;;
  stop)
    if pkill ngrok 2>/dev/null; then
      echo "ngrok stopped"
    else
      echo "ngrok is not running"
    fi
    ;;
  status|url)
    if ! pgrep -x ngrok > /dev/null; then
      echo "ngrok is not running"
      exit 1
    fi
    URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import json,sys
for t in json.load(sys.stdin)['tunnels']:
    if t['proto']=='https': print(t['public_url'])" 2>/dev/null)
    if [ "$1" = "url" ]; then
      echo "$URL"
    else
      echo "ngrok is running"
      echo "  Tunnel:  $URL"
      echo "  Webhook: $URL/api/v1/zoom/webhook"
      echo "  Monitor: http://localhost:4040"
    fi
    ;;
  *)
    echo "Usage: $0 {start|stop|status|url}"
    exit 1
    ;;
esac
