import os
import sqlite3
import json
import smtplib
import re
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright

import config

AI_KEYWORDS = [
    # 1. Core AI/ML
    'ai', 'ml', 'machine learning', 'deep learning', 'computer vision', 'nlp', 'llm', 'generative', 
    '인공지능', '머신러닝', '딥러닝', '자연어처리', '비전', '생성형',
    
    # 2. Data & Analytics
    'data scientist', 'data engineer', 'data analyst', 
    '데이터 분석가', '데이터 엔지니어', '데이터 사이언티스트', 'mlops',
    
    # 3. Research & Development
    'research', 'researcher', 'r&d', '연구원', '연구개발',
    
    # 4. Academic & Graduate
    '석박사', '산학장학생', '전문연구요원'
]

# 실제 채용 공고가 아닌 블로그, 기사, 기업문화, 메뉴 버튼 등을 걸러내기 위한 블랙리스트
NON_JOB_KEYWORDS = [
    '후기', '스케치', '테크톡톡', '윤리헌장', '소개드려요', '트렌드 전망', 
    '인포그래픽', '블로그', '인터뷰', '뉴스', 'news', '문화', '회사 홈페이지', '인재 영입', 
    '더 알아보기', '채용공고', 'core value', '로봇배달서비스', '배달의민족', 
    '엘리크루티비', '취향 지도', '채용안내'
]

def init_db():
    conn = sqlite3.connect('jobs.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS job_postings
                 (url TEXT PRIMARY KEY, title TEXT, company TEXT, date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    return conn

def is_ai_job(title):
    title_lower = title.lower()
    for keyword in AI_KEYWORDS:
        # 영어 알파벳이 하나라도 포함된 키워드(예: ai, ml, data)는 독립 단어(단어 경계)로만 매칭
        if re.search(r'[a-z]', keyword):
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, title_lower):
                return True
        else:
            # 순수 한글 키워드(예: 인공지능, 딥러닝)는 부분 문자열 매칭 허용 (예: 딥러닝연구원)
            if keyword in title_lower:
                return True
    return False

def scrape_site(browser, url, company_name):
    jobs = []
    print(f"크롤링 시작: {company_name} ({url})")
    
    # 봇 탐지 우회를 위해 User-Agent 설정
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()
    page_title = company_name
    
    try:
        # domcontentloaded 기준으로 먼저 화면을 띄우고
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        
        # SPA 렌더링을 위해 네트워크가 안정화될 때까지 기다리되, 무한 로딩 방지를 위해 최대 5초만 대기
        try:
            page.wait_for_load_state('networkidle', timeout=5000)
        except Exception:
            pass
            
        # 1. 영문 사이트 스킵
        lang = page.evaluate("document.documentElement.lang || ''")
        if lang.lower().startswith('en'):
            return [], company_name
            
        # 2. 마감된 공고 사이트 스킵
        try:
            body_text = page.locator("body").inner_text()
            if "지원 마감" in body_text or "모집 마감" in body_text or "채용 마감" in body_text:
                return [], company_name
        except Exception:
            pass
            
        
        # 페이지 타이틀 추출 (회사명/사이트명)
        fetched_title = page.title()
        if fetched_title:
            page_title = fetched_title

        # 동적 스크롤 (페이지네이션 또는 무한 스크롤 처리)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        
        # 모든 <a> 태그를 수집하여 범용적인 크롤링 수행
        links = page.query_selector_all('a')
        
        # 필터링을 위한 블랙리스트 (메뉴, 로그인, 소개 페이지 등)
        blacklist_words = [
            '로그인', 'login', '회원가입', 'sign up', '약관', 'terms', 'privacy', '개인정보',
            'about us', 'about', 'locations', 'teams', 'faq', 'q&a', '공지사항', 'notice',
            '회사소개', '인재상', '직무소개', '복리후생', 'benefits', 'culture', '지속가능',
            'sustainable', '지원하기', 'apply', 'myhyundai', 'hanwhain', '채용안내',
            '채용전형', '전형일정', '검색', 'search', '메뉴', 'menu', '채용홈', 'home',
            'jobs', 'careers', 'overview', 'contact'
        ]
        seen_titles = set()
        
        for link in links:
            raw_title = link.inner_text().strip()
            href = link.get_attribute('href')
            
            # 1. 텍스트나 링크가 없으면 제외
            if not raw_title or not href:
                continue
                
            # 여러 줄로 텍스트가 추출될 경우(예: D-12, #연구개발 등 태그 포함), 첫 번째 줄만 진짜 제목으로 사용
            title = raw_title.split('\n')[0].strip()
            
            # HTML 원시 코드(img, svg 등)가 그대로 딸려온 경우 제외
            if '<' in title and '>' in title:
                continue
                
            # 2. 길이가 너무 짧은 텍스트 제외 (최소 5자 이상) - 메뉴 버튼 방지
            if len(title) < 5:
                continue
                
            # 3. 블로그 기사, 인터뷰, 홈페이지 메뉴 등 제외
            is_garbage = False
            for garbage in NON_JOB_KEYWORDS:
                if garbage.lower() in title.lower():
                    is_garbage = True
                    break
            if is_garbage:
                continue

            # 4. 자바스크립트 실행 전용 링크나 단순 앵커(#) 제외
            if href.startswith('javascript') or href == '#':
                continue
                
            # 5. 블랙리스트 단어가 포함된 제목 제외
            title_lower = title.lower()
            if any(word in title_lower for word in blacklist_words):
                continue
                
            # 5. 현재 페이지에서 이미 수집한 제목(중복) 제외
            if title in seen_titles:
                continue
                
            seen_titles.add(title)
            full_url = page.evaluate('''(href) => new URL(href, document.baseURI).href''', href)
            jobs.append({'title': title, 'url': full_url, 'company': company_name})
                
    except Exception as e:
        print(f"에러 발생 [{company_name}]: {e}")
    finally:
        context.close()
        
    return jobs, page_title

def send_daily_summary_email(all_updates, threshold=5):
    """
    모든 사이트의 크롤링 결과를 모아서 이메일 1통으로 일괄 발송합니다.
    그룹사별로 사이트들을 묶어서 포맷팅합니다.
    """
    if not all_updates:
        return
        
    total_new_global = sum(len(u['new_jobs']) for u in all_updates)
    
    # 그룹사별로 데이터 묶기
    grouped_updates = {}
    for update in all_updates:
        comp = update['company']
        if comp not in grouped_updates:
            grouped_updates[comp] = []
        grouped_updates[comp].append(update)
        
    total_groups = len(grouped_updates)
    
    subject = f"[일간 채용 리포트] {total_groups}개 그룹사에서 총 {total_new_global}건의 신규 공고 발견!"
    body = "오늘의 신규 채용 공고 모아보기\n"
    body += "=" * 40 + "\n\n"
    
    for company, site_list in grouped_updates.items():
        body += f"🏢 그룹사: {company}\n\n"
        
        for site_info in site_list:
            site_url = site_info['site_url']
            site_title = site_info.get('site_title', company)
            new_jobs = site_info['new_jobs']
            ai_jobs = site_info['ai_jobs']
            total_new = len(new_jobs)
            
            body += f"  🔗 [{site_title}] 확인한 사이트: {site_url}\n"
            
            if total_new <= threshold:
                body += f"  👉 신규 공고 총 {total_new}건:\n"
                for j in new_jobs:
                    body += f"    - {j['title']}\n"
            else:
                if len(ai_jobs) > 0:
                    body += f"  👉 신규 공고 총 {total_new}건 중, AI 타겟 키워드 포함 공고 {len(ai_jobs)}건:\n"
                    for j in ai_jobs:
                        body += f"    - {j['title']}\n"
                else:
                    body += f"  👉 신규 공고 총 {total_new}건 대량 등록 (※ 타겟 AI 키워드 포함 직무 없음)\n"
                    body += f"    - 상세 공고는 위 링크에 직접 접속하여 확인해 주세요.\n"
            body += "\n"
                
        body += "-" * 40 + "\n\n"
            
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = config.EMAIL_SENDER
    msg['To'] = config.EMAIL_RECEIVER
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"일간 통합 이메일 발송 완료! (총 {total_new_global}건 신규)")
    except Exception as e:
        print(f"일간 통합 이메일 발송 실패: {e}")

def main():
    if config.EMAIL_SENDER == "본인의_지메일_주소@gmail.com":
        print("경고: config.py 파일에 이메일 설정을 먼저 입력해주세요!")
        return

    conn = init_db()
    c = conn.cursor()
    
    try:
        with open('discovered_urls.json', 'r', encoding='utf-8') as f:
            target_sites = json.load(f)
    except FileNotFoundError:
        print("discovered_urls.json 파일이 없습니다. url_discoverer.py를 먼저 실행하세요.")
        return

    total_inserted = 0
    TOO_MANY_THRESHOLD = 5 # 공고가 많다고 판단하는 기준 (5개 초과 시 키워드 필터링 적용)
    
    all_updates_for_today = []
    
    with sync_playwright() as p:
        # 깃허브 액션(CI) 환경에서는 기본 내장 Chromium 사용, 로컬(Mac)에서는 Chrome 사용
        is_ci = os.environ.get('GITHUB_ACTIONS') == 'true'
        browser_channel = None if is_ci else "chrome"
        browser = p.chromium.launch(headless=True, channel=browser_channel)
        
        for company, urls in target_sites.items():
            for site_url in urls:
                scraped_jobs, page_title = scrape_site(browser, site_url, company)
                
                new_jobs = []
                ai_jobs = []
                seen_urls_this_run = set()
                
                for job in scraped_jobs:
                    if job['url'] in seen_urls_this_run:
                        continue
                    seen_urls_this_run.add(job['url'])
                    
                    # DB 조회로 이미 발송/저장된 공고인지 확인
                    c.execute("SELECT url FROM job_postings WHERE url=?", (job['url'],))
                    if not c.fetchone():
                        new_jobs.append(job)
                        if is_ai_job(job['title']):
                            ai_jobs.append(job)
                        
                        # DB 저장
                        c.execute("INSERT INTO job_postings (url, title, company) VALUES (?, ?, ?)", 
                                  (job['url'], job['title'], job['company']))
                        total_inserted += 1
                
                if new_jobs:
                    conn.commit()
                    # 발송 대기열에 추가 (각 URL별로 각각 묶어서 추가)
                    all_updates_for_today.append({
                        'company': company,
                        'site_url': site_url,
                        'site_title': page_title,
                        'new_jobs': new_jobs,
                        'ai_jobs': ai_jobs
                    })

    # 모든 루프가 끝난 뒤 모아둔 공고가 있으면 메일 1통으로 통합 발송
    if all_updates_for_today:
        send_daily_summary_email(all_updates_for_today, TOO_MANY_THRESHOLD)
        
    print(f"크롤링 완료. 총 {total_inserted}건의 신규 공고가 처리되었습니다.")
    conn.close()

if __name__ == "__main__":
    main()
