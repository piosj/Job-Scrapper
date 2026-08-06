# AI Job Scraper & Notifier 🚀

주요 기업(삼성, 현대차, SK, LG 등) 및 빅테크의 채용 포털을 모니터링하여 **Applied AI Engineering, AI, ML** 관련 직무 공고가 올라오면 자동으로 알림을 보내주는 시스템입니다.

## 🌟 시스템 아키텍처
1. **URL 자동 탐색 (`url_discoverer.py`):** `duckduckgo-search` 패키지를 활용해 그룹사 내 개별 계열사의 채용 사이트 URL을 완전 무료로 동적 탐색합니다.
2. **동적 크롤링 (`scraper.py`):** `Playwright`를 통해 SPA(Single Page Application)로 렌더링된 채용 페이지의 요소를 렌더링한 후 공고 데이터를 추출합니다.
3. **필터링 및 비교:** SQLite DB(`jobs.db`)와 비교하여 중복을 제거하고, 직무명에 AI/ML 관련 키워드가 포함된 공고만 필터링합니다.
4. **자동 알림:** SMTP 프로토콜을 이용해 지정된 이메일(Gmail 등)로 새 공고 알림을 발송합니다.
5. **스케줄링:** GitHub Actions를 사용하여 매일 지정된 시간에 서버리스 환경에서 코드가 자동 실행됩니다.

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

### 3. 스크립트 실행
```bash
# 1단계: 타겟 계열사 URL 동적 탐색 (duckduckgo-search 사용)
python url_discoverer.py

# 2단계: 크롤링, 필터링 및 이메일 알림 발송
python scraper.py
```
