"""
주간보고 알림 슬랙봇 (개인용)
- 각자의 Mac에서 실행, 본인에게만 DM 전송
- 새 주간보고 페이지 생성 시 즉시 알림
- 금요일 오전 11시, 미작성자에게 리마인더
"""

import json
import os
import sys
import threading
import time
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

KST = ZoneInfo("Asia/Seoul")

# ── 내 정보 ─────────────────────────────────────────────────
MY_SLACK_USER_ID       = os.environ["MY_SLACK_USER_ID"]
MY_CONFLUENCE_USERNAME = os.environ["MY_CONFLUENCE_USERNAME"]

# ── Confluence 설정 ──────────────────────────────────────────
CONFLUENCE_BASE_URL  = "https://wiki.daumkakao.com"
PARENT_PAGE_ID       = "2048313600"
CONFLUENCE_API_TOKEN = os.environ["CONFLUENCE_API_TOKEN"]

# ── Slack 설정 ───────────────────────────────────────────────
SLACK_BOT_TOKEN  = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN  = os.environ["SLACK_APP_TOKEN"]   # xapp-... (Socket Mode용)
POLL_INTERVAL    = int(os.environ.get("POLL_INTERVAL_SECONDS", "300"))

BASE_DIR   = Path(__file__).parent
STATE_FILE = BASE_DIR / "state.json"

app    = App(token=SLACK_BOT_TOKEN)
client = app.client


# ── 상태 관리 ────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"seen_page_ids": [], "current_week_page_id": None, "current_week_page_url": None}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def current_week_key() -> str:
    iso = date.today().isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def is_skip_week() -> bool:
    return load_state().get("skip_week") == current_week_key()


# ── Confluence API ────────────────────────────────────────────

def cf_headers() -> dict:
    return {"Authorization": f"Bearer {CONFLUENCE_API_TOKEN}"}


def get_child_pages() -> list[dict]:
    r = requests.get(
        f"{CONFLUENCE_BASE_URL}/rest/api/content/{PARENT_PAGE_ID}/child/page",
        headers=cf_headers(),
        params={"limit": 100},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("results", [])


def get_page_contributors(page_id: str) -> set[str]:
    r = requests.get(
        f"{CONFLUENCE_BASE_URL}/rest/api/content/{page_id}",
        headers=cf_headers(),
        params={"expand": "history.contributors.publishers.users"},
        timeout=15,
    )
    if not r.ok:
        return set()
    users = (
        r.json()
        .get("history", {})
        .get("contributors", {})
        .get("publishers", {})
        .get("users", [])
    )
    return {u.get("username", "") for u in users if u.get("username")}


def extract_page_url(page: dict) -> str:
    webui = page.get("_links", {}).get("webui", f"/spaces/BXD/pages/{page['id']}")
    return CONFLUENCE_BASE_URL + webui


# ── Slack 메시지 ──────────────────────────────────────────────

def send_new_page_dm(page_title: str, page_url: str):
    client.chat_postMessage(
        channel=MY_SLACK_USER_ID,
        text="이번 주 BX 디자인팀 주간 보고를 작성해주세요! ⭐️",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"이번 주 BX 디자인팀 주간 보고를 작성해주세요! ⭐️\n📄 *{page_title}*",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "작성하러 가기"},
                        "url": page_url,
                        "style": "primary",
                        "action_id": "go_write",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "작성 완료"},
                        "value": "skip_week",
                        "action_id": "skip_week",
                    },
                ],
            },
        ],
    )


def send_friday_reminder(page_title: str, page_url: str):
    client.chat_postMessage(
        channel=MY_SLACK_USER_ID,
        text="오늘까지 주간보고 작성을 완료해주세요! 🚨",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"오늘까지 주간보고 작성을 완료해주세요! 🚨\n📄 *{page_title}*",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "작성하러 가기"},
                        "url": page_url,
                        "style": "primary",
                        "action_id": "go_write",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "이번 주 알림 끄기"},
                        "value": "skip_week",
                        "action_id": "skip_week",
                    },
                ],
            },
        ],
    )


# ── Slack 액션 핸들러 ─────────────────────────────────────────

@app.action("skip_week")
def handle_skip_week(ack, body, client):
    ack()
    state = load_state()
    state["skip_week"] = current_week_key()
    save_state(state)
    print(f"[{now()}] 이번 주 알림 끄기 설정 완료 ({current_week_key()})")

    # 메시지에서 버튼 제거하고 완료 상태 표시
    channel = body["channel"]["id"]
    ts = body["message"]["ts"]
    section_block = body["message"].get("blocks", [{}])[0]
    client.chat_update(
        channel=channel,
        ts=ts,
        text=body["message"].get("text", ""),
        blocks=[
            section_block,
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "✅ 이번 주 알림이 꺼졌습니다."}],
            },
        ],
    )


# ── Confluence 폴링 ───────────────────────────────────────────

def polling_loop():
    if not STATE_FILE.exists():
        print(f"[{now()}] 초기 상태 구성 중...")
        pages = get_child_pages()
        if pages:
            latest = pages[-1]
            page_url = extract_page_url(latest)
            # 최신 페이지는 seen에서 제외해서 반드시 알림 전송
            save_state({
                "seen_page_ids": [p["id"] for p in pages[:-1]],
                "current_week_page_id": latest["id"],
                "current_week_page_url": page_url,
            })
            print(f"[{now()}] 최신 페이지 알림 전송: {latest['title']}")
            send_new_page_dm(latest["title"], page_url)
        else:
            save_state({"seen_page_ids": [], "current_week_page_id": None, "current_week_page_url": None})
            print(f"[{now()}] 등록된 페이지 없음")

    while True:
        try:
            state = load_state()
            seen_ids = set(state["seen_page_ids"])
            pages = get_child_pages()
            # skip_week 여부와 무관하게 새 페이지면 항상 알림
            new_pages = [p for p in pages if p["id"] not in seen_ids]

            if new_pages:
                for page in new_pages:
                    page_url = extract_page_url(page)
                    print(f"[{now()}] 새 페이지 감지: {page['title']}")
                    send_new_page_dm(page["title"], page_url)
                    seen_ids.add(page["id"])

                latest = new_pages[-1]
                state["current_week_page_id"] = latest["id"]
                state["current_week_page_url"] = extract_page_url(latest)
            else:
                print(f"[{now()}] 새 페이지 없음")

            state["seen_page_ids"] = list(seen_ids)
            save_state(state)

        except Exception as e:
            print(f"[{now()}] 폴링 오류: {e}", file=sys.stderr)

        time.sleep(POLL_INTERVAL)


# ── 금요일 리마인더 ───────────────────────────────────────────

def friday_reminder_job():
    if is_skip_week():
        print(f"[{now()}] 리마인더 스킵: 이번 주 알림 끄기 설정됨")
        return

    state = load_state()
    page_id  = state.get("current_week_page_id")
    page_url = state.get("current_week_page_url")

    if not page_id:
        print(f"[{now()}] 리마인더: 현재 주 페이지 없음")
        return

    try:
        contributors = get_page_contributors(page_id)
        if MY_CONFLUENCE_USERNAME in contributors:
            print(f"[{now()}] 리마인더 스킵: 이미 작성 완료")
            return
    except Exception as e:
        print(f"[{now()}] 기여자 조회 실패: {e}", file=sys.stderr)

    try:
        r = requests.get(
            f"{CONFLUENCE_BASE_URL}/rest/api/content/{page_id}",
            headers=cf_headers(), timeout=10,
        )
        page_title = r.json().get("title", "주간보고")
    except Exception:
        page_title = "주간보고"

    send_friday_reminder(page_title, page_url)
    print(f"[{now()}] 금요일 리마인더 전송 완료")


# ── 유틸 ─────────────────────────────────────────────────────

def now() -> str:
    return datetime.now(KST).strftime("%H:%M:%S")


# ── 진입점 ───────────────────────────────────────────────────

if __name__ == "__main__":
    print("주간보고 알림 봇 시작")
    print(f"Slack 유저: {MY_SLACK_USER_ID} | Confluence: {MY_CONFLUENCE_USERNAME}")

    threading.Thread(target=polling_loop, daemon=True).start()

    scheduler = BackgroundScheduler(timezone=KST)
    scheduler.add_job(
        friday_reminder_job,
        CronTrigger(day_of_week="fri", hour=11, minute=0, timezone=KST),
    )
    scheduler.start()

    print("⚡️ 봇 실행 중 (종료: Ctrl+C)")

    SocketModeHandler(app, SLACK_APP_TOKEN).start()
