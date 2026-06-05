#!/bin/bash
# 주간보고 봇 자동 실행 등록 스크립트

set -e
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.kakao.weekly-report-bot.plist"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

echo "📦 패키지 설치 중..."
pip3 install -r "$BOT_DIR/requirements.txt" -q

echo "⚙️  .env 확인 중..."
if [ ! -f "$BOT_DIR/.env" ]; then
    cp "$BOT_DIR/.env.example" "$BOT_DIR/.env"
    echo "❗ .env 파일이 생성되었습니다. 토큰 값을 입력하고 다시 실행하세요:"
    echo "   $BOT_DIR/.env"
    exit 1
fi

echo "🔧 LaunchAgent 등록 중..."
mkdir -p "$LAUNCH_AGENTS"
cp "$BOT_DIR/$PLIST_NAME" "$LAUNCH_AGENTS/$PLIST_NAME"

# 이미 로드된 경우 언로드 후 재로드
launchctl unload "$LAUNCH_AGENTS/$PLIST_NAME" 2>/dev/null || true
launchctl load "$LAUNCH_AGENTS/$PLIST_NAME"

echo "✅ 완료! 봇이 백그라운드에서 실행 중입니다."
echo "   로그: $BOT_DIR/bot.log"
echo ""
echo "🛑 봇 중지하려면:"
echo "   launchctl unload ~/Library/LaunchAgents/$PLIST_NAME"
