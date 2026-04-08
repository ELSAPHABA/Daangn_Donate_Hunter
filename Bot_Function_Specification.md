# Daangn_Donate_Hunter_bot - 상세 기능 명세서

당근마켓에서 특정 동네에서의 나눔 상품을 탐지하고, 실시간으로 텔레그램으로 알려주는 텔레그램 봇 구현 상세 가이드

## 1. 프로젝트 개요
- **목표**: 특정 주기로 당근마켓 웹 페이지를 스크래핑 해, 특정 동네에서 최신 나눔 상품이 올라왔을 경우 실시간으로 텔레그램으로 알려주는 텔레그램 봇 구현
- **기술 스택**: python-telegram-bot, beautifulsoup, ????

## 2. Telegram bot UI/UX 설계
- **/start**
    - 초기
        - "당근마켓에서 동네의 나눔 상품을 탐지합니다. 탐지 동네 및 키워드, 알림을 설정하시려면 /settings를 입력해 주세요."

- **Markup+Button**
    - /settings 입력시 응답
    - Button(탐지 동네 설정)
        - Button(탐지 동네 조회)
            - "현재 탐지중인 동네입니다: - (동네이름)", Button(돌아가기)
        - Button(탐지 동네 추가)
            - "추가하실 동네를 입력해 주세요. [XX도 XX시 (XX구) XX동] 형식으로 입력해 주세요." Button(돌아가기)
                - "[XX도 XX시 (XX구) XX동]이 추가되었습니다." Button(돌아가기)
                - "이미 탐지중인 동네입니다." Button(돌아가기)
                - "해당되는 동네가 없습니다. 다시 입력해주세요." Button(돌아가기)
        - Button(탐지 동네 삭제)
            - "삭제하실 동네를 선택하세요." Button(동네이름), Button(돌아가기)
                - "[XX도 XX시 (XX구) XX동]이 삭제되었습니다." Button(돌아가기)
            - "탐지중인 동네가 없습니다." Button(돌아가기)
    - Button(탐지 키워드 설정)
        - Button(탐지 키워드 조회)
            - "현재 탐지중인 키워드입니다: - (키워드)" Button(돌아가기)
        - Button(탐지 키워드 추가)
            - "추가하실 키워드를 입력해 주세요." Button(돌아가기)
                - "[키워드]가 추가되었습니다." Button(돌아가기)
                - "이미 탐지중인 키워드입니다." Button(돌아가기)
        - Button(탐지 키워드 삭제)
            - "삭제하실 키워드를 선택하세요." Button(키워드), Button(돌아가기)
                - "[키워드]가 삭제되었습니다." Button(돌아가기)
            - "탐지중인 키워드가 없습니다." Button(돌아가기)
    - Button(알림 설정)
        - Button(알림 시작 / 알림 중지), Button(돌아가기)

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
        
- **/help**
    - /keyboardon: "키보드 버튼 켜기"
    - /keyboardoff: "키보드 버튼 끄기"
    - /settings: "탐지 및 알람 설정"

## 3. 핵심 기능 구현 상세
### 3.1 나눔 상품 스크래핑 탐지
- **링크 쿼리 규칙**:
    - 기본 링크: https://www.daangn.com/kr/buy-sell/s/?
    - 나눔: &price=0__0
    - 동네: &in=XX동-<번호> 또는 &in=<번호>
    - 상품 키워드: &search=<키워드>
        - 상품 멀티 키워드 (AND): &search=<키워드>+<키워드>
        - 스페이스는 +로 대체
    - 거래 가능만 보기: &only_on_sale=true

- **상품 링크 수집 및 비교**
    - 가장 최신 상품 링크 Selector: '#main-content > div._1j555bm0.sprinkles_paddingLeft_4_base__1byufe8g6.sprinkles_paddingLeft_10_small__1byufe8gr.sprinkles_paddingLeft_16_medium__1byufe8h4.sprinkles_paddingLeft_20_large__1byufe8h9.sprinkles_paddingRight_4_base__1byufe8e2.sprinkles_paddingRight_10_small__1byufe8en.sprinkles_paddingRight_16_medium__1byufe8f0.sprinkles_paddingRight_20_large__1byufe8f5.sprinkles_backgroundColor_layerDefault__1byufe8n.sprinkles_width_full_base__1byufe84q > div > section > div > div._12b29ll0.sprinkles_width_full_base__1byufe84q._12b29ll1 > a:nth-child(1)' 의 herf 링크값

### 3.? 동네 주소 수집 및 DB 저장
- **동네 주소 DB**:
    - XX도 XX시 (XX구) XX동 : <숫자>
    - dict + JSON

- **동네 주소 스크래핑 수집**:
    - 1달에 1번 또는 유저 요청시 실행
    - 마지막 번호 이후부터 탐색
    - User-Agent Mixer
- 
### 3.? 텔레그램 봇 구현
- 