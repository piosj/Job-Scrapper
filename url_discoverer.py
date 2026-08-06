import os
import sys
import requests
import json
import config
import time
from urllib.parse import urlparse

def discover_career_urls_serper(company_name, api_key):
    """
    Serper.dev API를 사용하여 특정 그룹/계열사의 채용 사이트 URL을 구글 검색으로 탐색합니다.
    DuckDuckGo의 크롤링 차단 및 낮은 검색 품질 문제를 우회합니다.
    """
    url = "https://google.serper.dev/search"
    # 그룹 전체의 채용 포털을 검색하도록 쿼리 수정
    query = f"{company_name} 그룹 채용 사이트 OR recruit OR careers"
    
    payload = json.dumps({
      "q": query,
      "num": 30
    })
    headers = {
      'X-API-KEY': api_key,
      'Content-Type': 'application/json'
    }
    
    career_urls = [] # 단순 URL 리스트 (도메인 단위의 지나친 중복 제거 방지)
    seen_urls = set()
    
    # 잡코리아, 자소설닷컴 등 채용 포털이나 뉴스 사이트, SNS 제외
    forbidden_domains = [
        'jobkorea', 'saramin', 'incruit', 'catch', 'linkareer', 'wanted', 
        'blind', 'remember', 'news', 'cnn', 'myntra', 'jasoseol', 'linkedin', 
        'instagram', 'greenhouse.io', 'jobs.ac.kr', 'work.go.kr', 'peoplenjob',
        'facebook', 'youtube', 'blog.naver', 'brunch.co.kr'
    ]
    
    # 채용 공고가 아닌 정보성/홍보성 페이지 제외 키워드
    forbidden_content = [
        '블로그', '기자단', '인사제도', '매거진', '스토리', '뉴스룸', 
        '저널', '안내', '소개', '문화', '인터뷰'
    ]
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        results = response.json().get('organic', [])
        
        for item in results:
            link = item.get('link', '')
            link_lower = link.lower()
            title = item.get('title', '').lower()
            snippet = item.get('snippet', '').lower()
            
            # 1차: 잡포털 도메인 필터링
            if any(forbidden in link_lower for forbidden in forbidden_domains):
                continue
                
            # 2차: 제목이나 내용에 블로그/안내 등 제외 키워드 포함 시 필터링
            if any(fc in title or fc in snippet for fc in forbidden_content):
                continue
                
            # 3차: URL에 기업 공식 채용 관련 키워드 포함 확인
            if any(kw in link_lower for kw in ['career', 'recruit', 'hire', 'jobs', 'talent']):
                if link not in seen_urls:
                    seen_urls.add(link)
                    career_urls.append(link)
                
        return career_urls
    except Exception as e:
        print(f"Error discovering URLs for {company_name}: {e}")
        return []

if __name__ == "__main__":
    if not hasattr(config, 'SERPER_API_KEY') or config.SERPER_API_KEY == "여기에_SERPER_API_KEY_입력":
        print("경고: config.py 파일에 SERPER_API_KEY를 먼저 입력해주세요!")
        print("가입 및 발급처: https://serper.dev (2500건 완전 무료)")
        exit(1)
        
    # 실행 시 터미널에서 회사명을 입력받으면 해당 회사만 추가, 아니면 기본 리스트 실행
    if len(sys.argv) > 1:
        target_groups = sys.argv[1:]
        print(f"🚀 지정된 기업만 추가 검색합니다: {target_groups}")
    else:
        target_groups = [
            "삼성", "현대", "SK", "LG", "한화", "포스코", 
            "네이버", "카카오", "롯데", "한미"
        ]
        print("기본 그룹 전체를 대상으로 채용 사이트를 탐색합니다...")
    
    # 기존에 저장된 파일이 있으면 불러오기 (데이터 누적을 위해)
    all_career_sites = {}
    json_path = 'discovered_urls.json'
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                all_career_sites = json.load(f)
        except json.JSONDecodeError:
            pass

    for group in target_groups:
        print(f"[{group}] 채용 사이트 탐색 중...")
        urls = discover_career_urls_serper(group, config.SERPER_API_KEY)
        # 기존에 데이터가 있더라도 새로운 결과로 덮어쓰거나, 없으면 새로 추가됨
        all_career_sites[group] = urls
        print(f"발견된 URL: {urls}\n")
        time.sleep(1) # API 호출 간 짧은 대기
        
    # 결과를 파일에 누적 저장
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_career_sites, f, ensure_ascii=False, indent=4)
    print("✅ discovered_urls.json 파일 업데이트가 완료되었습니다.")
