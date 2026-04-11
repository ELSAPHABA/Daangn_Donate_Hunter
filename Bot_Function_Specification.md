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
            - "추가하실 키워드를 입력해 주세요." Button(돌아가기)
                - "[키워드]가 추가되었습니다." Button(돌아가기)
                - "이미 탐지중인 키워드입니다." Button(돌아가기)
        - Button(탐지 키워드 삭제)
            - "삭제하실 키워드를 선택하세요." Button([키워드]), Button(돌아가기)
                - "[키워드]가 삭제되었습니다." Button(돌아가기)
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

- **상품 링크 수집 및 비교**
    - 1분마다 스크래핑 실행
    - 탐지 동네 및 키워드 조합으로 링크 쿼리 생성
    - Requests의 proxies 옵션 활용해 프록시 서버를 통한 요청으로 IP 차단 방지
        - USER, PASS, HOST[1]~HOST[12], PORT는 .env 관리
        - HOST는 15분마다 교체
    - User-Agent Mixer
        - 추적 및 차단을 피하기 위해 User-Agent를 주기적으로 교체
        - user-agents.py, user-agents.txt를 참고해 적절히 변형해 사용
    - 가장 최신 상품 링크 Selector: '#main-content > div._1j555bm0.sprinkles_paddingLeft_4_base__1byufe8g6.sprinkles_paddingLeft_10_small__1byufe8gr.sprinkles_paddingLeft_16_medium__1byufe8h4.sprinkles_paddingLeft_20_large__1byufe8h9.sprinkles_paddingRight_4_base__1byufe8e2.sprinkles_paddingRight_10_small__1byufe8en.sprinkles_paddingRight_16_medium__1byufe8f0.sprinkles_paddingRight_20_large__1byufe8f5.sprinkles_backgroundColor_layerDefault__1byufe8n.sprinkles_width_full_base__1byufe84q > div > section > div > div._12b29ll0.sprinkles_width_full_base__1byufe84q._12b29ll1 > a:nth-child(1)' 의 herf 링크값
    - 마지막 탐지 시점의 가장 최신 상품 링크와 비교
    - 링크값이 변경되었을 경우 새 상품으로 판단하여 텔레그램 봇으로 알림 전송
    - 스크래핑에 실패했을 경우 오류 로그 기록

### 3.? 동네 주소 수집 및 DB 저장
- **동네 주소 DB**:
    - XX도 XX시 (XX구) XX동 : <숫자>
    - dict + JSON

- **동네 주소 스크래핑 수집**:
    - https://www.daangn.com/kr/buy-sell/s/?in=<번호>
    - 1달에 1번 또는 유저 요청시 실행
    - 마지막 번호 이후부터 탐색
    - Requests의 proxies 옵션 활용해 프록시 서버를 통한 요청으로 IP 차단 방지
        - USER, PASS, HOST[1]~HOST[12], PORT는 .env 관리
        - HOST는 15분마다 교체
    - User-Agent Mixer
        - 추적 및 차단을 피하기 위해 User-Agent를 주기적으로 교체
        - user-agents.py, user-agents.txt를 참고해 적절히 변형해 사용
    - '#main-content > div._1j555bm0.sprinkles_paddingLeft_4_base__1byufe8g6.sprinkles_paddingLeft_10_small__1byufe8gr.sprinkles_paddingLeft_16_medium__1byufe8h4.sprinkles_paddingLeft_20_large__1byufe8h9.sprinkles_paddingRight_4_base__1byufe8e2.sprinkles_paddingRight_10_small__1byufe8en.sprinkles_paddingRight_16_medium__1byufe8f0.sprinkles_paddingRight_20_large__1byufe8f5.sprinkles_backgroundColor_layerDefault__1byufe8n.sprinkles_width_full_base__1byufe84q > div > div > h1' 의 text값에서, "중고거래" 키워드 제외한 주소값만 저장
    - 같은 주소가 여러 번호로 중복 수집될 경우 마지막 수집된 번호로 저장
    - 스크래핑에 실패했을 경우 오류 로그 기록
    
### 3.? 텔레그램 봇 구현
-  멀티 유저 서비스를 위한 chat_id, detect_link JSON 저장
    - chat_id:
    - detect_link
        - 당근 기본 링크 + 동네 (&in=<번호>) + 키워드 (&search=<키워드>)
        - 0개~n개
-  유저별 탐지 설정 관리
    - 탐지 동네 설정
    - 탐지 키워드 설정
    - 알림 설정