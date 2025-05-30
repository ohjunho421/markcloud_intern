from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import os
import requests
import datetime
import json
import pandas as pd
import random
import re
import traceback
import threading
import dateparser
from datetime import timedelta

# 전역 변수 정의
instagram_username = None
instagram_password = None

# 스레드 안전 글로벌 변수와 잠금
processed_ids_lock = threading.Lock()
all_posts_summary_lock = threading.Lock()

# 크롬 드라이버 설정
chrome_options = Options()
# chrome_options.add_argument("--headless")  # 백그라운드 실행 시 주석 해제
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--start-maximized")  # 창 최대화로 더 많은 요소 로드
# 로그 메시지 감소
chrome_options.add_argument("--log-level=3")
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
# 사용자 에이전트 설정 (최신 크롬 버전)
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

def create_driver():
    """새 브라우저 드라이버 인스턴스 생성 및 반환"""
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

# 로그 저장 파일
def setup_logging(save_dir):
    os.makedirs(save_dir, exist_ok=True)
    log_file = os.path.join(save_dir, "scraping_log.txt")
    return log_file

def log_message(log_file, message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

# 인스타그램 로그인
def instagram_login(driver, username, password, log_file):
    log_message(log_file, "로그인 시도 중...")
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(5)  # 로딩 대기
    
    # 쿠키 수락 버튼이 있다면 클릭
    try:
        cookie_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Allow') or contains(text(), '수락')]")
        if cookie_buttons:
            cookie_buttons[0].click()
            time.sleep(2)
    except Exception as e:
        log_message(log_file, f"쿠키 수락 버튼 클릭 오류: {e}")
    
    # 로그인 폼 작성
    try:
        username_input = driver.find_element(By.CSS_SELECTOR, "input[name='username']")
        password_input = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
        
        username_input.send_keys(username)
        password_input.send_keys(password)
        
        # 로그인 버튼 클릭
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        
        # 로그인 완료 대기
        time.sleep(7)
    except Exception as e:
        log_message(log_file, f"로그인 입력 오류: {e}")
    
    # "나중에 하기" 버튼이 나타나면 클릭
    try:
        not_now_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), '나중에 하기') or contains(text(), 'Not Now') or contains(text(), 'Skip')]")
        if not_now_buttons:
            not_now_buttons[0].click()
            time.sleep(2)
    except:
        pass
    
    # 알림 설정 나중에 하기가 나타나면 클릭
    try:
        notifications_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '나중에 하기') or contains(text(), 'Not Now') or contains(text(), 'Skip')]"))
        )
        notifications_button.click()
        time.sleep(2)
    except:
        pass
    
    log_message(log_file, "로그인 완료!")

def is_reels_url(url):
    """URL이 릴스인지 확인"""
    return '/reel/' in url or '/reels/' in url

def get_post_type(url):
    """게시물 타입 판별 (post/reel)"""
    if is_reels_url(url):
        return "reel"
    elif '/p/' in url:
        return "post"
    else:
        return "unknown"

# 인스타그램 날짜 파싱
def parse_instagram_date(date_text):
    """
    인스타그램의 상대적 날짜 텍스트를 datetime 객체로 파싱
    """
    if not date_text or date_text == "날짜 정보 없음":
        return datetime.datetime.now()
    
    # 인스타그램의 상대적 날짜 형식 처리
    try:
        # 다양한 형식에 대해 dateparser로 시도
        parsed_date = dateparser.parse(date_text, languages=['ko', 'en'])
        
        if parsed_date:
            return parsed_date
        
        # 특정 형식에 대한 수동 파싱
        if "주" in date_text or "week" in date_text.lower():
            weeks = int(re.search(r'(\d+)', date_text).group(1))
            return datetime.datetime.now() - timedelta(weeks=weeks)
        elif "일" in date_text or "day" in date_text.lower():
            days = int(re.search(r'(\d+)', date_text).group(1))
            return datetime.datetime.now() - timedelta(days=days)
        elif "시간" in date_text or "hour" in date_text.lower():
            hours = int(re.search(r'(\d+)', date_text).group(1))
            return datetime.datetime.now() - timedelta(hours=hours)
        elif "분" in date_text or "minute" in date_text.lower():
            minutes = int(re.search(r'(\d+)', date_text).group(1))
            return datetime.datetime.now() - timedelta(minutes=minutes)
    except:
        pass
    
    # 현재 날짜로 대체
    return datetime.datetime.now()

def format_date_for_filename(date_obj):
    """
    datetime 객체를 파일명 친화적인 문자열로 형식화 (YYYY-MM-DD)
    """
    return date_obj.strftime("%Y-%m-%d")

# 게시물 날짜 추출
def extract_post_date_text(driver):
    """
    게시물에서 날짜 텍스트 추출
    """
    try:
        # time 요소 또는 그 부모 요소에서 날짜 텍스트 찾기
        date_text = None
        
        # 방법 1: time 요소 자체
        time_elements = driver.find_elements(By.XPATH, "//time")
        if time_elements:
            date_text = time_elements[0].text.strip()
            if date_text:
                return date_text
        
        # 방법 2: time 요소의 부모
        time_parents = driver.find_elements(By.XPATH, "//time/..")
        if time_parents:
            date_text = time_parents[0].text.strip()
            if date_text:
                return date_text
        
        # 방법 3: JavaScript로 추출
        date_text = driver.execute_script("""
            const timeEl = document.querySelector('time');
            if (timeEl) return timeEl.textContent.trim() || timeEl.parentElement.textContent.trim();
            return '';
        """)
        
        if date_text:
            return date_text
    except:
        pass
    
    return "날짜 정보 없음"

# 게시물 링크 찾기 함수 (릴스 포함)
def find_all_post_links(driver, log_file):
    """
    현재 페이지의 모든 게시물 링크 찾기 (일반 게시물 + 릴스)
    """
    try:
        # JavaScript로 모든 게시물 링크 찾기
        links = driver.execute_script("""
            const links = [];
            const allLinks = document.querySelectorAll('a');
            for (const link of allLinks) {
                if (link.href && (link.href.includes('/p/') || link.href.includes('/reel/'))) {
                    links.push(link.href);
                }
            }
            return [...new Set(links)]; // 중복 제거
        """)
        
        if links:
            return links
    except Exception as e:
        log_message(log_file, f"JavaScript로 링크 검색 중 오류: {e}")
    
    # 기본 방법으로 찾기
    try:
        links = []
        # 일반 게시물과 릴스 모두 검색
        posts = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
        for post in posts:
            href = post.get_attribute('href')
            if href and ('/p/' in href or '/reel/' in href):
                links.append(href)
        
        unique_links = list(set(links))  # 중복 제거
        return unique_links
    except Exception as e:
        log_message(log_file, f"게시물 링크 검색 중 오류: {e}")
        return []

# 개선된 점진적 스크롤링 함수 (새로고침 없음, 릴스 포함)
def progressive_scrolling(driver, target_posts, log_file, max_scroll_attempts=100):
    """
    새로고침 없이 점진적으로 스크롤하여 게시물 로드 (릴스 포함)
    """
    log_message(log_file, f"점진적 스크롤링 시작 (목표: {target_posts}개 이상, 일반 게시물 + 릴스)")
    
    # 이전에 발견한 링크 추적
    found_links = set()
    scroll_count = 0
    no_new_links_count = 0
    
    # 초기 게시물 링크 수집
    initial_links = find_all_post_links(driver, log_file)
    found_links.update(initial_links)
    
    # 초기 타입별 분류
    post_count = sum(1 for link in found_links if '/p/' in link)
    reel_count = sum(1 for link in found_links if '/reel/' in link)
    log_message(log_file, f"초기 게시물: 총 {len(found_links)}개 (일반: {post_count}개, 릴스: {reel_count}개)")
    
    # 목표 게시물 수에 도달했는지 확인
    if len(found_links) >= target_posts:
        log_message(log_file, f"이미 충분한 게시물이 로드되었습니다: {len(found_links)}개")
        return list(found_links)
    
    # 스크롤링 시작
    while scroll_count < max_scroll_attempts:
        scroll_count += 1
        
        # 페이지 아래로 스크롤 (점진적으로)
        if scroll_count < 5:
            # 처음에는 천천히 스크롤
            driver.execute_script("window.scrollBy(0, 800);")
        else:
            # 나중에는 더 멀리 스크롤
            screen_height = driver.execute_script("return window.innerHeight;")
            driver.execute_script(f"window.scrollBy(0, {screen_height * 0.8});")
        
        # 게시물이 로드될 시간 대기
        time.sleep(3.5)
        
        # 새 게시물 링크 수집
        current_links = find_all_post_links(driver, log_file)
        new_links_count = 0
        
        for link in current_links:
            if link not in found_links:
                found_links.add(link)
                new_links_count += 1
        
        # 로그 기록 (타입별 카운트 포함)
        if scroll_count % 5 == 0 or new_links_count > 0:
            post_count = sum(1 for link in found_links if '/p/' in link)
            reel_count = sum(1 for link in found_links if '/reel/' in link)
            log_message(log_file, f"스크롤 #{scroll_count}: 총 {len(found_links)}개 (일반: {post_count}개, 릴스: {reel_count}개, 새로운: {new_links_count}개)")
        
        # 목표 게시물 수에 도달했는지 확인
        if len(found_links) >= target_posts:
            post_count = sum(1 for link in found_links if '/p/' in link)
            reel_count = sum(1 for link in found_links if '/reel/' in link)
            log_message(log_file, f"목표 달성! {len(found_links)}개 게시물 로드 완료 (일반: {post_count}개, 릴스: {reel_count}개)")
            break
        
        # 새 게시물이 발견되지 않으면 카운터 증가
        if new_links_count == 0:
            no_new_links_count += 1
        else:
            no_new_links_count = 0  # 새 게시물이 발견되면 카운터 리셋
        
        # 일정 횟수 동안 새 게시물이 발견되지 않으면 다른 스크롤 방법 시도
        if no_new_links_count >= 5:
            log_message(log_file, f"{no_new_links_count}회 연속 새 게시물이 발견되지 않음, 다른 방법 시도...")
            
            # 방법 1: 페이지 하단으로 완전히 스크롤
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # 방법 2: 위로 약간 스크롤했다가 다시 아래로
            driver.execute_script("window.scrollBy(0, -500);")
            time.sleep(1.5)
            driver.execute_script("window.scrollBy(0, 700);")
            time.sleep(1.5)
            
            # 방법 3: 스페이스바 누르기
            try:
                body = driver.find_element(By.TAG_NAME, 'body')
                body.send_keys(Keys.PAGE_DOWN)
                time.sleep(2)
            except:
                pass
            
            # 새 게시물 확인
            after_retry_links = find_all_post_links(driver, log_file)
            new_after_retry = len(set(after_retry_links) - found_links)
            
            if new_after_retry > 0:
                log_message(log_file, f"다른 방법으로 {new_after_retry}개의 새 게시물 발견!")
                found_links.update(after_retry_links)
                no_new_links_count = 0  # 카운터 리셋
            else:
                no_new_links_count += 1
                
                # 10회 이상 새 게시물이 발견되지 않으면 중단
                if no_new_links_count >= 10:
                    log_message(log_file, f"더 이상 새 게시물을 찾을 수 없습니다. 스크롤링 종료 (총 {len(found_links)}개)")
                    break
        
        # 15번마다 잠시 쉬기
        if scroll_count % 15 == 0:
            log_message(log_file, "스크롤링 잠시 쉬는 중...")
            time.sleep(3)
    
    # 정렬을 위해 리스트로 변환하고 최신순으로 정렬
    result_links = list(found_links)
    
    # 인스타그램은 기본적으로 최신순으로 표시되므로 수집된 순서를 유지
    # 하지만 확실히 하기 위해 역순으로 정렬 (페이지 상단이 최신)
    # result_links.reverse()  # 필요시 주석 해제
    
    post_count = sum(1 for link in result_links if '/p/' in link)
    reel_count = sum(1 for link in result_links if '/reel/' in link)
    log_message(log_file, f"스크롤링 완료: 총 {len(result_links)}개 게시물 발견 (일반: {post_count}개, 릴스: {reel_count}개)")
    log_message(log_file, "게시물은 최신순으로 처리됩니다.")
    
    return result_links

# 릴스 텍스트 추출 함수
def get_reels_text(driver, log_file):
    """
    릴스 게시물의 텍스트 내용 추출 (일반 게시물과 동일한 방식)
    """
    log_message(log_file, "릴스 텍스트 추출 시작 (일반 게시물 방식 사용)...")
    
    # 일반 게시물과 동일한 방식으로 텍스트 추출
    return get_post_text(driver, log_file)

# 텍스트 내용 가져오기 (일반 게시물용)
def get_post_text(driver, log_file):
    """
    인스타그램 게시물 본문 텍스트 내용 가져오기
    - 두 번째 'goodibk' 다음부터 댓글 시작 전까지의 텍스트 추출 (수정됨 포함)
    - 중복 내용 제거 및 줄바꿈 유지
    """
    log_message(log_file, "본문 텍스트 추출 시작...")
    
    # 1. 페이지 로딩 완료 대기 (최대 10초)
    try:
        # 본문 텍스트가 포함될 가능성이 높은 요소가 로드될 때까지 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//article"))
        )
        # 추가 대기 (완전한 로딩을 위해)
        time.sleep(3)
    except Exception as e:
        log_message(log_file, f"페이지 로딩 대기 중 오류: {str(e)}")
        # 계속 진행 (일부 내용이라도 추출 시도)
    
    # 2. "더 보기" 버튼 클릭 시도 (여러 방법으로)
    try:
        # JavaScript로 "더 보기" 버튼 클릭 (가장 안정적)
        driver.execute_script("""
            const moreButtons = document.querySelectorAll('div');
            for (const button of moreButtons) {
                if (button.textContent.includes('더 보기') || button.textContent.includes('more')) {
                    button.click();
                }
            }
        """)
        time.sleep(1)
    except:
        pass
    
    # 3. 전체 페이지 텍스트에서 두 번째 'goodibk' 다음부터 추출
    try:
        # 전체 페이지 텍스트
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        # 'goodibk'가 나타나는 모든 위치 찾기
        goodibk_positions = [m.start() for m in re.finditer('goodibk', page_text.lower())]
        
        if len(goodibk_positions) >= 2:
            # 두 번째 'goodibk' 위치
            second_goodibk_pos = goodibk_positions[1]
            
            # 두 번째 'goodibk' 다음부터 텍스트 시작
            text_start = page_text.find('\n', second_goodibk_pos)
            if text_start == -1:
                text_start = second_goodibk_pos + len('goodibk')
            else:
                text_start += 1  # 줄바꿈 문자 건너뛰기
            
            # 댓글 시작 위치 찾기 - 작은 시간 표시가 단독으로 있는 경우 (예: "1주")
            # 단, 본문의 "수정됨"은 포함해야 함
            comment_match = re.search(r'\n\s*\d+[주일시분]\s*\n', page_text[text_start:])
            
            if comment_match:
                # 시간 표시 직전까지 추출
                text_end = text_start + comment_match.start()
                extracted_text = page_text[text_start:text_end].strip()
            else:
                # 시간 표시를 찾지 못한 경우 끝까지 추출
                extracted_text = page_text[text_start:].strip()
                
                # 텍스트 끝에 있을 수 있는 시간 표시 제거
                extracted_text = re.sub(r'\s*\d+[주일시분]\s*$', '', extracted_text)
            
            # 중복 제거 및 정리 (수정됨은 유지)
            extracted_text = clean_and_deduplicate_text(extracted_text, keep_modified=True)
            
            log_message(log_file, f"두 번째 'goodibk' 이후 텍스트 추출 성공 (길이: {len(extracted_text)})")
            return extracted_text
        else:
            log_message(log_file, "두 번째 'goodibk'를 찾을 수 없음, 다른 방법 시도")
    except Exception as e:
        log_message(log_file, f"텍스트 추출 중 오류: {str(e)}")
    
    # 모든 방법 실패 시
    return ""

def clean_and_deduplicate_text(text, keep_modified=True):
    """
    텍스트 중복 제거 및 정리
    - 연속된 같은 줄 제거
    - 줄바꿈 유지
    - 시작/끝 공백 제거
    - 수정됨 텍스트 유지 옵션
    """
    if not text:
        return ""
    
    # 줄 단위로 분할
    lines = text.split('\n')
    
    # 중복 줄 제거
    unique_lines = []
    previous_line = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # "수정됨"이 포함된 줄은 항상 포함 (keep_modified가 True인 경우)
        if keep_modified and '수정됨' in line:
            unique_lines.append(line)
            previous_line = line
            continue
            
        # 이전 줄과 다른 경우만 추가
        if line != previous_line:
            unique_lines.append(line)
            previous_line = line
    
    # 정리된 텍스트
    cleaned_text = '\n'.join(unique_lines)
    
    # 마지막에 시간 표시(예: "4일")가 있으면 제거
    cleaned_text = re.sub(r'\s*\d+[주일시분]\s*$', '', cleaned_text)
    
    return cleaned_text.strip()

# 통합 텍스트 추출 함수
def get_content_text(driver, log_file, post_type):
    """
    게시물 타입에 따라 적절한 텍스트 추출 함수 호출
    """
    if post_type == "reel":
        return get_reels_text(driver, log_file)
    else:
        return get_post_text(driver, log_file)
    
# 모든 이미지 URL 가져오기 (다중 이미지 지원)
# 기존 함수를 다음으로 교체:
def get_all_image_urls(driver, log_file, post_type="post"):
    """
    게시물의 모든 이미지 URL 가져오기 (병렬 처리, 릴스 스킵)
    """
    image_urls = []
    
    # 릴스인 경우 이미지 스크래핑 건너뛰기
    if post_type == "reel":
        log_message(log_file, "릴스 게시물: 이미지 스크래핑 건너뛰기")
        return []
    
    try:
        # 먼저 모든 이미지 URL 수집 (JavaScript로 한 번에)
        all_images = driver.execute_script("""
            const allUrls = new Set();
            
            // 현재 보이는 모든 이미지 수집
            const imgs = document.querySelectorAll('article img');
            imgs.forEach(img => {
                if (img.src && img.src.startsWith('http') && 
                    !img.src.includes('profile_pic') && img.width > 100) {
                    allUrls.add(img.src);
                }
            });
            
            return Array.from(allUrls);
        """)
        
        if all_images:
            image_urls.extend(all_images)
            log_message(log_file, f"초기 스캔으로 {len(all_images)}개 이미지 발견")
        
        # 캐러셀 확인 및 병렬 처리
        carousel_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, '다음') or contains(@aria-label, 'Next')]")
        
        if carousel_buttons:
            log_message(log_file, "캐러셀 감지 - 고속 병렬 스캔 시작")
            
            # 빠른 연속 클릭으로 모든 이미지 로드
            max_clicks = 15  # 최대 15번 클릭
            for i in range(max_clicks):
                try:
                    # 다음 버튼 클릭
                    next_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, '다음') or contains(@aria-label, 'Next')]")
                    if next_button.is_enabled():
                        driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(0.3)  # 매우 짧은 대기
                        
                        # 새 이미지 즉시 수집
                        new_images = driver.execute_script("""
                            const newUrls = [];
                            const imgs = document.querySelectorAll('article img');
                            imgs.forEach(img => {
                                if (img.src && img.src.startsWith('http') && 
                                    !img.src.includes('profile_pic') && 
                                    img.width > 100 && img.offsetParent !== null) {
                                    newUrls.push(img.src);
                                }
                            });
                            return newUrls;
                        """)
                        
                        # 새로운 이미지만 추가
                        added_count = 0
                        for img_url in new_images:
                            if img_url not in image_urls:
                                image_urls.append(img_url)
                                added_count += 1
                        
                        if added_count == 0:
                            # 더 이상 새 이미지가 없으면 종료
                            break
                        else:
                            log_message(log_file, f"클릭 {i+1}: {added_count}개 새 이미지 추가")
                    else:
                        break
                except:
                    break
        
        # 중복 제거
        image_urls = list(dict.fromkeys(image_urls))
        log_message(log_file, f"최종 {len(image_urls)}개 이미지 URL 수집 완료")
        return image_urls
        
    except Exception as e:
        log_message(log_file, f"이미지 URL 추출 중 오류: {str(e)}")
        return []

def download_images(image_urls, post_dir, log_file):
    """
    여러 이미지를 다운로드하여 저장
    """
    downloaded_images = []
    
    if not image_urls:
        return downloaded_images
    
    for i, img_url in enumerate(image_urls, 1):
        try:
            # 파일명 생성 (여러 이미지인 경우 번호 추가)
            if len(image_urls) == 1:
                img_name = "image.jpg"
            else:
                img_name = f"image_{i:02d}.jpg"
            
            img_path = os.path.join(post_dir, img_name)
            
            # 이미지 다운로드
            response = requests.get(img_url, timeout=15)
            response.raise_for_status()
            
            with open(img_path, 'wb') as handler:
                handler.write(response.content)
            
            downloaded_images.append({
                'filename': img_name,
                'path': img_path,
                'url': img_url,
                'index': i
            })
            
            log_message(log_file, f"이미지 {i}/{len(image_urls)} 저장 완료: {img_name}")
            
        except Exception as e:
            log_message(log_file, f"이미지 {i} 다운로드 오류: {str(e)}")
            continue
    
    log_message(log_file, f"총 {len(downloaded_images)}/{len(image_urls)}개 이미지 다운로드 완료")
    return downloaded_images

def scrape_all_posts_sequential(username, max_posts=100, save_dir=None, start_index=0, driver=None):
    """
    단일 드라이버로 게시물을 순차적으로 스크래핑 (릴스 포함)
    """
    # 글로벌 변수 사용
    global instagram_username, instagram_password
    
    # 디렉토리 및 로그 파일 설정
    if save_dir is None:
        save_dir = f"instagram_{username}_all"
    
    os.makedirs(save_dir, exist_ok=True)
    log_file = setup_logging(save_dir)
    
    log_message(log_file, f"'{username}'의 순차적 스크래핑 시작 (일반 게시물 + 릴스)")
    log_message(log_file, f"목표: 최대 {max_posts}개 게시물")
    
    # 이전 진행 상황 불러오기
    processed_ids = set()
    all_posts_summary = []
    current_index = start_index
    
    progress_file = os.path.join(save_dir, "progress.json")
    if os.path.exists(progress_file) and start_index == 0:
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
                processed_ids = set(progress_data.get('processed_ids', []))
                current_index = progress_data.get('last_processed_index', 0) + 1
                
                log_message(log_file, f"이전 진행 상황을 불러왔습니다: {len(processed_ids)}개 게시물 처리됨, 인덱스 {current_index}부터 시작")
        except Exception as e:
            log_message(log_file, f"이전 진행 상황을 불러오는 중 오류 발생: {str(e)}")
    
    # 스크래핑 시작 시간 기록
    scrape_start_time = time.time()
    
    # 외부에서 드라이버를 받지 않았다면 새로 생성
    should_close_driver = False
    if driver is None:
        driver = create_driver()
        should_close_driver = True
        
        # 새로 생성한 드라이버는 로그인 필요
        if instagram_username and instagram_password:
            instagram_login(driver, instagram_username, instagram_password, log_file)
        else:
            log_message(log_file, "경고: 로그인 정보가 설정되지 않았습니다.")
    
    try:
        # 계정 프로필 페이지 방문
        driver.get(f"https://www.instagram.com/{username}/")
        time.sleep(7)
        
        # 계정 정보 수집
        try:
            account_name_elements = driver.find_elements(By.XPATH, "//h2[contains(@class, '_aacl')]")
            account_name = account_name_elements[0].text if account_name_elements else username
            
            follower_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'followers')]/span")
            if follower_elements:
                follower_text = follower_elements[0].text
                try:
                    follower_count = int(follower_text.replace(',', ''))
                except:
                    follower_count = follower_text
                
                log_message(log_file, f"계정 정보: {account_name} (팔로워: {follower_count})")
        except Exception as e:
            log_message(log_file, f"계정 정보 수집 오류: {e}")
        
        # 게시물 링크 수집 (릴스 포함)
        post_links = progressive_scrolling(driver, max_posts, log_file, max_scroll_attempts=500)
        
        if not post_links:
            log_message(log_file, "게시물이 없거나 로드하지 못했습니다.")
            return []
        
        # 상위 N개 게시물만 선택
        post_links = post_links[:max_posts]
        
        # 타입별 통계
        post_count = sum(1 for link in post_links if '/p/' in link)
        reel_count = sum(1 for link in post_links if '/reel/' in link)
        log_message(log_file, f"처리할 게시물 수: 총 {len(post_links)}개 (일반: {post_count}개, 릴스: {reel_count}개)")
        
        # 이미 처리된 게시물 불러오기
        existing_json = os.path.join(save_dir, "all_posts_summary.json")
        if os.path.exists(existing_json):
            try:
                with open(existing_json, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    all_posts_summary = existing_data
                    log_message(log_file, f"기존 데이터를 불러왔습니다: {len(all_posts_summary)}개 게시물")
                    
                    for post in all_posts_summary:
                        processed_ids.add(post.get('post_id'))
            except Exception as e:
                log_message(log_file, f"기존 데이터를 불러오는 중 오류 발생: {str(e)}")
        
        # 현재 인덱스부터 시작하도록 링크 자르기
        if current_index > 0 and current_index < len(post_links):
            remaining_links = post_links[current_index:]
        else:
            remaining_links = post_links
        
        # 순차적으로 게시물 처리
        for i, link in enumerate(remaining_links, start=current_index):
            try:
                # 게시물 ID 및 타입 추출
                post_type = get_post_type(link)
                if post_type == "reel":
                    post_id = link.split('/')[-2] if link.endswith('/') else link.split('/')[-1]
                elif post_type == "post":
                    post_id = link.split('/')[-2]
                else:
                    log_message(log_file, f"알 수 없는 게시물 타입: {link}")
                    continue
                
                # 이미 처리되었는지 확인
                if post_id in processed_ids:
                    log_message(log_file, f"게시물 {i+1}/{len(post_links)}: {post_id} ({post_type}) - 이미 처리됨 (건너뜀)")
                    continue
                
                log_message(log_file, f"게시물 {i+1}/{len(post_links)} 처리 중: {post_id} ({post_type})")
                
                # 게시물 페이지 방문
                driver.get(link)
                time.sleep(3)
                
                # 날짜 정보 추출 및 처리
                date_text = extract_post_date_text(driver)
                post_date = parse_instagram_date(date_text)
                formatted_date = format_date_for_filename(post_date)
                
                # 게시물 디렉토리 생성
                post_dir = os.path.join(save_dir, f"{i+1:03d}_{formatted_date}_{post_type}_{post_id}")
                os.makedirs(post_dir, exist_ok=True)
                
                # 텍스트 및 이미지 수집 (타입에 따라 다른 함수 사용)
                text = get_content_text(driver, log_file, post_type)
                image_urls = get_all_image_urls(driver, log_file, post_type)
                
                # 여러 이미지 다운로드
                downloaded_images = download_images(image_urls, post_dir, log_file)
                
                # 메인 이미지 URL (첫 번째 이미지)
                main_img_url = image_urls[0] if image_urls else ""
                
                # 게시물 정보 저장
                post_data = {
                    'order': i + 1,
                    'post_id': post_id,
                    'post_type': post_type,
                    'account': username,
                    'text': text,
                    'display_date': date_text,
                    'parsed_date': formatted_date,
                    'image_urls': image_urls if post_type != "reel" else [],
                    'image_count': len(image_urls) if post_type != "reel" else 0,
                    'main_image_url': main_img_url if post_type != "reel" else "",
                    'downloaded_images': downloaded_images if post_type != "reel" else [],
                    'link': link,
                    'folder': post_dir
                }
                
                # 정보 저장 (텍스트 파일)
                with open(os.path.join(post_dir, "info.txt"), 'w', encoding='utf-8') as f:
                    f.write(f"순서: {i+1}\n")
                    f.write(f"게시물 ID: {post_id}\n")
                    f.write(f"게시물 타입: {post_type}\n")
                    f.write(f"계정: {username}\n")
                    f.write(f"표시된 날짜: {date_text}\n")
                    f.write(f"파싱된 날짜: {formatted_date}\n")
                    f.write(f"링크: {link}\n")
                    
                    # 릴스와 일반 게시물 구분하여 이미지 정보 저장
                    if post_type != "reel":
                        f.write(f"이미지 개수: {len(image_urls)}개\n")
                        if downloaded_images:
                            f.write(f"\n다운로드된 이미지:\n")
                            for img_info in downloaded_images:
                                f.write(f"  {img_info['index']}. {img_info['filename']}\n")
                    else:
                        f.write(f"릴스 게시물: 이미지 스크래핑 제외\n")
                    
                    f.write(f"\n텍스트 내용:\n{text}\n")
                
                # 정보 저장 (JSON)
                with open(os.path.join(post_dir, "info.json"), 'w', encoding='utf-8') as f:
                    json.dump(post_data, f, ensure_ascii=False, indent=4)
                
                # 요약 정보에 추가
                all_posts_summary.append(post_data)
                processed_ids.add(post_id)
                
                log_message(log_file, f"게시물 {post_id} ({post_type}) 저장 완료 (순서: {i+1}, 날짜: {formatted_date})")
                
                # 텍스트 내용 확인
                if text:
                    log_summary = text[:50] + "..." if len(text) > 50 else text
                    log_message(log_file, f"텍스트 내용 (요약): {log_summary}")
                else:
                    log_message(log_file, "텍스트 내용이 없습니다.")
                
                # 5개마다 저장 (더 자주 저장)
                if (i + 1) % 5 == 0:
                    log_message(log_file, f"진행 중... {i+1}/{len(post_links)} 완료, 중간 저장")
                    
                    # 현재까지의 결과 저장
                    temp_df = pd.DataFrame(all_posts_summary)
                    temp_df.to_csv(os.path.join(save_dir, f"posts_summary_temp_{i+1}.csv"), index=False, encoding='utf-8')
                    
                    # 전체 결과 정기 저장
                    summary_df = pd.DataFrame(all_posts_summary)
                    summary_df.to_csv(os.path.join(save_dir, "all_posts_summary.csv"), index=False, encoding='utf-8')
                    
                    with open(os.path.join(save_dir, "all_posts_summary.json"), 'w', encoding='utf-8') as f:
                        json.dump(all_posts_summary, f, ensure_ascii=False, indent=4)
                    
                    # 진행 상황 저장
                    with open(os.path.join(save_dir, "progress.json"), 'w', encoding='utf-8') as f:
                        json.dump({
                            'last_processed_index': i,
                            'processed_ids': list(processed_ids),
                            'total_processed': len(all_posts_summary),
                            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }, f, ensure_ascii=False, indent=4)
                
                # 게시물 간 랜덤 대기 (인스타그램 제한 방지)
                time.sleep(random.uniform(2.0, 4.0))
                
            except Exception as e:
                log_message(log_file, f"게시물 처리 중 오류 발생: {str(e)}")
                log_message(log_file, traceback.format_exc())
                time.sleep(5)  # 오류 후 더 긴 대기
        
        # 최종 결과 저장
        if all_posts_summary:
            summary_df = pd.DataFrame(all_posts_summary)
            summary_df.to_csv(os.path.join(save_dir, "all_posts_summary.csv"), index=False, encoding='utf-8')
            
            with open(os.path.join(save_dir, "all_posts_summary.json"), 'w', encoding='utf-8') as f:
                json.dump(all_posts_summary, f, ensure_ascii=False, indent=4)
            
            # 총 소요 시간 계산
            total_minutes = (time.time() - scrape_start_time) / 60
            
            # 타입별 통계 계산
            final_post_count = sum(1 for post in all_posts_summary if post.get('post_type') == 'post')
            final_reel_count = sum(1 for post in all_posts_summary if post.get('post_type') == 'reel')
            
            log_message(log_file, f"\n수집 완료! 총 {len(all_posts_summary)}개 게시물이 {save_dir} 폴더에 저장되었습니다.")
            log_message(log_file, f"게시물 타입별 통계: 일반 게시물 {final_post_count}개, 릴스 {final_reel_count}개")
            log_message(log_file, f"총 소요 시간: {total_minutes:.1f}분")
            
            # 수집 완료 표시
            with open(os.path.join(save_dir, "SCRAPING_COMPLETE.txt"), 'w', encoding='utf-8') as f:
                f.write(f"스크래핑 완료 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"대상 계정: {username}\n")
                f.write(f"총 수집 게시물 수: {len(all_posts_summary)}개\n")
                f.write(f"일반 게시물: {final_post_count}개\n")
                f.write(f"릴스: {final_reel_count}개\n")
                f.write(f"총 소요 시간: {total_minutes:.1f}분\n")
            
            # 진행 상황 완료 표시
            with open(os.path.join(save_dir, "progress.json"), 'w', encoding='utf-8') as f:
                json.dump({
                    'status': 'completed',
                    'last_processed_index': len(post_links) - 1,
                    'processed_ids': list(processed_ids),
                    'total_processed': len(all_posts_summary),
                    'post_count': final_post_count,
                    'reel_count': final_reel_count,
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'total_time_minutes': total_minutes
                }, f, ensure_ascii=False, indent=4)
            
            return all_posts_summary
        else:
            log_message(log_file, "수집된 게시물이 없습니다.")
            return []
        
    except Exception as e:
        log_message(log_file, f"스크래핑 중 오류 발생: {str(e)}")
        log_message(log_file, traceback.format_exc())
        return []
    finally:
        # 드라이버 종료 (직접 생성한 경우에만)
        if should_close_driver and driver:
            driver.quit()

# 메인 실행 블록
if __name__ == "__main__":
    # 디버깅을 위한 시작 메시지
    print("스크립트가 시작되었습니다...")
    
    # 로그인 정보 설정
    instagram_username = os.getenv("INSTAGRAM_USERNAME")
    instagram_password = os.getenv("INSTAGRAM_PASSWORD")
    
    # 크롤링하고 싶은 계정 이름
    target_account = "goodibk"  
    
    # 저장 디렉토리 설정
    save_directory = f"instagram_{target_account}_all"
    
    # 이전 진행 상황 확인
    start_index = 0
    progress_file = os.path.join(save_directory, "progress.json")
    
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
                
                # 이미 완료된 경우
                if progress_data.get('status') == 'completed':
                    print("이미 스크래핑이 완료되었습니다. 다시 실행하려면 progress.json 파일을 삭제하거나 이름을 변경하세요.")
                    exit()
                
                # 자동으로 이어서 진행
                last_index = progress_data.get('last_processed_index', -1)
                if last_index >= 0:
                    start_index = last_index + 1
                    print(f"{start_index}번째 게시물부터 이어서 진행합니다.")
        except Exception as e:
            print(f"이전 진행 상황을 확인하는 중 오류 발생: {str(e)}")
    
    try:
        # 로그 파일 설정
        log_file = setup_logging(save_directory)
        
        # 중요 메시지 표시
        log_message(log_file, "======= 인스타그램 게시물 순차적 스크래핑 시작 (릴스 포함) =======")
        log_message(log_file, f"대상 계정: {target_account}")
        log_message(log_file, "모든 보이는 게시물(일반 게시물 + 릴스)을 순서대로 스크래핑합니다.")
        
        # 메인 드라이버 생성 및 로그인
        main_driver = create_driver()
        instagram_login(main_driver, instagram_username, instagram_password, log_file)
        
        # 순차적 스크래핑 수행 (기존 드라이버 전달)
        collected_posts = scrape_all_posts_sequential(
            username=target_account,
            max_posts=1000,
            save_dir=save_directory,
            start_index=start_index,
            driver=main_driver  # 기존 드라이버 재사용
        )
        
        # 최종 통계 출력
        if collected_posts:
            post_count = sum(1 for post in collected_posts if post.get('post_type') == 'post')
            reel_count = sum(1 for post in collected_posts if post.get('post_type') == 'reel')
            log_message(log_file, f"스크래핑 성공적으로 완료. 총 {len(collected_posts)}개 게시물 수집 (일반: {post_count}개, 릴스: {reel_count}개)")
        
    except Exception as e:
        if 'log_file' in locals():
            log_message(log_file, f"프로그램 실행 중 오류 발생: {str(e)}")
            log_message(log_file, traceback.format_exc())
        else:
            print(f"로그 파일 설정 전 오류 발생: {str(e)}")
        
    finally:
        # 브라우저 종료
        try:
            if 'main_driver' in locals() and main_driver:
                main_driver.quit()
            if 'log_file' in locals():
                log_message(log_file, "브라우저 종료 및 프로그램 종료")
            else:
                print("브라우저 종료 및 프로그램 종료")
        except:
            if 'log_file' in locals():
                log_message(log_file, "브라우저 종료 중 오류 발생")
            else:
                print("브라우저 종료 중 오류 발생")
        
        # 스크립트 종료 메시지
        print("스크립트 실행이 완료되었습니다.")