# BX디자인팀 주간보고 알림 슬랙봇

Confluence에 새 주간보고 페이지가 생성되면 Slack DM으로 알려주는 개인용 봇입니다.
**각자 본인의 Mac에서 실행하며, 본인에게만 알림이 전송됩니다.**

---

## 기능

- 새 주간보고 페이지 생성 시 → 즉시 Slack DM 알림 + 페이지 링크
- 매주 금요일 오전 11시 → 미작성자에게 리마인더 알림
- Mac 로그인 시 자동 실행 (LaunchAgent)

---

## 사전 준비

> `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`은 carol.me에게 Slack DM으로 받으세요.

### 1. 내 Slack 유저 ID 확인

```
Slack → 내 프로필 클릭 → ··· (더보기) → 멤버 ID 복사
```
`U`로 시작하는 문자열입니다. (예: `U01LEN0GC6A`)

### 2. 내 Confluence PAT 발급

```
wiki.daumkakao.com 접속
→ 우측 상단 프로필 클릭
→ 개인 설정
→ 보안
→ Personal Access Tokens
→ 토큰 만들기 클릭
→ 이름 입력 (예: weekly-bot) → 만들기
→ 생성된 토큰 복사 (다시 볼 수 없으니 바로 저장)
```

---

## 설치

### 1. 코드 받기

```bash
git clone https://github.com/carolme-kamo/bxd-weekly-bot.git
cd bxd-weekly-bot
```

### 2. .env 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 아래 값 입력:

```
MY_SLACK_USER_ID=U012ABCDEFG          ← 내 Slack 유저 ID
MY_CONFLUENCE_USERNAME=hong.gildong   ← 카카오 이메일 @ 앞부분
CONFLUENCE_API_TOKEN=발급받은PAT토큰   ← 내 Confluence PAT
SLACK_BOT_TOKEN=carol에게받은토큰      ← 팀 공통 (carol.me에게 요청)
SLACK_APP_TOKEN=carol에게받은토큰      ← 팀 공통 (carol.me에게 요청)
```

### 3. 동작 확인

```bash
python3 -u bot.py
```

아래처럼 출력되면 정상:
```
주간보고 알림 봇 시작
Slack 유저: U012ABCDEFG | Confluence: hong.gildong
⚡️ 봇 실행 중 (종료: Ctrl+C)
[09:00:00] 새 페이지 없음
```

알림 테스트:
```bash
python3 test.py new       # 새 페이지 알림 테스트
python3 test.py reminder  # 금요일 리마인더 테스트
```

### 4. Mac 로그인 시 자동 실행 설정

터미널에서 아래 명령어 한 줄 실행:

```bash
bash install.sh
```

완료되면 Mac을 재시작하거나 로그아웃 후 재로그인해도 봇이 자동으로 시작됩니다.

자동 실행 해제:
```bash
launchctl unload ~/Library/LaunchAgents/com.kakao.weekly-report-bot.plist
```

재등록:
```bash
launchctl load ~/Library/LaunchAgents/com.kakao.weekly-report-bot.plist
```

로그 확인:
```bash
tail -f bot.log
```

---

## 폴더 구조

```
bxd-weekly-bot/
├── bot.py                              # 봇 메인 코드
├── test.py                             # 알림 테스트 스크립트
├── install.sh                          # 자동 실행 등록 스크립트
├── com.kakao.weekly-report-bot.plist   # macOS LaunchAgent 설정
├── requirements.txt                    # 패키지 목록
├── .env.example                        # 환경변수 템플릿
├── .env                                # 실제 설정값 (git에 올라가지 않음)
├── state.json                          # 페이지 추적 상태 (자동 생성)
└── bot.log                             # 실행 로그 (자동 생성)
```

---

## 문의

carol.me@kakaomobility.com
