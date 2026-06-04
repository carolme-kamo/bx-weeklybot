"""
알림 테스트 스크립트
사용법:
  python3 test.py new       # 새 페이지 생성 알림 테스트
  python3 test.py reminder  # 금요일 리마인더 테스트
  python3 test.py           # 둘 다
"""

import sys
from dotenv import load_dotenv
from bot import load_state, send_new_page_dm, send_friday_reminder

load_dotenv()

TEST_TITLE = "[테스트] 26. 6월 주간보고"
state = load_state()
TEST_PAGE_URL = state.get("current_week_page_url", "https://wiki.daumkakao.com")

mode = sys.argv[1] if len(sys.argv) > 1 else "both"

if mode in ("new", "both"):
    print("▶ 새 페이지 알림 전송 중...")
    send_new_page_dm(TEST_TITLE, TEST_PAGE_URL)
    print("  완료")

if mode in ("reminder", "both"):
    print("▶ 금요일 리마인더 전송 중...")
    send_friday_reminder(TEST_TITLE, TEST_PAGE_URL)
    print("  완료")

print("✅ 테스트 완료 — Slack을 확인하세요")
