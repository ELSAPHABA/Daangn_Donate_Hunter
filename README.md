# Daangn_Donate_Hunter
Hunter of detecting and alerting donate products at daangn.

## 실행

```powershell
python -m pip install -e .
$env:TELEGRAM_BOT_TOKEN="..."
$env:ADMIN_CHAT_IDS="123456789"
python main.py bot
```

설치 후 콘솔 스크립트로도 실행할 수 있습니다.

```powershell
daangn-donate-hunter bot
```

## 동네DB 자동 수집

`python main.py bot` 또는 컨테이너 기본 실행(`daangn-donate-hunter bot`)을 시작하면 동네DB 수집도 백그라운드에서 즉시 시작됩니다.
시작 수집은 Telegram 초기화가 끝난 뒤 별도 백그라운드 작업으로 실행되므로, 컨테이너 OS나 초기 네트워크 지연으로 JobQueue 즉시 실행 잡이 누락되는 문제를 피합니다.

- 시작 번호: `scrape_state.json`의 `last_area_number + 1`
- 최초 실행: `last_area_number` 기본값이 `0`이면 `AREA_COLLECTION_START_NUMBER`부터 시작
- 최초 시작 번호 기본값: `11`
- 컨테이너 재실행: `/data/scrape_state.json`에 저장된 마지막 수집/확인 번호 다음부터 재개
- 수집 간격: 10초에 1개 (`AREA_COLLECTION_DELAY_SECONDS`로 조정 가능)
- 실패 재시도: 스크래핑 실패 또는 동네 이름 미검출 시 실패한 번호에서 60초 후 재시도 (`AREA_COLLECTION_RETRY_DELAY_SECONDS`로 조정 가능)
- 정기 실행: 매월 1일 00:00, `Asia/Seoul` 기준
- 중단 조건: 요청한 번호와 응답 URL의 `in` 번호가 30회 연속 불일치하면 없는 번호 구간으로 보고 종료 (`AREA_COLLECTION_MISMATCH_STOP_THRESHOLD`로 조정 가능)

수집된 동네는 `areas.json`에 즉시 저장되고, 마지막 수집/확인 번호는 `scrape_state.json`에 저장됩니다.
Docker 배포에서는 `daangn-donate-hunter-data:/data` 볼륨을 사용하므로 컨테이너가 재생성되어도 `last_area_number`가 유지됩니다.
불일치가 발생해도 30회 연속에 도달하기 전 정상 동네 번호를 다시 만나면 연속 불일치 횟수는 0으로 초기화됩니다.

## 나눔 모니터링

유저가 등록한 구독은 기본 60초마다 확인합니다.

- 모니터링 주기: `SCRAPE_INTERVAL_SECONDS` 기본값 60초
- misfire 허용 시간: `MONITOR_MISFIRE_GRACE_SECONDS` 기본값 300초
- 중복 실행 방지: 이전 모니터링 회차가 아직 실행 중이면 다음 회차는 건너뜁니다.
- 지연 회차 처리: 컨테이너 pause/unpause 또는 호스트 지연으로 여러 회차가 밀리면 `coalesce=True`로 한 번만 실행합니다.

런타임 데이터는 `data/`, 사용자 활동 로그는 `user_activity.log`, 오류 로그는 `error.log`에 저장됩니다.

## 코드 구조

```text
bot/            텔레그램 명령어와 키보드 핸들러
core/           설정, 도메인 모델, 당근 검색 URL 생성
monitoring/     구독별 주기 탐지 및 알림 트리거
notifications/  텔레그램 메시지 전송
resources/      User-Agent 목록
scraping/       당근 페이지 스크래핑, 프록시, User-Agent 관리
storage/        JSON 기반 사용자/동네/탐지 상태 저장
utils/          로깅과 프로세스 인코딩 설정
```
