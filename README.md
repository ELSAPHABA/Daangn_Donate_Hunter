# Daangn Donate Hunter

당근마켓의 나눔 상품을 주기적으로 확인하고, 조건에 맞는 새 상품을 Telegram으로 알려주는 봇입니다.

이 문서는 프로젝트 구조, 실행 방법, 주요 기능, 설정값, 저장 데이터 구조를 설명합니다. 토큰, 채팅 ID, 프록시 계정 같은 민감 정보는 포함하지 않습니다.

## 주요 기능

- Telegram 봇 키보드와 slash command로 탐지 동네, 탐지 키워드, 제외 키워드, 알림 상태를 관리합니다.
- 당근 동네 번호를 자동 수집해 `areas.json`에 저장합니다.
- 등록된 동네와 키워드 조합별로 당근 나눔 상품을 주기적으로 확인합니다.
- 새 상품이 발견되면 Telegram으로 상품 제목과 짧은 상품 링크를 보냅니다.
- 같은 유저에게 같은 상품 URL을 중복 발송하지 않도록 막습니다.
- 포괄 동네와 세부 동네처럼 서로 다른 검색 링크에서 같은 상품이 잡혀도 유저별 상품 URL 기준으로 한 번만 알립니다.
- 제외 키워드가 상품 제목에 토큰 기반 AND 방식으로 매칭되면 해당 유저에게 알림을 보내지 않습니다.
- 사용자 활동은 `user_activity.log`, 오류는 `error.log`에 기록합니다.
- 여러 Proxy와 User-Agent를 사용해 요청을 분산할 수 있습니다.

## 실행 환경

- Python 3.11 이상
- Telegram Bot Token
- 네트워크 접근 가능한 실행 환경

Python 의존성은 `pyproject.toml`에 정의되어 있습니다.

```text
beautifulsoup4
python-dotenv
python-telegram-bot[job-queue]
requests[socks]
```

## 설치와 실행

개발 환경에서 실행:

```powershell
python -m pip install -e .
$env:TELEGRAM_BOT_TOKEN="<telegram-bot-token>"
python main.py bot
```

설치 후 콘솔 스크립트로 실행:

```powershell
daangn-donate-hunter bot
```

`.env` 파일을 사용할 수도 있습니다. 실제 값은 개인 환경에만 보관하고 저장소에 커밋하지 마세요.

```env
TELEGRAM_BOT_TOKEN=<telegram-bot-token>
ADMIN_CHAT_IDS=<telegram-chat-id>
```

## Docker 실행

이미지 빌드:

```powershell
docker build -t daangn-donate-hunter .
```

컨테이너 실행 예시:

```powershell
docker run -d --name daangn-donate-hunter --env-file .env -v daangn-donate-hunter-data:/data daangn-donate-hunter
```

Docker 기본값:

- 앱 경로: `/app`
- 데이터 경로: `/data`
- 사용자 활동 로그: `/data/user_activity.log`
- 오류 로그: `/data/error.log`
- 기본 명령: `daangn-donate-hunter bot`

## Telegram 명령어

봇 시작 시 Telegram BotCommand가 등록되어, Telegram에서 `/`를 입력하면 명령어 자동완성이 표시됩니다.

| 명령어 | 기능 |
| --- | --- |
| `/start` | 봇 시작 |
| `/settings` | 설정 메인 키보드 표시 |
| `/areasetting` | 탐지 동네 설정 |
| `/areaview` | 탐지 동네 조회 |
| `/areaadd` | 탐지 동네 추가 |
| `/areadelete` | 탐지 동네 삭제 |
| `/kwdsetting` | 탐지 키워드 설정 |
| `/kwdview` | 탐지 키워드 조회 |
| `/kwdadd` | 탐지 키워드 추가 |
| `/kwddelete` | 탐지 키워드 삭제 |
| `/skipkwdsetting` | 제외 키워드 설정 |
| `/skipkwdview` | 제외 키워드 조회 |
| `/skipkwdadd` | 제외 키워드 추가 |
| `/skipkwddelete` | 제외 키워드 삭제 |
| `/arlam` | 알림 시작/중지 토글 |
| `/help` | 도움말 |
| `/manage` | 관리자 메뉴 |

`/manage`는 `ADMIN_CHAT_IDS`에 등록된 관리자만 사용할 수 있습니다.

## Telegram 키보드 구조

메인 키보드:

```text
탐지 동네 설정 | 탐지 키워드 설정
제외 키워드 설정 | 알림 설정
```

탐지 동네 설정:

```text
탐지 동네 조회 | 탐지 동네 추가
탐지 동네 삭제 | 돌아가기
```

탐지 키워드 설정:

```text
탐지 키워드 조회 | 탐지 키워드 추가
탐지 키워드 삭제 | 돌아가기
```

제외 키워드 설정:

```text
제외 키워드 조회 | 제외 키워드 추가
제외 키워드 삭제 | 돌아가기
```

## 동네DB 자동 수집

봇 실행 시 동네DB 수집 작업이 백그라운드에서 시작됩니다. 이후 매월 1일 00:00에 `Asia/Seoul` 기준으로 다시 실행됩니다.

동작 흐름:

```text
scrape_state.json의 last_area_number 확인
-> 다음 번호부터 당근 동네 페이지 요청
-> 동네 이름을 찾으면 areas.json에 저장
-> 마지막 성공/확인 번호를 scrape_state.json에 저장
-> 번호 불일치가 기준 횟수만큼 연속 발생하면 종료
```

기본값:

- 최초 시작 번호: `AREA_COLLECTION_START_NUMBER`, 기본값 `11`
- 수집 간격: `AREA_COLLECTION_DELAY_SECONDS`, 기본값 `10`초
- 실패 재시도 대기: `AREA_COLLECTION_RETRY_DELAY_SECONDS`, 기본값 `60`초
- 연속 불일치 종료 기준: `AREA_COLLECTION_MISMATCH_STOP_THRESHOLD`, 기본값 `30`

## 나눔 모니터링

유저가 등록한 구독은 `동네 x 탐지 키워드` 조합으로 저장됩니다. 모니터링 작업은 기본 60초마다 실행됩니다.

동작 흐름:

```text
활성 유저 목록 조회
-> detect_link별 구독 묶기
-> 당근 최신 나눔 상품 조회
-> 링크별 최근 상품 URL 확인
-> 유저별 제외 키워드 확인
-> 유저별 상품 URL 중복 알림 확인
-> Telegram 알림 전송
-> user_activity.log에 발송 기록 저장
```

기본값:

- 모니터링 주기: `SCRAPE_INTERVAL_SECONDS`, 기본값 `60`초
- 동시 처리 수: `MONITOR_CONCURRENCY`, 기본값 `3`
- 링크별 재시도 횟수: `MONITOR_MAX_RETRIES`, 기본값 `1`
- 재시도 대기: `MONITOR_RETRY_DELAY_SECONDS`, 기본값 `60`초
- 스크래핑 타임아웃: `SCRAPE_TIMEOUT_SECONDS`, 기본값 `10`초
- 최근 URL 보관 수: `MONITOR_RECENT_ITEMS_LIMIT`, 기본값 `100`
- misfire 허용 시간: `MONITOR_MISFIRE_GRACE_SECONDS`, 기본값 `300`초

이전 회차가 아직 실행 중이면 다음 회차는 건너뜁니다. 컨테이너 pause/unpause 등으로 작업이 밀리면 JobQueue의 `coalesce=True` 설정으로 한 번만 실행합니다.

## 알림 형식

Telegram 나눔 알림은 아래 형식으로 전송됩니다.

```text
[동네] [키워드] 새 나눔 알림:
상품 제목
https://www.daangn.com/kr/buy-sell/<상품ID>/
```

상품 제목은 스크래핑 결과의 `item.title`을 사용합니다.

당근 상품 URL이 아래처럼 제목 slug를 포함해도:

```text
https://www.daangn.com/kr/buy-sell/<제목-slug>-<상품ID>/
```

유저에게는 아래처럼 짧은 URL을 보냅니다.

```text
https://www.daangn.com/kr/buy-sell/<상품ID>/
```

## 중복 알림 방지

중복 방지는 두 단계입니다.

1. `latest_items[detect_link]`
   - 검색 링크별 최근 상품 URL을 기억합니다.
   - 같은 링크에서 이미 본 상품이면 새 알림 후보로 보지 않습니다.

2. `notified_items[chat_id]`
   - 유저별로 이미 알림 보낸 상품 URL을 기억합니다.
   - 서로 다른 동네 링크에서 같은 상품이 잡혀도 같은 유저에게는 한 번만 보냅니다.

각 목록은 `MONITOR_RECENT_ITEMS_LIMIT` 개수까지만 보관합니다.

## 제외 키워드

제외 키워드는 상품 제목에 대해 토큰 기반 AND 매칭으로 동작합니다.

예:

```text
제외 키워드: 아이폰 12
상품 제목: 깨끗한 아이폰 미니 12 나눔
결과: "아이폰"과 "12"가 모두 제목에 있으므로 알림 제외
```

예:

```text
제외 키워드: 아이폰 13
상품 제목: 깨끗한 아이폰 미니 12 나눔
결과: "13"이 없으므로 알림 전송 대상 유지
```

제외 키워드가 매칭되면 Telegram 알림은 보내지 않고 `user_activity.log`에 `[나눔 알림 제외]` 기록을 남깁니다.

## Proxy와 User-Agent

Proxy는 환경변수로 설정합니다. 값 자체는 민감 정보이므로 저장소에 커밋하지 마세요.

| 환경변수 | 설명 |
| --- | --- |
| `PROXY_HOST_1`, `PROXY_HOST_2`, ... | Proxy 호스트 목록 |
| `PROXY_USER` | Proxy 사용자명 |
| `PROXY_PASS` | Proxy 비밀번호 |
| `PROXY_PORT` | Proxy 포트 |
| `PROXY_ROTATE_SECONDS` | Proxy 로테이션 주기, 기본값 `900`초 |

Proxy 정보가 모두 설정되어 있지 않으면 Proxy 없이 요청합니다.

User-Agent는 `resources/user-agents.txt`에서 읽습니다. 기본적으로 20회 사용 후 다른 User-Agent로 교체됩니다.

## 환경변수

| 환경변수 | 기본값 | 설명 |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | 없음 | Telegram Bot Token, 필수 |
| `ADMIN_CHAT_IDS` | 빈 값 | 관리자 Telegram chat ID 목록, 쉼표 구분 |
| `DATA_DIR` | `data` | JSON 데이터 저장 경로 |
| `USER_ACTIVITY_LOG` | `user_activity.log` | 사용자 활동 로그 경로 |
| `ERROR_LOG` | `error.log` | 오류 로그 경로 |
| `SCRAPE_INTERVAL_SECONDS` | `60` | 나눔 모니터링 주기 |
| `MONITOR_MISFIRE_GRACE_SECONDS` | `300` | 지연 실행 허용 시간 |
| `MONITOR_RETRY_DELAY_SECONDS` | `60` | 모니터링 재시도 대기 |
| `MONITOR_CONCURRENCY` | `3` | 동시에 처리할 검색 링크 수 |
| `MONITOR_MAX_RETRIES` | `1` | 링크별 최대 시도 횟수 |
| `MONITOR_RECENT_ITEMS_LIMIT` | `100` | 중복 방지용 최근 URL 보관 수 |
| `SCRAPE_TIMEOUT_SECONDS` | `10` | 스크래핑 요청 타임아웃 |
| `AREA_COLLECTION_START_NUMBER` | `11` | 동네DB 최초 시작 번호 |
| `AREA_COLLECTION_DELAY_SECONDS` | `10` | 동네DB 번호별 수집 간격 |
| `AREA_COLLECTION_RETRY_DELAY_SECONDS` | `60` | 동네DB 실패 재시도 대기 |
| `AREA_COLLECTION_MISMATCH_STOP_THRESHOLD` | `30` | 연속 번호 불일치 종료 기준 |
| `PROXY_ROTATE_SECONDS` | `900` | Proxy 로테이션 주기 |
| `USER_AGENT_FILE` | `resources/user-agents.txt` | User-Agent 목록 파일 |

## 데이터 파일

기본 로컬 실행에서는 `DATA_DIR` 아래에 JSON 데이터가 저장됩니다. Docker 실행에서는 `/data` 볼륨에 저장됩니다.

### `users.json`

유저 설정을 저장합니다.

```json
{
  "users": [
    {
      "chat_id": "<telegram-chat-id>",
      "notification": true,
      "regions": [],
      "keywords": [],
      "skip_keywords": [],
      "subscriptions": []
    }
  ]
}
```

### `areas.json`

동네 이름과 당근 동네 번호를 저장합니다.

```json
{
  "서울 금천구 독산동": "295"
}
```

### `scrape_state.json`

스크래핑 상태와 중복 알림 방지 상태를 저장합니다.

```json
{
  "latest_items": {},
  "notified_items": {},
  "last_area_number": 0
}
```

## 로그

`user_activity.log`에는 주요 사용자 활동과 정상 흐름이 기록됩니다.

예:

```text
[탐지 동네 추가]
[탐지 키워드 추가]
[제외 키워드 추가]
[나눔 알림 발송]
[나눔 알림 제외]
[동네DB 수집]
```

`error.log`에는 스크래핑 실패, Telegram 전송 실패, JSON 손상 등 오류가 기록됩니다.

## 프로젝트 구조

```text
.github/
  workflows/          GitHub Actions 워크플로우
bot/
  handlers.py         Telegram 명령어, 키보드, 대화 상태 처리
core/
  config.py           환경변수 로딩과 Settings 정의
  models.py           Region, Subscription, ScrapedItem 모델
  query.py            검색 URL 생성, 입력 정규화, 키워드 매칭, URL 축약
monitoring/
  area_collection.py  동네DB 자동 수집
  donation.py         나눔 상품 주기 모니터링과 알림 필터링
notifications/
  telegram.py         Telegram 메시지 전송
resources/
  user-agents.txt     User-Agent 목록
scraping/
  daangn.py           당근 페이지/API 스크래핑
  proxy.py            Proxy 로테이션
  user_agents.py      User-Agent 로테이션
storage/
  json_store.py       JSON 파일 기반 사용자/동네/상태 저장소
utils/
  encoding.py         프로세스 인코딩 설정
  logging_config.py   로그 설정
main.py               앱 구성, JobQueue 등록, CLI 진입점
Dockerfile            Docker 이미지 정의
docker-entrypoint.sh  컨테이너 시작 스크립트
pyproject.toml        패키지 메타데이터와 의존성
README.md             프로젝트 문서
```

## 보안 주의사항

- `TELEGRAM_BOT_TOKEN`은 README, 코드, 로그, 커밋 메시지에 남기지 마세요.
- 실제 `ADMIN_CHAT_IDS` 값은 공개 저장소에 올리지 마세요.
- Proxy 사용자명과 비밀번호는 `.env` 또는 배포 환경변수로만 관리하세요.
- `data/`, `user_activity.log`, `error.log`, `.env`는 `.gitignore`에 포함되어 있습니다.

## 간단 점검

문법 확인:

```powershell
python -m compileall -q main.py bot core monitoring notifications resources scraping storage utils
```

설정과 주요 import 확인:

```powershell
python -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); import main; from core import load_settings; from scraping import DaangnScraper; print('imports ok')"
```

동네DB 샘플 수집 CLI는 현재 `main.py`에 등록되어 있지 않습니다. 동네DB 수집은 봇 실행 시 백그라운드 작업으로 실행됩니다.
