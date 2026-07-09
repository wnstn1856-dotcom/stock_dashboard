# GitHub Actions로 자동 갱신하기 (완전 무료, PC 꺼놔도 동작)

이 폴더에는 이미 `.github/workflows/update-dashboard.yml`이 들어있습니다. 이 폴더를 GitHub에
올리기만 하면, GitHub가 30분마다 자동으로 대시보드를 새로 만들어서 웹페이지로 보여줍니다. 진짜
실시간(초 단위)은 아니지만, 컴퓨터를 꺼둬도 계속 갱신되고 스마트폰에서도 링크 하나로 확인할 수 있습니다.

프로그래밍 경험이 없어도 따라할 수 있도록 마우스 클릭 위주로 설명합니다.

## 0단계. 준비물

- GitHub 계정 (없으면 https://github.com 에서 무료로 만들 수 있습니다 - 이메일만 있으면 됩니다)
- GitHub Desktop 프로그램 (https://desktop.github.com 에서 무료 다운로드, Git 명령어를 몰라도 됨)

## 1단계. GitHub 계정 만들기

1. https://github.com 접속 → 오른쪽 위 "Sign up" 클릭
2. 이메일, 비밀번호, 아이디 입력하고 가입 완료

## 2단계. GitHub Desktop 설치 및 로그인

1. https://desktop.github.com 에서 다운로드 후 설치
2. 실행 후 "Sign in to GitHub.com" 클릭 → 방금 만든 계정으로 로그인

## 3단계. 이 폴더를 저장소로 등록하기

1. GitHub Desktop 왼쪽 위 "File" → "Add local repository" 클릭
2. "Choose..." 버튼으로 이 폴더를 선택: `C:\Users\ibr\Desktop\클로드\stock_dashboard`
3. "이 폴더는 Git 저장소가 아닙니다. 저장소로 만들까요?" 같은 메시지가 뜨면 **"create a repository"** 클릭
4. 저장소 이름은 그대로 두거나 원하는 이름으로 (예: `stock-dashboard`) 입력하고 "Create Repository" 클릭

## 4단계. GitHub에 업로드(Publish)하기

1. GitHub Desktop 화면 위쪽에 있는 **"Publish repository"** 버튼 클릭
2. **"Keep this code private" 체크를 해제**하세요 (공개 저장소로 만들어야 무료로 자동 실행 시간 제한 없이,
   그리고 무료로 웹페이지 호스팅(GitHub Pages)까지 쓸 수 있습니다). 종목 코드/설정 파일에는 개인정보나
   계좌 정보가 없으니 공개해도 안전합니다.
3. "Publish Repository" 클릭 → 완료되면 GitHub 웹사이트에 이 폴더가 그대로 올라갑니다

## 5단계. 자동 실행(Actions) 확인

1. 브라우저에서 본인 GitHub 저장소 페이지로 이동 (예: `https://github.com/내아이디/stock-dashboard`)
2. 상단 메뉴에서 **"Actions"** 탭 클릭
3. "Update Stock Dashboard"라는 워크플로가 보일 것입니다. 처음엔 자동으로 안 도니까,
   그 워크플로 이름을 클릭 → 오른쪽의 **"Run workflow"** 버튼 → 다시 "Run workflow" 클릭해서 수동으로 한 번
   실행해보세요.
4. 1~5분 정도 기다리면 초록색 체크 표시가 뜹니다 (실패하면 빨간색 X, 클릭하면 에러 로그를 볼 수 있어요)
5. 이후로는 `.github/workflows/update-dashboard.yml`에 설정된 대로 30분마다 자동으로 실행됩니다

## 6단계. 웹페이지로 보기 (GitHub Pages) 활성화

1. 저장소 페이지에서 **"Settings"** 탭 클릭
2. 왼쪽 메뉴에서 **"Pages"** 클릭
3. "Build and deployment" → Source: **"Deploy from a branch"** 선택
4. Branch: **"main"**, 폴더: **"/docs"** 선택 후 **"Save"**
5. 몇 분 기다리면 이 페이지 위쪽에 초록색으로 "Your site is live at https://내아이디.github.io/stock-dashboard/"
   같은 링크가 뜹니다. 이 링크를 즐겨찾기 해두면, PC를 꺼놔도 최신 대시보드를 어디서든 볼 수 있습니다.

## 이후에는?

- 30분마다 GitHub 서버가 자동으로 국내/해외 데이터를 다시 수집해서 Pages 링크를 갱신합니다.
- 로컬(내 컴퓨터)에서 `python main.py`를 직접 돌리면 그건 별개로 `dashboard_날짜.html` 파일이 새로 생기는
  것이고, GitHub 자동 실행과는 무관합니다. GitHub 쪽 결과만 보고 싶으면 Pages 링크만 확인하면 됩니다.
- 뉴스 수집까지 자동 실행에 포함하고 싶거나, 종목 수를 늘리거나, 주기를 바꾸고 싶으면
  `.github/workflows/update-dashboard.yml` 파일을 열어서 `KR_TOP_N`, `US_UNIVERSE_SIZE`, `cron` 값을
  수정한 뒤 GitHub Desktop에서 다시 커밋(Commit) → 푸시(Push)하면 됩니다.
- 워크플로 파일을 수정할 때 종목 수를 너무 크게 올리면 `timeout-minutes: 15`(15분 제한)를 넘겨 실패할 수
  있습니다. 그 경우 timeout-minutes 값도 함께 늘려주세요.

## 참고: 이게 진짜 "실시간"인가요?

아닙니다. 여전히 무료 API의 지연 시세(15~20분 지연)를 쓰고, 30분마다 스냅샷을 새로 찍는 방식입니다. 다만
- 사람이 직접 `python main.py`를 매번 실행할 필요가 없어지고
- 컴퓨터를 꺼둬도 계속 갱신되고
- 스마트폰 등 어느 기기에서든 링크로 확인 가능해진다는 점에서, 실질적으로 "자동으로 계속 최신 상태를 보여주는"
경험에 가장 가깝습니다. 진짜 초 단위 실시간이 꼭 필요하다면 한국투자증권 Open API 같은 증권사 연동이
필요한데, 이건 별도로 요청해주시면 추가해드릴게요.
