# AI Job Scraper & Notifier 🚀

주요 기업(삼성, 현대차, SK, LG 등) 및 빅테크의 채용 포털을 모니터링하여 **Applied AI Engineering, AI, ML** 관련 직무 공고가 올라오면 자동으로 알림을 보내주는 시스템입니다.

## 🌟 시스템 아키텍처
1. **URL 타겟팅 (`discovered_urls.json`):** 크롤링할 정확한 채용 공고 게시판 URL들을 수동으로 관리하여 높은 정확도를 보장합니다.
2. **동적 크롤링 (`scraper.py`):** `Playwright`를 통해 SPA(Single Page Application)로 렌더링된 채용 페이지의 요소를 렌더링한 후 공고 데이터를 추출합니다.
3. **필터링 및 비교:** SQLite DB(`jobs.db`)와 비교하여 중복을 제거하고, 직무명에 AI/ML 관련 키워드가 포함된 공고만 깐깐하게 필터링합니다. (뉴스 기사, 사내 블로그 등 제외 로직 포함)
4. **자동 알림:** SMTP 프로토콜을 이용해 지정된 이메일(Gmail 등)로 새 공고 알림을 발송합니다.
5. **스케줄링:** GitHub Actions를 사용하여 매일 지정된 시간(09:00, 18:00)에 클라우드 환경에서 코드가 자동 실행됩니다.

## 🛠 환경 설정 및 실행 방법

### 1. 가상 환경 생성 및 의존성 설치
```bash
# 가상 환경 생성
python -m venv venv

# 가상 환경 활성화 (Mac/Linux)
source venv/bin/activate

# 의존성 패키지 설치
pip install -r requirements.txt

# Playwright 브라우저 바이너리 설치 (크롤링용)
python -m playwright install chromium
```

### 2. 환경 변수 및 설정 파일 (`config.py`)
이메일 알림을 받기 위해 프로젝트 최상단에 `config.py` 파일이 있습니다. 본인의 정보로 수정해주세요.
**(구글 API 키는 더 이상 필요하지 않습니다!)**

```python
# config.py
EMAIL_SENDER = "본인의_지메일_주소@gmail.com"
EMAIL_PASSWORD = "여기에_지메일_앱_비밀번호_입력"
EMAIL_RECEIVER = "알림을_받을_이메일_주소@gmail.com"
```
> **주의:** 보안을 위해 이 파일은 `git`에 커밋하지 않도록 `.gitignore`에 등록해야 합니다.

### 3. 로컬에서 수동 스크립트 실행 (테스트용)
```bash
python scraper.py
```
> **Tip:** 테스트 후 특정 회사의 발송 내역만 DB에서 지우려면 `sqlite3 jobs.db "DELETE FROM job_postings WHERE company='토스';"` 명령어를 활용하세요.

### 4. 🤖 깃허브 액션(GitHub Actions)으로 매일 자동 메일 받기 (추천)
로컬 PC를 켜두지 않아도 깃허브 클라우드에서 매일 오전 8시, 오후 6시에 크롤러가 자동으로 실행되어 메일을 보내주게 할 수 있습니다.

**1단계: 깃허브(GitHub)에 코드 올리기**
1. 깃허브에 **Private Repository**를 새로 생성합니다.
2. 로컬 터미널에서 아래 명령어로 코드를 푸시합니다.
```bash
git init
git add .
git commit -m "최종 채용공고 크롤러 완성"
git remote add origin https://github.com/아이디/레포지토리이름.git
git branch -M main
git push -u origin main
```

**2단계: 깃허브 보안 비밀금고(Secrets)에 이메일 정보 등록하기**
코드를 공개(Public)로 돌리더라도 안전하게 이메일을 발송하기 위해 Secrets를 사용합니다.
1. 깃허브 레포지토리 상단의 **[Settings]** 탭 클릭
2. 왼쪽 메뉴 **[Secrets and variables]** -> **[Actions]** 클릭
3. 초록색 **[New repository secret]** 버튼을 눌러 아래 3가지를 생성합니다.
   * Name: `EMAIL_SENDER` / Secret: `보내는사람메일@gmail.com`
   * Name: `EMAIL_PASSWORD` / Secret: `구글앱비밀번호16자리`
   * Name: `EMAIL_RECEIVER` / Secret: `받는사람메일@gmail.com`

**3단계: DB 쓰기 권한 허용하기**
크롤러가 깃허브 액션 환경에서 수집을 마친 뒤 `jobs.db`에 저장 내역을 기록(Commit & Push)해야 메일 중복 발송을 막을 수 있습니다.
1. 깃허브 **[Settings]** -> 왼쪽 메뉴 **[Actions]** -> **[General]** 클릭
2. 스크롤을 맨 아래로 내려서 **Workflow permissions** 항목 찾기
3. **`Read and write permissions`** 체크 후 [Save] 클릭

설정이 모두 끝났습니다! 이제 [Actions] 탭에서 `Daily AI Job Scraper` 워크플로우를 선택한 뒤 **[Run workflow]** 버튼을 눌러 첫 테스트 메일을 보내보세요!
