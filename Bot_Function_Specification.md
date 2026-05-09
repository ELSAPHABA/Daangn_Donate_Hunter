# Daangn_Donate_Hunter: Telegram-bot - 상세 기능 명세서

당근마켓 동네에서의 나눔 상품을 탐지하고, 실시간으로 텔레그램으로 알려주는 텔레그램 봇 구현 상세 가이드

## 1. 프로젝트 개요
- **목표**: 특정 주기로 당근마켓 웹 페이지를 스크래핑 해, 특정 동네에서 최신 나눔 상품이 올라왔을 경우 실시간으로 텔레그램으로 알려주는 텔레그램 봇 구현
- **기술 스택**: python-telegram-bot, beautifulsoup, requests, user-agents, json, logging
- **주요 기능**:
    - 나눔 상품 탐지: 특정 동네 및 키워드 조합으로 당근마켓 웹 페이지를 스크래핑 해 최신 나눔 상품 탐지
    - 텔레그램 알림: 탐지된 나눔 상품 정보를 텔레그램으로 실시간 전송
    - 유저 설정 관리: 탐지 동네, 키워드, 알림 설정을 텔레그램 봇 UI에서 관리
    - 오류 로그 기록: 스크래핑 실패 및 기타 오류 발생 시 로그 기록
    - 동네 주소 스크래핑: 당근마켓에서 사용되는 동네 주소를 스크래핑 해 DB에 저장

## 2. Telegram bot UI/UX 설계
- **/start**
    - 초기
        - "당근마켓에서 동네의 나눔 상품을 탐지합니다. 탐지 동네 및 키워드, 알림을 설정하시려면 /settings를, 도움말은 /help를 입력해 주세요."
        - CustomKeyboard 팝업

- **/settings**
    - Markup+Button
    - CustomKeyboard 팝업
    - Button(탐지 동네 설정)
        - Button(탐지 동네 조회)
            - "현재 탐지중인 동네입니다: - ([동네이름])", Button(돌아가기)
        - Button(탐지 동네 추가)
            - "추가하실 동네를 입력해 주세요. [XX도 XX시 (XX구) XX동] 형식으로 입력해 주세요." Button(돌아가기)
                - "[XX도 XX시 (XX구) XX동]이 추가되었습니다." Button(돌아가기)
                - "이미 탐지중인 동네입니다." Button(돌아가기)
                - "해당되는 동네가 없습니다. 다시 입력해주세요." Button(돌아가기)
        - Button(탐지 동네 삭제)
            - "삭제하실 동네를 선택하세요." Button([동네이름]), Button(돌아가기)
                - "[XX도 XX시 (XX구) XX동]이 삭제되었습니다." Button(돌아가기)
            - "탐지중인 동네가 없습니다." Button(돌아가기)
    - Button(탐지 키워드 설정)
        - Button(탐지 키워드 조회)
            - "현재 탐지중인 키워드입니다: - ([키워드])" Button(돌아가기)
        - Button(탐지 키워드 추가)
            - "추가하실 키워드를 입력해 주세요. 미입력시 전체를 탐지합니다." Button(돌아가기)
                - "[키워드]가 추가되었습니다." Button(돌아가기)
                - "전체를 탐지합니다." Button(돌아가기)
                - "이미 탐지중인 키워드입니다." Button(돌아가기)
        - Button(탐지 키워드 삭제)
            - "삭제하실 키워드를 선택하세요." Button([키워드]), Button(돌아가기)
                - "[키워드]가 삭제되었습니다." Button(돌아가기)
                - "해당 키워드는 탐지중이지 않습니다." Button(돌아가기)
                - "전체 탐지가 해제되었습니다." Button(돌아가기)
            - "탐지중인 키워드가 없습니다." Button(돌아가기)
    - Button(알림 설정)
        - Button(알림 시작 / 알림 중지), Button(돌아가기)

- **/help**
    - /keyboardon: "키보드 버튼 켜기"
    - /keyboardoff: "키보드 버튼 끄기"
    - /settings: "탐지 및 알림 설정"
    - /help: "도움말"

- **/manage**
    - Button(오류 로그 조회)


- **CustomKeyboard**
    - 탐지 동네 설정
        - 탐지 동네 조회
        - 탐지 동네 추가
        - 탐지 동네 삭제
        - 돌아가기
    - 탐지 키워드 설정
        - 탐지 키워드 조회
        - 탐지 키워드 추가
        - 탐지 키워드 삭제
        - 돌아가기
    - 알림 설정
    - 키보드 끄기

## 3. 핵심 기능 구현 상세
### 3.1 나눔 상품 스크래핑 탐지
- **링크 쿼리 규칙**:
    - 기본 링크: https://www.daangn.com/kr/buy-sell/s/?
    - 나눔: &price=0__0
    - 동네: &in=XX동-<번호> 또는 &in=<번호>
    - 상품 키워드: &search=<키워드>
        - 상품 멀티 키워드 (AND): &search=<키워드>+<키워드>
        - 스페이스는 +로 대체
        - 전체 탐지: &search= 생략

- **상품 링크 수집 및 비교**
    - 1분마다 스크래핑 실행
    - 탐지 동네 및 키워드 조합으로 링크 쿼리 생성
        - 멀티 키워드는 +로 연결하여 쿼리 생성
        - 전체 탐지 경우 &search= 생략
    - Requests의 proxies 옵션 활용해 프록시 서버를 통한 요청으로 IP 차단 방지
        - USER, PASS, HOST_1~HOST_12, PORT는 .env 관리
            - Github Actions에서 .env 파일을 secrets로 관리
        - HOST는 15분마다 교체
    - User-Agent Mixer
        - 추적 및 차단을 피하기 위해 User-Agent를 주기적으로 교체
        - user-agents.py, user-agents.txt를 참고해 적절히 변형해 사용
    - 가장 최신 상품 링크 Selector: 
    ```css
    '#main-content > div._1j555bm0.sprinkles_paddingLeft_4_base__1byufe8g6.sprinkles_paddingLeft_10_small__1byufe8gr.sprinkles_paddingLeft_16_medium__1byufe8h4.sprinkles_paddingLeft_20_large__1byufe8h9.sprinkles_paddingRight_4_base__1byufe8e2.sprinkles_paddingRight_10_small__1byufe8en.sprinkles_paddingRight_16_medium__1byufe8f0.sprinkles_paddingRight_20_large__1byufe8f5.sprinkles_backgroundColor_layerDefault__1byufe8n.sprinkles_width_full_base__1byufe84q > div > section > div > div._12b29ll0.sprinkles_width_full_base__1byufe84q._12b29ll1 > a:nth-child(1)' 의 herf 링크값
    ```
    - 마지막 탐지 시점의 가장 최신 상품 링크와 비교
    - 링크값이 변경되었을 경우 새 상품으로 판단하여 텔레그램 봇으로 알림 전송
    - 페이지 소스 로딩 후, 짧은 대기 후 스크래핑 실행하여, 페이지 로딩 지연으로 인한 탐지 실패 방지
    - 최초 스크래핑 실패 시 10초 내 1회 재시도, 10초 초과시 TimeoutError로 간주하여 오류 로그 기록 및 다음 스크래핑 대상으로 넘어감
    - 스크래핑에 실패했을 경우 오류 로그 기록

### 3.2 동네 주소 수집 및 DB 저장
- **동네 주소 DB**:
    - XX도 XX시 (XX구) XX동 : <숫자>
    - dict + JSON
        - JSON 구조 예시: 
        ```json
        {
            "서울특별시 강남구 역삼동": "12345",
            "서울특별시 서초구 서초동": "67890"
        }
        ```

- **동네 주소 스크래핑 수집**:
    - https://www.daangn.com/kr/buy-sell/s/?in=<번호>
    - 1달에 1번 또는 유저 요청시 실행
    - 마지막 번호 이후부터 탐색
    - Requests의 proxies 옵션 활용해 프록시 서버를 통한 요청으로 IP 차단 방지
        - USER, PASS, HOST_1~HOST_12, PORT는 .env 관리
            - Github Actions에서 .env 파일을 secrets로 관리
        - HOST는 15분마다 교체
    - User-Agent Mixer
        - 추적 및 차단을 피하기 위해 User-Agent를 주기적으로 교체
        - user-agents.py, user-agents.txt를 참고해 적절히 변형해 사용
    - '#main-content > div._1j555bm0.sprinkles_paddingLeft_4_base__1byufe8g6.sprinkles_paddingLeft_10_small__1byufe8gr.sprinkles_paddingLeft_16_medium__1byufe8h4.sprinkles_paddingLeft_20_large__1byufe8h9.sprinkles_paddingRight_4_base__1byufe8e2.sprinkles_paddingRight_10_small__1byufe8en.sprinkles_paddingRight_16_medium__1byufe8f0.sprinkles_paddingRight_20_large__1byufe8f5.sprinkles_backgroundColor_layerDefault__1byufe8n.sprinkles_width_full_base__1byufe84q > div > div > h1' 의 text값에서, "중고거래" 키워드 제외한 주소값만 저장
    - 같은 주소가 여러 번호로 중복 수집될 경우 마지막 수집된 번호로 저장
    - 스크래핑에 실패했을 경우 오류 로그 기록
    
### 3.3 텔레그램 봇 구현
- **멀티 유저 서비스를 위한 JSON 저장**
    - chat_id
    - detect_link
        - 당근 기본 링크 + 동네 (&in=<번호>) + 키워드 (&search=<키워드>)
        - 0개~n개
        - 유저별로 탐지 설정에 따라 동네 및 키워드 조합으로 생성된 링크 저장
    - json 구조 예시:
    ```json
    {
        "users": [
            {
            "chat_id": "123456789",
            "notification": true,
            "subscriptions": [
                {
                "region": {
                    "full_name": "서울특별시 강남구 역삼동",
                    "dong_name": "역삼동",
                    "code": "12345"
                },
                "keyword": "아이폰",
                "detect_link": "https://www.daangn.com/search?in=12345&search=아이폰"
                },
                {
                "region": {
                    "full_name": "서울특별시 서초구 서초동",
                    "dong_name": "서초동",
                    "code": "67890"
                },
                "keyword": "맥북 중고",
                "detect_link": "https://www.daangn.com/search?in=67890&search=맥북+중고"
                }
            ]
            }
        ]
        }
    ``` 
- **유저별 탐지 설정 관리
    - 탐지 동네 설정
    - 탐지 키워드 설정
        - 키워드 미입력 시 전체 탐지로 간주
            - 전체 탐지 설정 시 기존 키워드 설정 무시하되, 값은 유지
                - 전체 탐지 취소시 기존 키워드 설정으로 탐지 재개
            - 전체 탐지 설정은 특별 키워드 (예: "전체")로 관리하여, 탐지 시 전체 탐지로 간주하여 처리
    - 알림 설정 (켜기/끄기)
- **텔레그램 메시지 포맷**
    - 제목: [당근마켓 나눔 탐지 알림]
    - 내용: [dong_name]에서 [keyword] 관련 나눔 상품이 올라왔습니다! 링크: [상품링크]
        - 상품 링크는 클릭시 앱으로 연결되도록 구현
        - 무조건 https://www.daangn.com 링크 기반으로 전송
- **텔레그램 메시지 전송**
    - 메시지 전송 시점: 새 상품 탐지 시, 유저가 알림 설정을 켜놓은 경우
    - 메시지 전송 실패 시 오류 로그 기록
- **텔레그램 봇 명령어 및 버튼 구현**
    - /start, /settings, /help, /manage 명령어 구현
    - CustomKeyboard를 활용한 탐지 설정 관리 버튼 구현
- **텔레그램 봇 UI/UX 설계에 따른 메시지 및 버튼 구현**
    - 각 명령어 및 버튼에 따른 메시지 및 기능 구현
- **텔레그램 봇과 스크래핑 기능 연동**
    - 스크래핑에서 탐지된 새 상품 정보를 텔레그램 봇으로 전달하여 알림 전송

### 3.4 오류 로그 기록
- 스크래핑 실패 및 기타 오류 발생 시 로그 기록
- 로그 파일: error.log
- 로그 포맷: [날짜 시간] [오류 유형] 오류 메시지
- 로그 레벨: ERROR
- 로그 기록 시점: 스크래핑 실패, 텔레그램 메시지 전송 실패, 기타 예외 발생 시

### 4. Github Actions CI/CD 설정
- **자동 배포**: main 브랜치에 푸시될 때마다 자동으로 배포되도록 설정
    - on: push: branches: [main]
- **환경 변수 관리**: .env 파일을 secrets로 관리하여 Github Actions 과정에서 생성할 수 있도록 설정
    - secrets.RPI3_SERVER_HOST, secrets.RPI3_SERVER_USER, secrets.RPI3_SERVER_KEY, secrets.PROXY_USER, secrets.PROXY_PASS, secrets.PROXY_HOST_1~secrets.PROXY_HOST_12, secrets.PROXY_PORT
- **테스트 스크립트**: 배포 전에 간단한 테스트 스크립트를 실행하여 주요 기능이 정상적으로 작동하는지 확인
- **배포 스크립트**: 배포 스크립트를 작성하여 자동으로 서버에 코드를 배포하고 필요한 서비스를 재시작하도록 설정
    - appleboy/ssh-action@v1.2.5
    - git pull & systemctl restart 방식
        - .env 파일 생성 및 토큰 주입
        - pip install pyproject.toml
    - docker build & run 방식
        - restart unless-stopped
        - env-file
        - volume
            - json
        - docker-entrypoint.sh
        - dockerignore
    - 양 방식 모두 작성 및 선택적으로 실행할 수 있도록 설정
    - docker 방식은 주석 처리

### 5. 보안 고려사항
- **환경 변수 보안**: .env 파일을 GitHub에 업로드하지 않고 secrets로 관리하여 보안 유지
- **프록시 서버 보안**: 프록시 서버의 사용자명, 비밀번호, 호스트 정보는 .env 파일로 관리하여 외부에 노출되지 않도록 설정
- **텔레그램 봇 토큰 보안**: 텔레그램 봇 토큰은 .env 파일로 관리하여 외부에 노출되지 않도록 설정
- **로그 파일 보안**: 로그 파일은 민감한 정보를 포함하지 않도록 주의하며, 접근 권한을 제한하여 보안 유지
- **코드 보안**: 스크래핑 및 텔레그램 봇 코드에서 외부 입력을 처리할 때는 적절한 검증 및 예외 처리를 통해 보안 취약점을 방지

### 6. 유지보수 및 확장성 고려사항
- **코드 구조화**: 기능별로 모듈화하여 코드의 가독성과 유지보수성을 높임
- **유저 데이터 관리**: 유저 데이터를 JSON 파일로 관리하되, 향후 데이터베이스로 확장할 수 있도록 설계
- **에러 핸들링**: 예외 처리를 통해 예상치 못한 오류 발생 시에도 시스템이 안정적으로 동작하도록 구현
- **확장성**: 향후 기능 추가 (예: 특정 카테고리 탐지, 멀티 플랫폼 지원 등)를 고려하여 코드 구조를 유연하게 설계

### 7. AI 개발 지침
- **크로스 코드 리뷰 및 개선**: AI 코드 작성 후, 타 AI 호출하여 코드 리뷰 및 개선 제안 받고, 제안된 개선 사항을 반영하여 코드 개선
    - Gemini CLI, Codex CLI, Copilot CLI
        - SKILL.md
        - Gemini CLI: gemini-reviewer.md
        - Codex CLI: 
            - codex-reviewer.md
            - codex /review
            - codex /improve
        - Copilot CLI: copilot-reviewer.md
        - 상세 명령어는 oneshot-command.md 참고

- **문서화**: AI 코드 작성 및 수정 시, 수정 히스토리 및 변경 사항을 상세히 문서화하여 추후 유지보수 및 협업에 용이하도록 함
    - 변경 사항: 언제, 어떤 부분이 어떻게 변경되었는지, 왜 변경되었는지에 대한 설명 포함