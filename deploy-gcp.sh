#!/bin/bash
# GCP Compute Engine 배포 스크립트
set -e

PROJECT_ID="bxd-ai-0f32"
INSTANCE_NAME="weekly-report-bot"
ZONE="asia-northeast3-a"   # 서울
MACHINE_TYPE="e2-micro"
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "▶ 프로젝트 설정: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# VM이 이미 있는지 확인
if gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" &>/dev/null; then
    echo "✅ 기존 VM 발견 — 파일만 재배포합니다."
else
    echo "▶ VM 생성 중..."
    gcloud compute instances create "$INSTANCE_NAME" \
        --zone="$ZONE" \
        --machine-type="$MACHINE_TYPE" \
        --image-family=debian-12 \
        --image-project=debian-cloud \
        --boot-disk-size=10GB \
        --tags=weekly-report-bot \
        --metadata=startup-script='#!/bin/bash
            curl -fsSL https://get.docker.com | sh
            usermod -aG docker $(logname)
            apt-get install -y docker-compose-plugin'
    echo "⏳ VM 초기화 대기 중 (60초)..."
    sleep 60
fi

echo "▶ 파일 전송 중..."
gcloud compute scp \
    "$BOT_DIR/bot.py" \
    "$BOT_DIR/requirements.txt" \
    "$BOT_DIR/Dockerfile" \
    "$BOT_DIR/docker-compose.yml" \
    "$BOT_DIR/.env" \
    "$INSTANCE_NAME":~/weekly-report-bot/ \
    --zone="$ZONE" \
    --recurse 2>/dev/null || \
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --command="mkdir -p ~/weekly-report-bot" && \
gcloud compute scp \
    "$BOT_DIR/bot.py" \
    "$BOT_DIR/requirements.txt" \
    "$BOT_DIR/Dockerfile" \
    "$BOT_DIR/docker-compose.yml" \
    "$BOT_DIR/.env" \
    "$INSTANCE_NAME":~/weekly-report-bot/ \
    --zone="$ZONE"

# state.json, users.json 있으면 함께 전송
for f in state.json users.json; do
    [ -f "$BOT_DIR/$f" ] && \
        gcloud compute scp "$BOT_DIR/$f" "$INSTANCE_NAME":~/weekly-report-bot/ --zone="$ZONE" || true
done

echo "▶ Docker 빌드 및 실행..."
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --command="
    cd ~/weekly-report-bot
    sudo docker compose down 2>/dev/null || true
    sudo docker compose up -d --build
    sudo docker compose ps
"

echo ""
echo "✅ 배포 완료!"
echo "   로그 보기: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='sudo docker compose -f ~/weekly-report-bot/docker-compose.yml logs -f'"
