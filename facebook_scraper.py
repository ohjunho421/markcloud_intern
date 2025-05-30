from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import requests
import datetime
import json
import pandas as pd
import random
import re
import traceback
from bs4 import BeautifulSoup
import dateparser
import pickle
import os       
import os.path
import hashlib


def create_driver():
    """최적화된 드라이버 생성"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    chrome_options.add_argument("--max_old_space_size=4096")
    chrome_options.add_argument("--memory-pressure-off")
    
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)


def setup_logging(save_dir):
    """로그 파일 설정"""
    os.makedirs(save_dir, exist_ok=True)
    log_file = os.path.join(save_dir, "scraping_log.txt")
    return log_file


def log_message(log_file, message):
    """로그 메시지 기록"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")


def facebook_login_robust(driver, username, password, log_file, target_page, manual_verification_timeout=600):
    """강화된 페이스북 로그인"""
    log_message(log_file, "페이스북 로그인 시도 중...")
    driver.get("https://www.facebook.com/login")
    time.sleep(5)
    
    try:
        cookie_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Allow') or contains(text(), '수락')]")
        if cookie_buttons:
            cookie_buttons[0].click()
            time.sleep(2)
    except Exception as e:
        log_message(log_file, f"쿠키 수락 버튼 클릭 오류: {e}")
    
    try:
        username_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email']"))
        )
        username_input.clear()
        username_input.send_keys(username)
        
        password_input = driver.find_element(By.CSS_SELECTOR, "input[name='pass']")
        password_input.clear()
        password_input.send_keys(password)
        
        login_button = driver.find_element(By.XPATH, "//button[@name='login']")
        login_button.click()
        time.sleep(10)
        
        current_url = driver.current_url
        
        if ("two_step_verification" in current_url or 
            "checkpoint" in current_url or 
            "authentication" in current_url):
            
            print("\n" + "!"*80)
            print("🔒 2단계 인증 또는 보안 검증이 필요합니다!")
            print("📱 브라우저 창에서 직접 인증을 완료해주세요.")
            print("✅ 인증을 완료한 후 여기에서 Enter 키를 눌러주세요...")
            print("!"*80 + "\n")
            
            input("인증을 완료했으면 Enter 키를 눌러주세요... ")
            
            driver.get("https://www.facebook.com/")
            time.sleep(7)
            
            logged_in = check_login_status(driver, log_file)
            
            if logged_in:
                target_url = f"https://www.facebook.com/{target_page}?locale=ko_KR"
                driver.get(target_url)
                time.sleep(7)
                return True
            else:
                return False
        
        if "facebook.com/home" in driver.current_url or "facebook.com/feed" in driver.current_url:
            target_url = f"https://www.facebook.com/{target_page}?locale=ko_KR"
            driver.get(target_url)
            time.sleep(7)
            return True
        
        driver.get("https://www.facebook.com/")
        time.sleep(7)
        
        if check_login_status(driver, log_file):
            target_url = f"https://www.facebook.com/{target_page}?locale=ko_KR"
            driver.get(target_url)
            time.sleep(7)
            return True
        else:
            return False
            
    except Exception as e:
        log_message(log_file, f"로그인 중 오류 발생: {e}")
        return False


def check_login_status(driver, log_file):
    """로그인 상태 확인"""
    log_message(log_file, "로그인 상태 확인 중...")
    
    current_url = driver.current_url
    log_message(log_file, f"현재 확인 중인 URL: {current_url}")
    
    try:
        if any(url in current_url for url in ["facebook.com/home", "facebook.com/feed", "facebook.com/profile"]):
            return True
        
        login_forms = driver.find_elements(By.CSS_SELECTOR, "form[action*='login']")
        if login_forms:
            return False
        
        profile_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/profile.php') or contains(@aria-label, '프로필')]")
        if profile_elements:
            return True
        
        navigation_elements = driver.find_elements(By.XPATH, "//div[@role='navigation']")
        if navigation_elements:
            return True
            
        logout_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'logout.php')]")
        if logout_elements:
            return True
        
        feed_elements = driver.find_elements(By.XPATH, "//div[@role='feed'] | //div[contains(@aria-label, 'Stories')]")
        if feed_elements:
            return True
    except Exception as e:
        log_message(log_file, f"로그인 상태 확인 중 오류: {e}")
    
    print("\n" + "="*70)
    print("⚠️  로그인 상태를 자동으로 확인할 수 없습니다.")
    print("👉  브라우저에서 페이스북에 로그인되어 있나요? (y/n):")
    user_input = input().strip().lower()
    
    return user_input.startswith('y')


def find_posts_with_enhanced_uniqueness(driver, log_file, processed_signatures):
    """🔥 중복 방지 강화된 게시물 찾기"""
    try:
        posts_data = driver.execute_script("""
            const posts = [];
            const articles = document.querySelectorAll('div[role="article"]');
            const processedSignatures = arguments[0] || [];
            const currentTime = Date.now();
            
            for (const article of articles) {
                try {
                    // IBK 관련 게시물인지 확인
                    const articleText = article.textContent;
                    if (!articleText.includes('IBK기업은행') && 
                        !articleText.includes('IBK') &&
                        !article.querySelector('a[href*="IBK.bank.official"]')) {
                        continue;
                    }
                    
                    const rect = article.getBoundingClientRect();
                    const scrollY = window.scrollY;
                    
                    // 화면에 보이는지 확인
                    if (rect.bottom < 100 || rect.top > window.innerHeight - 100) {
                        continue;
                    }
                    
                    // 🔥 게시물 고유 시그니처 생성 (다중 기준)
                    const absoluteTop = rect.top + scrollY;
                    const textContent = articleText.replace(/\\s+/g, ' ').trim();
                    const textHash = textContent.substring(0, 100).replace(/[^a-zA-Z0-9가-힣]/g, '');
                    
                    // 링크 추출
                    let postLink = '';
                    const links = article.querySelectorAll('a[href*="IBK.bank.official"]');
                    for (const link of links) {
                        const href = link.href;
                        if (href.includes('/posts/') || href.includes('/photos/') || 
                            href.includes('/videos/') || href.includes('/reel/')) {
                            postLink = href.split('?')[0];
                            break;
                        }
                    }
                    
                    // 🔥 다중 시그니처 생성
                    const signatures = {
                        link: postLink,
                        textHash: textHash,
                        position: Math.floor(absoluteTop / 100) * 100, // 100px 단위로 반올림
                        size: Math.floor(rect.height / 50) * 50,        // 50px 단위로 반올림
                        combined: `${textHash}_${Math.floor(absoluteTop / 100)}_${Math.floor(rect.height / 50)}`
                    };
                    
                    // 🔥 중복 확인 (어떤 시그니처라도 겹치면 중복)
                    let isDuplicate = false;
                    for (const processed of processedSignatures) {
                        if ((signatures.link && signatures.link === processed.link) ||
                            (signatures.textHash && signatures.textHash === processed.textHash) ||
                            (signatures.combined === processed.combined) ||
                            (Math.abs(signatures.position - processed.position) < 200 && 
                             Math.abs(signatures.size - processed.size) < 100)) {
                            isDuplicate = true;
                            break;
                        }
                    }
                    
                    if (isDuplicate) {
                        continue;
                    }
                    
                    // 게시물 유형 판단
                    let isReels = false;
                    let hasVideo = false;
                    let postType = 'normal';
                    
                    if (articleText.includes('릴스') || 
                        articleText.includes('Reels') || 
                        article.querySelector('a[href*="/reel/"]')) {
                        isReels = true;
                        postType = 'reels';
                    } else if (articleText.includes('동영상') || 
                               article.querySelector('video')) {
                        hasVideo = true;
                        postType = 'video';
                    }
                    
                    // 날짜 추출
                    let dateText = '';
                    const timeSpans = article.querySelectorAll('span');
                    for (const span of timeSpans) {
                        const text = span.textContent.trim();
                        if (text.match(/\\d+[시간분일주월년]/)) {
                            dateText = text;
                            break;
                        }
                    }
                    
                    posts.push({
                        element: article,
                        signatures: signatures,
                        top: absoluteTop,
                        height: rect.height,
                        width: rect.width,
                        text: textContent,
                        date: dateText || '날짜 정보 없음',
                        isReels: isReels,
                        hasVideo: hasVideo,
                        postType: postType,
                        originalLink: postLink,
                        timestamp: currentTime
                    });
                    
                } catch (e) {
                    console.log('게시물 처리 오류:', e);
                }
            }
            
            // 위치 순으로 정렬
            posts.sort((a, b) => a.top - b.top);
            
            return posts;
        """, list(processed_signatures))
        
        log_message(log_file, f"🔍 중복 방지 강화로 {len(posts_data)}개 고유 게시물 발견")
        return posts_data
        
    except Exception as e:
        log_message(log_file, f"❌ 게시물 찾기 오류: {str(e)}")
        return []


def wait_for_new_content_load(driver, log_file, max_wait_time=15):
    """🔥 새 콘텐츠 로딩 대기 (개선된 버전)"""
    log_message(log_file, "새 콘텐츠 로딩 대기 중...")
    
    start_time = time.time()
    initial_height = driver.execute_script("return document.body.scrollHeight")
    
    while time.time() - start_time < max_wait_time:
        # 여러 방법으로 스크롤 시도
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(1)
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        # Space 키 누르기
        try:
            body = driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.SPACE)
            time.sleep(1)
        except:
            pass
        
        # 현재 높이 확인
        current_height = driver.execute_script("return document.body.scrollHeight")
        if current_height > initial_height:
            log_message(log_file, f"새 콘텐츠 로딩됨: {initial_height} -> {current_height}")
            return True
        
        # 로딩 인디케이터 확인
        loading_indicators = driver.find_elements(By.XPATH, 
            "//div[contains(@aria-label, 'Loading') or contains(@class, 'loading') or contains(text(), '로딩')]")
        if loading_indicators:
            log_message(log_file, "로딩 인디케이터 감지됨, 계속 대기...")
            time.sleep(2)
        else:
            time.sleep(1)
    
    log_message(log_file, f"새 콘텐츠 로딩 대기 완료 ({time.time() - start_time:.1f}초)")
    return False


def enhanced_scroll_for_new_content(driver, log_file, current_position=0):
    """🔥 새 콘텐츠를 위한 향상된 스크롤링"""
    log_message(log_file, f"새 콘텐츠 스크롤링 시작 (현재 위치: {current_position}px)")
    
    # 현재 위치에서 시작
    if current_position > 0:
        driver.execute_script(f"window.scrollTo(0, {current_position});")
        time.sleep(2)
    
    # 다양한 스크롤 패턴 시도
    scroll_patterns = [
        lambda: driver.execute_script("window.scrollBy(0, 800);"),
        lambda: driver.execute_script("window.scrollBy(0, 1200);"),
        lambda: driver.execute_script("window.scrollTo(0, document.body.scrollHeight);"),
        lambda: driver.execute_script("window.scrollBy(0, -200); setTimeout(() => window.scrollBy(0, 400), 100);"),
    ]
    
    for i, scroll_pattern in enumerate(scroll_patterns):
        try:
            log_message(log_file, f"스크롤 패턴 {i+1} 시도")
            scroll_pattern()
            time.sleep(3)
            
            # Space 키로 추가 스크롤
            try:
                body = driver.find_element(By.TAG_NAME, 'body')
                for _ in range(3):
                    body.send_keys(Keys.SPACE)
                    time.sleep(0.5)
            except:
                pass
            
            # 새 게시물이 로딩되었는지 확인
            new_posts = find_posts_with_enhanced_uniqueness(driver, log_file, [])
            if len(new_posts) > 0:
                log_message(log_file, f"스크롤 패턴 {i+1}로 새 게시물 {len(new_posts)}개 발견")
                break
                
        except Exception as e:
            log_message(log_file, f"스크롤 패턴 {i+1} 오류: {str(e)}")
            continue
    
    return driver.execute_script("return window.scrollY")


def extract_reels_text_no_fullscreen(driver, post_element, log_file):
    """🔥 릴스 텍스트 추출 (전체화면 진입 완전 방지)"""
    try:
        log_message(log_file, "릴스 안전 텍스트 추출 시작 (전체화면 방지 모드)")
        
        # 현재 URL 저장
        original_url = driver.current_url
        
        # 🔥 1단계: 스크롤 상태에서 기본 텍스트 추출 (댓글 제외)
        base_text = driver.execute_script("""
            const postElement = arguments[0];
            
            // 릴스 게시물 본문 영역 찾기 (댓글 영역 제외)
            let bestText = '';
            let bestScore = 0;
            
            // 댓글 영역 식별을 위한 키워드
            const commentKeywords = ['댓글', '답글', 'Reply', 'Comment', '좋아요', 'Like', '시간 전', '분 전', '일 전'];
            
            // 게시물 상단 70% 영역에서만 텍스트 찾기 (댓글은 보통 하단에 위치)
            const postRect = postElement.getBoundingClientRect();
            const contentArea = postRect.height * 0.7; // 상단 70% 영역
            
            // 텍스트 요소들 찾기
            const textElements = postElement.querySelectorAll('div, span, p');
            
            for (const element of textElements) {
                const text = element.textContent.trim();
                const elementRect = element.getBoundingClientRect();
                const relativeTop = elementRect.top - postRect.top;
                
                // 상단 70% 영역에 있는 텍스트만 고려 (댓글 영역 제외)
                if (relativeTop > contentArea) {
                    continue;
                }
                
                // 댓글이나 UI 요소인지 확인
                let isComment = false;
                for (const keyword of commentKeywords) {
                    if (text.includes(keyword)) {
                        isComment = true;
                        break;
                    }
                }
                
                // 부모 요소들도 댓글 영역인지 확인
                if (!isComment) {
                    let parent = element.parentElement;
                    for (let i = 0; i < 3 && parent; i++) {
                        const parentText = parent.textContent;
                        for (const keyword of commentKeywords) {
                            if (parentText.includes(keyword) && parentText.length < text.length * 3) {
                                isComment = true;
                                break;
                            }
                        }
                        if (isComment) break;
                        parent = parent.parentElement;
                    }
                }
                
                // 게시물 본문으로 판단되는 텍스트인지 확인
                if (!isComment && text.length > 15 && 
                    !text.match(/^\\d+[시간분일주]$/) &&
                    !text.includes('공유') &&
                    !text.includes('Share') &&
                    !text.includes('View') &&
                    !text.includes('Play')) {
                    
                    // 텍스트 점수 계산 (게시물 본문일 가능성)
                    let score = text.length;
                    if (text.includes('#')) score += 30; // 해시태그 가점 (릴스에 흔함)
                    if (text.includes('IBK')) score += 20; // IBK 키워드 가점
                    if (/[가-힣]/.test(text)) score += 10; // 한글 가점
                    if (text.length > 50) score += 15; // 긴 텍스트 가점
                    if (relativeTop < contentArea * 0.5) score += 10; // 상단에 위치한 텍스트 가점
                    
                    // 댓글처럼 보이는 패턴 감점
                    if (text.includes('님이') || text.includes('wrote:') || text.includes('replied:')) {
                        score -= 20;
                    }
                    
                    if (score > bestScore) {
                        bestText = text;
                        bestScore = score;
                    }
                }
            }
            
            return bestText;
        """, post_element)
        
        # 🔥 2단계: 강화된 더보기 클릭 시도 (확실한 클릭)
        more_clicked = driver.execute_script("""
            const postElement = arguments[0];
            const originalURL = arguments[1];
            
            console.log('릴스 더보기 버튼 강화된 클릭 시도');
            
            // 더보기 버튼 패턴들 (다양한 형태)
            const morePatterns = [
                '더 보기', 'See more', '...더 보기', 'more', 'More',
                '자세히 보기', '전체 보기', '계속 읽기', '…더 보기', '... 더 보기'
            ];
            
            const postRect = postElement.getBoundingClientRect();
            const elements = Array.from(postElement.querySelectorAll('*'));
            const moreButtonCandidates = [];
            
            // 더보기 버튼 후보들 수집
            for (const element of elements) {
                const text = element.textContent.trim();
                
                // 더보기 패턴 매칭 (정확한 매칭 + 부분 매칭)
                const isMoreButton = morePatterns.some(pattern => 
                    text === pattern || 
                    text.includes(pattern) || 
                    (text.length <= 15 && (text.includes('더') || text.toLowerCase().includes('more')))
                );
                
                if (isMoreButton) {
                    const rect = element.getBoundingClientRect();
                    const elementCenter = rect.top + rect.height / 2;
                    const relativeTop = elementCenter - postRect.top;
                    
                    // 게시물 하단 50% 영역에 있는 더보기만 고려
                    if (relativeTop > postRect.height * 0.5 && rect.width > 0 && rect.height > 0) {
                        
                        // 🔥 매우 중요: 비디오, 이미지, 링크 영역이 아닌지 확인
                        const isVideoOrImage = element.closest('video') || 
                                             element.closest('img') || 
                                             element.closest('a[href*="/reel/"]') ||
                                             element.tagName.toLowerCase() === 'video' ||
                                             element.tagName.toLowerCase() === 'img';
                        
                        if (!isVideoOrImage) {
                            // 클릭 가능성 점수 계산
                            let clickScore = 0;
                            
                            // 정확한 "더 보기" 텍스트면 높은 점수
                            if (text === '더 보기' || text === 'See more') clickScore += 50;
                            else if (text.includes('더 보기') || text.includes('See more')) clickScore += 30;
                            else if (text.includes('더') || text.toLowerCase().includes('more')) clickScore += 10;
                            
                            // 하단에 가까울수록 높은 점수
                            const distanceFromBottom = postRect.bottom - rect.bottom;
                            clickScore += Math.max(0, 20 - distanceFromBottom / 10);
                            
                            // 클릭 가능한 요소인지 확인
                            const style = window.getComputedStyle(element);
                            if (style.cursor === 'pointer' || 
                                element.tagName.toLowerCase() === 'button' ||
                                element.getAttribute('role') === 'button') {
                                clickScore += 15;
                            }
                            
                            moreButtonCandidates.push({
                                element: element,
                                text: text,
                                score: clickScore,
                                rect: rect,
                                relativeTop: relativeTop
                            });
                        }
                    }
                }
            }
            
            // 점수 순으로 정렬
            moreButtonCandidates.sort((a, b) => b.score - a.score);
            
            console.log('릴스 더보기 후보:', moreButtonCandidates.length + '개');
            
            // 🔥 여러 시도로 확실한 클릭
            for (let i = 0; i < Math.min(3, moreButtonCandidates.length); i++) {
                const candidate = moreButtonCandidates[i];
                
                try {
                    console.log('더보기 클릭 시도:', {
                        index: i,
                        text: candidate.text,
                        score: candidate.score
                    });
                    
                    // 요소가 여전히 보이는지 확인
                    const currentStyle = window.getComputedStyle(candidate.element);
                    if (currentStyle.display === 'none' || currentStyle.visibility === 'hidden') {
                        continue;
                    }
                    
                    // 스크롤해서 중앙에 위치시키기
                    candidate.element.scrollIntoView({behavior: 'auto', block: 'center'});
                    
                    // 잠시 대기
                    const start = Date.now();
                    while (Date.now() - start < 500) {}
                    
                    // 🔥 다중 클릭 방법 시도
                    let clickSuccess = false;
                    
                    // 방법 1: 이벤트 디스패치 (전파 방지)
                    try {
                        const clickEvent = new MouseEvent('click', {
                            view: window,
                            bubbles: false,
                            cancelable: true,
                            detail: 1
                        });
                        candidate.element.dispatchEvent(clickEvent);
                        clickSuccess = true;
                        console.log('이벤트 디스패치 클릭 성공');
                    } catch (e) {
                        console.log('이벤트 디스패치 실패:', e);
                    }
                    
                    // 방법 2: 직접 클릭
                    if (!clickSuccess) {
                        try {
                            candidate.element.click();
                            clickSuccess = true;
                            console.log('직접 클릭 성공');
                        } catch (e) {
                            console.log('직접 클릭 실패:', e);
                        }
                    }
                    
                    // 방법 3: 부모 요소 클릭
                    if (!clickSuccess && candidate.element.parentElement) {
                        try {
                            candidate.element.parentElement.click();
                            clickSuccess = true;
                            console.log('부모 요소 클릭 성공');
                        } catch (e) {
                            console.log('부모 요소 클릭 실패:', e);
                        }
                    }
                    
                    if (clickSuccess) {
                        // 🔥 클릭 후 즉시 전체화면 진입 감지
                        setTimeout(() => {
                            if (window.location.href !== originalURL || 
                                window.location.href.includes('/reel/')) {
                                console.log('경고: 전체화면 진입 감지!');
                                window.history.back();
                            }
                        }, 100);
                        
                        console.log('릴스 더보기 클릭 성공 (순위:', i + ')');
                        return true;
                    }
                    
                } catch (e) {
                    console.log('더보기 클릭 시도 실패 (순위', i + '):', e);
                    continue;
                }
            }
            
            console.log('모든 더보기 클릭 시도 실패');
            return false;
        """, post_element, original_url)
        
        # 🔥 3단계: 더보기 클릭 후 확장된 텍스트 추출 (댓글 제외)
        if more_clicked:
            log_message(log_file, "릴스 더보기 클릭 성공, 확장된 텍스트 추출 중...")
            time.sleep(3)  # 텍스트 확장 대기
            
            # URL 변경 확인 (전체화면 진입 감지)
            current_url = driver.current_url
            if current_url != original_url or '/reel/' in current_url:
                log_message(log_file, "🚨 전체화면 진입 감지! 즉시 복구")
                driver.back()
                time.sleep(2)
                return base_text if base_text else "릴스 전체화면 진입으로 인한 기본 텍스트"
            
            # 확장된 텍스트 추출 (댓글 영역 완전 제외)
            expanded_text = driver.execute_script("""
                const postElement = arguments[0];
                
                console.log('릴스 확장된 텍스트 추출 시작 (댓글 제외)');
                
                // 댓글 영역을 더 정확히 식별
                const commentIndicators = [
                    '댓글', '답글', 'Reply', 'Comment', 'Comments', 
                    '좋아요', 'Like', 'Liked', '시간 전', '분 전', '일 전',
                    '님이', 'wrote:', 'replied:', 'commented:', 
                    'View all', '모든 댓글', '댓글 보기', '더 보기', 'Show more'
                ];
                
                const postRect = postElement.getBoundingClientRect();
                const contentBoundary = postRect.height * 0.65; // 상위 65% 영역만 고려
                
                let bestText = '';
                let bestScore = 0;
                
                // 모든 텍스트 요소 검사
                const allTextElements = postElement.querySelectorAll('div, span, p, h1, h2, h3, h4, h5, h6');
                
                for (const element of allTextElements) {
                    const text = element.textContent.trim();
                    const elementRect = element.getBoundingClientRect();
                    const relativeTop = elementRect.top - postRect.top;
                    
                    // 상위 65% 영역에 있는 텍스트만 고려
                    if (relativeTop > contentBoundary) {
                        continue;
                    }
                    
                    // 댓글 영역인지 확인 (더 엄격한 기준)
                    let isCommentArea = false;
                    
                    // 1. 텍스트 자체에 댓글 지시어가 있는지 확인
                    for (const indicator of commentIndicators) {
                        if (text.includes(indicator)) {
                            // "더 보기"는 예외 (게시물 본문의 더보기일 수 있음)
                            if (indicator === '더 보기' || indicator === 'Show more') {
                                // 주변 텍스트가 댓글 관련이면 댓글 영역으로 판단
                                const surroundingText = element.parentElement?.textContent || '';
                                if (surroundingText.includes('댓글') || surroundingText.includes('Comment')) {
                                    isCommentArea = true;
                                    break;
                                }
                            } else {
                                isCommentArea = true;
                                break;
                            }
                        }
                    }
                    
                    // 2. 부모 요소들 확인 (댓글 컨테이너인지)
                    if (!isCommentArea) {
                        let parent = element.parentElement;
                        for (let i = 0; i < 4 && parent; i++) {
                            const parentText = parent.textContent;
                            
                            // 부모의 텍스트가 현재 텍스트보다 2배 이상 크면서 댓글 지시어가 있으면 댓글 영역
                            if (parentText.length > text.length * 2) {
                                for (const indicator of commentIndicators) {
                                    if (parentText.includes(indicator)) {
                                        isCommentArea = true;
                                        break;
                                    }
                                }
                                if (isCommentArea) break;
                            }
                            
                            parent = parent.parentElement;
                        }
                    }
                    
                    // 3. 댓글 스타일 패턴 확인
                    if (!isCommentArea) {
                        // 짧은 텍스트에 사용자명 패턴이 있으면 댓글
                        if (text.length < 100 && (
                            text.includes('님이') || 
                            text.match(/^[가-힣A-Za-z\\s]+\\s+(wrote|said|replied)/) ||
                            text.match(/^@[A-Za-z0-9_]+/)
                        )) {
                            isCommentArea = true;
                        }
                    }
                    
                    // 댓글이 아닌 게시물 본문으로 판단되는 텍스트
                    if (!isCommentArea && text.length > 10) {
                        
                        // 게시물 본문 점수 계산
                        let contentScore = 0;
                        
                        // 기본 길이 점수
                        contentScore += text.length;
                        
                        // 해시태그가 있으면 높은 점수 (릴스 특성)
                        if (text.includes('#')) {
                            const hashtagCount = (text.match(/#/g) || []).length;
                            contentScore += hashtagCount * 25;
                        }
                        
                        // IBK 관련 키워드
                        if (text.includes('IBK') || text.includes('기업은행')) {
                            contentScore += 30;
                        }
                        
                        // 한글 컨텐츠 가점
                        if (/[가-힣]/.test(text)) {
                            contentScore += 15;
                        }
                        
                        // 상단에 위치할수록 높은 점수
                        if (relativeTop < contentBoundary * 0.3) {
                            contentScore += 20;
                        }
                        
                        // 긴 텍스트 가점
                        if (text.length > 100) {
                            contentScore += 25;
                        }
                        
                        // 줄바꿈이 있으면 구조화된 텍스트로 가점
                        if (text.includes('\\n') || text.split(' ').length > 10) {
                            contentScore += 15;
                        }
                        
                        // 댓글 같은 패턴이면 감점
                        if (text.includes('님이') || text.includes('wrote:') || 
                            text.includes('replied:') || text.length < 30) {
                            contentScore -= 20;
                        }
                        
                        console.log('텍스트 후보:', {
                            preview: text.substring(0, 50) + '...',
                            length: text.length,
                            score: contentScore,
                            relativeTop: relativeTop
                        });
                        
                        if (contentScore > bestScore) {
                            bestText = text;
                            bestScore = contentScore;
                        }
                    }
                }
                
                console.log('최종 선택된 텍스트:', {
                    preview: bestText.substring(0, 100) + '...',
                    length: bestText.length,
                    score: bestScore
                });
                
                return bestText;
            """, post_element)
            
            if expanded_text and len(expanded_text) > len(base_text):
                log_message(log_file, f"릴스 확장 텍스트 추출 성공: {len(expanded_text)}자")
                return clean_reels_text(expanded_text)
        
        # 기본 텍스트 반환
        if base_text and len(base_text) > 5:
            log_message(log_file, f"릴스 기본 텍스트 추출: {len(base_text)}자")
            return clean_reels_text(base_text)
        
        return "릴스 텍스트 추출 실패"
        
    except Exception as e:
        log_message(log_file, f"릴스 안전 텍스트 추출 오류: {str(e)}")
        
        # 오류 발생 시에도 전체화면 확인
        try:
            current_url = driver.current_url
            if '/reel/' in current_url:
                driver.back()
                time.sleep(2)
        except:
            pass
        
        return "릴스 텍스트 추출 오류"


def clean_reels_text(text):
    """릴스 텍스트 정리 (댓글 제거 강화)"""
    if not text:
        return ""
    
    import re
    
    # 릴스 특화 정리 패턴
    removal_patterns = [
        # 기본 UI 요소
        "좋아요", "댓글", "공유하기", "댓글 달기",
        "Like", "Comment", "Share", 
        "더 보기", "See more", "...더 보기",
        "번역 보기", "See translation",
        "IBK기업은행", "IBK 기업은행",
        
        # 릴스 특화 UI
        "릴스", "Reels", "Play", "Watch", "View",
        "팔로우", "Follow", "Following",
        
        # 댓글 관련
        "님이", "wrote:", "replied:", "commented:",
        "답글", "Reply", "Replies"
    ]
    
    cleaned_text = text
    for pattern in removal_patterns:
        cleaned_text = cleaned_text.replace(pattern, "")
    
    # 시간 표시 제거 (릴스에서 흔함)
    time_patterns = [
        r'\d+시간( 전)?', r'\d+분( 전)?', r'\d+일( 전)?',
        r'\d+주( 전)?', r'\d+개월( 전)?', r'\d+년( 전)?',
        r'\d+h', r'\d+m', r'\d+d', r'\d+w'  # 축약형
    ]
    
    for pattern in time_patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text)
    
    # 멘션 및 댓글 패턴 제거
    cleaned_text = re.sub(r'@[A-Za-z0-9_]+', '', cleaned_text)
    cleaned_text = re.sub(r'^[가-힣A-Za-z\s]+님이.*', '', cleaned_text, flags=re.MULTILINE)
    
    # 공백 정리
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    
    # 해시태그 앞에서 줄바꿈 (릴스 특성)
    cleaned_text = re.sub(r'(#\w+)', r'\n\1', cleaned_text)
    
    # 연속된 줄바꿈 정리
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
    
    result = cleaned_text.strip()
    
    # 너무 짧은 결과 체크
    if len(result) < 5:
        return "릴스 텍스트 추출 실패"
    
    return result


def extract_complete_text_with_more_button_enhanced(driver, post_element, is_reels, log_file):
    """🔥 강화된 텍스트 추출 - 모든 게시물 구조에 대응"""
    try:
        if is_reels:
            return extract_reels_text_no_fullscreen(driver, post_element, log_file)
        
        log_message(log_file, "강화된 일반 게시물 텍스트 추출 시작")
        
        # 🔥 1단계: 다중 방식 더보기 버튼 클릭 시도
        more_clicked = attempt_multiple_more_button_clicks(driver, post_element, log_file)
        
        if more_clicked:
            log_message(log_file, "더보기 클릭 성공, 텍스트 확장 대기 중...")
            time.sleep(4)  # 충분한 대기 시간
        
        # 🔥 2단계: 다중 전략 텍스트 추출
        extracted_text = extract_text_multiple_strategies(driver, post_element, log_file)
        
        # 🔥 3단계: 텍스트 품질 검증 및 재시도
        if len(extracted_text.strip()) < 50:
            log_message(log_file, "추출된 텍스트가 짧음, 재시도...")
            
            # 추가 더보기 클릭 시도
            additional_more_clicked = attempt_additional_more_clicks(driver, post_element, log_file)
            if additional_more_clicked:
                time.sleep(3)
                extracted_text = extract_text_multiple_strategies(driver, post_element, log_file)
        
        if extracted_text and len(extracted_text.strip()) > 5:
            log_message(log_file, f"강화된 텍스트 추출 성공: {len(extracted_text)}자")
            return clean_facebook_text_enhanced(extracted_text)
        else:
            # 최후의 수단: 기본 텍스트
            basic_text = post_element.text if post_element else ""
            log_message(log_file, f"기본 텍스트 반환: {len(basic_text)}자")
            return clean_facebook_text_enhanced(basic_text)
            
    except Exception as e:
        log_message(log_file, f"강화된 텍스트 추출 중 오류: {str(e)}")
        return post_element.text if post_element else ""

def attempt_multiple_more_button_clicks(driver, post_element, log_file):
    """🔥 다중 방식 더보기 버튼 클릭 시도"""
    try:
        clicked = driver.execute_script("""
            const postElement = arguments[0];
            
            console.log('🔥 강화된 다중 방식 더보기 클릭 시도');
            
            // 🔥 방법 1: 정확한 텍스트 매칭
            const exactTexts = ['더 보기', 'See more', '...더 보기', '… 더 보기', 'Show more'];
            
            for (const text of exactTexts) {
                const elements = Array.from(postElement.querySelectorAll('*')).filter(el => 
                    el.textContent.trim() === text
                );
                
                for (const element of elements) {
                    if (isValidMoreButton(element, postElement)) {
                        if (attemptClick(element, '정확한 텍스트: ' + text)) {
                            return true;
                        }
                    }
                }
            }
            
            // 🔥 방법 2: 부분 텍스트 매칭 (더 관대한 조건)
            const partialTexts = ['더 보기', 'more', 'More', '더보기'];
            
            for (const text of partialTexts) {
                const elements = Array.from(postElement.querySelectorAll('*')).filter(el => {
                    const elText = el.textContent.trim();
                    return elText.includes(text) && elText.length <= text.length + 10;
                });
                
                for (const element of elements) {
                    if (isValidMoreButton(element, postElement)) {
                        if (attemptClick(element, '부분 텍스트: ' + text)) {
                            return true;
                        }
                    }
                }
            }
            
            // 🔥 방법 3: CSS 선택자 기반 (페이스북 일반적인 클래스들)
            const cssSelectors = [
                'div[role="button"][tabindex="0"]',
                'span[role="button"]',
                'div[tabindex="0"]',
                '[data-testid*="more"]',
                '[aria-label*="more"]',
                '[aria-label*="더"]'
            ];
            
            for (const selector of cssSelectors) {
                try {
                    const elements = postElement.querySelectorAll(selector);
                    for (const element of elements) {
                        const text = element.textContent.trim();
                        if ((text.includes('더') || text.toLowerCase().includes('more')) && 
                            text.length < 20 && isValidMoreButton(element, postElement)) {
                            if (attemptClick(element, 'CSS 선택자: ' + selector)) {
                                return true;
                            }
                        }
                    }
                } catch (e) {
                    console.log('CSS 선택자 오류:', e);
                }
            }
            
            // 🔥 방법 4: 위치 기반 (게시물 중간~하단 영역의 클릭 가능한 요소들)
            const postRect = postElement.getBoundingClientRect();
            const middleArea = postRect.height * 0.3; // 30% 이후부터
            const bottomArea = postRect.height * 0.8;  // 80% 이전까지
            
            const clickableElements = postElement.querySelectorAll('[role="button"], button, [tabindex="0"]');
            for (const element of clickableElements) {
                const rect = element.getBoundingClientRect();
                const relativeTop = rect.top - postRect.top;
                
                if (relativeTop >= middleArea && relativeTop <= bottomArea) {
                    const text = element.textContent.trim();
                    if (text.length > 0 && text.length < 30 && 
                        (text.includes('더') || text.toLowerCase().includes('more') || 
                         text.includes('보기') || text.includes('show'))) {
                        if (attemptClick(element, '위치 기반: ' + text)) {
                            return true;
                        }
                    }
                }
            }
            
            // 🔥 유효한 더보기 버튼인지 확인하는 함수
            function isValidMoreButton(element, postElement) {
                // 댓글 영역이 아닌지 확인
                const commentKeywords = ['댓글', '답글', 'comment', 'reply', '좋아요', 'like'];
                let parent = element.parentElement;
                
                for (let i = 0; i < 4 && parent; i++) {
                    const parentText = parent.textContent.toLowerCase();
                    for (const keyword of commentKeywords) {
                        if (parentText.includes(keyword) && parentText.length < 300) {
                            return false;
                        }
                    }
                    parent = parent.parentElement;
                }
                
                // 요소가 보이는지 확인
                const rect = element.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0;
            }
            
            // 🔥 클릭 시도 함수
            function attemptClick(element, method) {
                try {
                    console.log('클릭 시도:', method);
                    
                    // 스크롤해서 보이게 하기
                    element.scrollIntoView({behavior: 'auto', block: 'center'});
                    
                    // 잠시 대기
                    const start = Date.now();
                    while (Date.now() - start < 200) {}
                    
                    // 🔥 다양한 클릭 방법 시도
                    
                    // 방법 1: 직접 클릭
                    try {
                        element.click();
                        console.log('직접 클릭 성공:', method);
                        return true;
                    } catch (e) {
                        console.log('직접 클릭 실패:', e);
                    }
                    
                    // 방법 2: 마우스 이벤트
                    try {
                        const mouseEvent = new MouseEvent('click', {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            detail: 1
                        });
                        element.dispatchEvent(mouseEvent);
                        console.log('마우스 이벤트 성공:', method);
                        return true;
                    } catch (e) {
                        console.log('마우스 이벤트 실패:', e);
                    }
                    
                    // 방법 3: 포커스 후 엔터
                    try {
                        element.focus();
                        const enterEvent = new KeyboardEvent('keydown', {
                            key: 'Enter',
                            code: 'Enter',
                            keyCode: 13,
                            bubbles: true
                        });
                        element.dispatchEvent(enterEvent);
                        console.log('엔터 키 성공:', method);
                        return true;
                    } catch (e) {
                        console.log('엔터 키 실패:', e);
                    }
                    
                    // 방법 4: 부모 요소 클릭
                    if (element.parentElement) {
                        try {
                            element.parentElement.click();
                            console.log('부모 요소 클릭 성공:', method);
                            return true;
                        } catch (e) {
                            console.log('부모 요소 클릭 실패:', e);
                        }
                    }
                    
                    return false;
                } catch (e) {
                    console.log('클릭 시도 전체 실패:', method, e);
                    return false;
                }
            }
            
            console.log('모든 더보기 클릭 방법 실패');
            return false;
        """, post_element)
        
        if clicked:
            log_message(log_file, "다중 방식 더보기 클릭 성공")
            return True
        else:
            log_message(log_file, "모든 더보기 클릭 방법 실패")
            return False
            
    except Exception as e:
        log_message(log_file, f"다중 방식 더보기 클릭 오류: {str(e)}")
        return False


def attempt_additional_more_clicks(driver, post_element, log_file):
    """🔥 추가 더보기 클릭 시도 (짧은 텍스트일 때)"""
    try:
        log_message(log_file, "추가 더보기 버튼 검색 중...")
        
        clicked = driver.execute_script("""
            const postElement = arguments[0];
            
            console.log('🔥 추가 더보기 버튼 검색');
            
            // 🔥 새로 나타난 더보기 버튼들 찾기
            const moreTexts = ['더 보기', 'See more', 'Show more', '...더 보기', '…'];
            
            // 모든 가능한 요소 검색
            const allElements = Array.from(postElement.querySelectorAll('*'));
            
            for (const element of allElements) {
                const text = element.textContent.trim();
                
                // 더보기 패턴 체크
                const isMoreButton = moreTexts.some(pattern => text === pattern) ||
                                   (text.includes('더') && text.length < 10) ||
                                   (text.toLowerCase().includes('more') && text.length < 15);
                
                if (isMoreButton) {
                    const rect = element.getBoundingClientRect();
                    
                    // 요소가 보이고 클릭 가능한지 확인
                    if (rect.width > 0 && rect.height > 0) {
                        // 댓글 영역이 아닌지 확인
                        let isCommentArea = false;
                        let parent = element.parentElement;
                        
                        for (let i = 0; i < 3 && parent; i++) {
                            const parentText = parent.textContent.toLowerCase();
                            if (parentText.includes('댓글') || parentText.includes('comment') ||
                                parentText.includes('좋아요') || parentText.includes('like')) {
                                isCommentArea = true;
                                break;
                            }
                            parent = parent.parentElement;
                        }
                        
                        if (!isCommentArea) {
                            try {
                                console.log('추가 더보기 클릭 시도:', text);
                                element.scrollIntoView({block: 'center'});
                                
                                // 대기
                                const start = Date.now();
                                while (Date.now() - start < 300) {}
                                
                                element.click();
                                console.log('추가 더보기 클릭 성공');
                                return true;
                            } catch (e) {
                                console.log('추가 더보기 클릭 실패:', e);
                            }
                        }
                    }
                }
            }
            
            return false;
        """, post_element)
        
        return clicked
        
    except Exception as e:
        log_message(log_file, f"추가 더보기 클릭 오류: {str(e)}")
        return False


def extract_text_multiple_strategies(driver, post_element, log_file):
    """🔥 다중 전략 텍스트 추출"""
    try:
        log_message(log_file, "다중 전략 텍스트 추출 시작")
        
        extracted_text = driver.execute_script("""
            const postElement = arguments[0];
            
            console.log('🔥 다중 전략 텍스트 추출');
            
            const commentIndicators = [
                '댓글', '답글', 'Reply', 'Comment', 'Comments', 
                '좋아요', 'Like', 'Liked', '시간 전', '분 전', '일 전',
                '님이', 'wrote:', 'replied:', 'commented:', 
                'View all', '모든 댓글', '댓글 보기',
                '공유', 'Share', 'Shared'
            ];
            
            const postRect = postElement.getBoundingClientRect();
            const contentBoundary = postRect.height * 0.7; // 상위 70% 영역
            
            let bestText = '';
            let bestScore = 0;
            const candidateTexts = [];
            
            // 🔥 전략 1: Facebook 표준 선택자들
            const standardSelectors = [
                '[data-ad-preview="message"]',
                '[data-testid="post_message"]',
                '[data-ad-comet-preview="message"]',
                '.userContent',
                '.text_exposed_root',
                '.text_exposed_show',
                'div[dir="auto"]',
                'span[dir="auto"]',
                '[role="article"] [dir="auto"]'
            ];
            
            for (const selector of standardSelectors) {
                try {
                    const elements = postElement.querySelectorAll(selector);
                    for (const element of elements) {
                        const text = extractCleanText(element);
                        if (text && text.length > 20 && !isCommentText(text)) {
                            candidateTexts.push({
                                text: text,
                                method: 'standard_' + selector,
                                score: calculateTextScore(text, element, postRect)
                            });
                        }
                    }
                } catch (e) {
                    console.log('표준 선택자 오류:', selector, e);
                }
            }
            
            // 🔥 전략 2: 클래스 기반 검색 (페이스북 일반적인 패턴들)
            const classPatterns = [
                '[class*="userContent"]',
                '[class*="text_exposed"]',
                '[class*="message"]',
                '[class*="content"]',
                '[class*="post"]'
            ];
            
            for (const pattern of classPatterns) {
                try {
                    const elements = postElement.querySelectorAll(pattern);
                    for (const element of elements) {
                        const text = extractCleanText(element);
                        if (text && text.length > 20 && !isCommentText(text)) {
                            candidateTexts.push({
                                text: text,
                                method: 'class_' + pattern,
                                score: calculateTextScore(text, element, postRect)
                            });
                        }
                    }
                } catch (e) {
                    console.log('클래스 패턴 오류:', pattern, e);
                }
            }
            
            // 🔥 전략 3: 구조적 분석 (div 계층 구조 기반)
            const mainDivs = postElement.querySelectorAll('div');
            for (const div of mainDivs) {
                const divRect = div.getBoundingClientRect();
                const relativeTop = divRect.top - postRect.top;
                
                // 상위 70% 영역에 있는 div만 고려
                if (relativeTop < contentBoundary && divRect.height > 30) {
                    const text = extractCleanText(div);
                    if (text && text.length > 30 && !isCommentText(text)) {
                        candidateTexts.push({
                            text: text,
                            method: 'structural_div',
                            score: calculateTextScore(text, div, postRect, relativeTop)
                        });
                    }
                }
            }
            
            // 🔥 전략 4: 텍스트 노드 직접 탐색
            const walker = document.createTreeWalker(
                postElement,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            let textNodes = [];
            let node;
            while (node = walker.nextNode()) {
                if (node.textContent.trim().length > 10) {
                    textNodes.push(node);
                }
            }
            
            // 텍스트 노드들을 결합하여 완전한 텍스트 구성
            if (textNodes.length > 0) {
                let combinedText = '';
                for (const textNode of textNodes) {
                    const parentElement = textNode.parentElement;
                    if (parentElement) {
                        const rect = parentElement.getBoundingClientRect();
                        const relativeTop = rect.top - postRect.top;
                        
                        if (relativeTop < contentBoundary) {
                            const nodeText = textNode.textContent.trim();
                            if (!isCommentText(nodeText)) {
                                combinedText += nodeText + ' ';
                            }
                        }
                    }
                }
                
                if (combinedText.trim().length > 30) {
                    candidateTexts.push({
                        text: combinedText.trim(),
                        method: 'text_nodes',
                        score: calculateTextScore(combinedText.trim(), null, postRect)
                    });
                }
            }
            
            // 🔥 최고 점수 텍스트 선택
            candidateTexts.sort((a, b) => b.score - a.score);
            
            console.log('텍스트 후보들:', candidateTexts.length + '개');
            for (let i = 0; i < Math.min(3, candidateTexts.length); i++) {
                console.log('후보 ' + (i+1) + ':', {
                    method: candidateTexts[i].method,
                    score: candidateTexts[i].score,
                    length: candidateTexts[i].text.length,
                    preview: candidateTexts[i].text.substring(0, 100) + '...'
                });
            }
            
            if (candidateTexts.length > 0) {
                bestText = candidateTexts[0].text;
                console.log('최종 선택:', candidateTexts[0].method);
            }
            
            // 🔥 헬퍼 함수들
            function extractCleanText(element) {
                if (!element) return '';
                
                // innerHTML을 사용하여 줄바꿈 보존
                let html = element.innerHTML;
                
                // <br> 태그를 줄바꿈으로 변환
                html = html.replace(/<br\\s*\\/?>/gi, '\\n');
                html = html.replace(/<\\/div>/gi, '\\n');
                html = html.replace(/<\\/p>/gi, '\\n');
                
                // HTML 태그 제거
                html = html.replace(/<[^>]*>/g, '');
                
                // HTML 엔티티 디코딩
                html = html.replace(/&nbsp;/g, ' ');
                html = html.replace(/&amp;/g, '&');
                html = html.replace(/&lt;/g, '<');
                html = html.replace(/&gt;/g, '>');
                
                // 공백 정리
                html = html.replace(/\\s+/g, ' ');
                html = html.replace(/\\n\\s+/g, '\\n');
                html = html.replace(/\\n{3,}/g, '\\n\\n');
                
                return html.trim();
            }
            
            function isCommentText(text) {
                for (const indicator of commentIndicators) {
                    if (text.includes(indicator)) {
                        // "더 보기"는 예외 처리
                        if (indicator === '더 보기' || indicator === 'See more') {
                            // 주변에 댓글 키워드가 있으면 댓글 영역
                            if (text.includes('댓글') || text.includes('Comment')) {
                                return true;
                            }
                        } else {
                            return true;
                        }
                    }
                }
                
                // 댓글 패턴 체크
                if (text.match(/^[가-힣A-Za-z\\s]+님이/) || 
                    text.match(/^[가-힣A-Za-z\\s]+\\s+(wrote|said|replied)/)) {
                    return true;
                }
                
                return false;
            }
            
            function calculateTextScore(text, element, postRect, relativeTop = 0) {
                let score = 0;
                
                // 기본 길이 점수
                score += text.length;
                
                // 해시태그 가점
                if (text.includes('#')) {
                    const hashtagCount = (text.match(/#/g) || []).length;
                    score += hashtagCount * 20;
                }
                
                // IBK 키워드 가점
                if (text.includes('IBK') || text.includes('기업은행')) {
                    score += 30;
                }
                
                // 한글 내용 가점
                if (/[가-힣]/.test(text)) {
                    score += 15;
                }
                
                // 상단 위치 가점
                if (element) {
                    const rect = element.getBoundingClientRect();
                    const elementRelativeTop = rect.top - postRect.top;
                    if (elementRelativeTop < postRect.height * 0.4) {
                        score += 25;
                    }
                } else if (relativeTop < postRect.height * 0.4) {
                    score += 25;
                }
                
                // 긴 텍스트 가점
                if (text.length > 100) {
                    score += 20;
                }
                
                // 구조화된 텍스트 가점 (줄바꿈, 문장 구조)
                if (text.includes('\\n') || text.split('.').length > 3) {
                    score += 15;
                }
                
                // 댓글 패턴 감점
                if (text.includes('님이') || text.includes('wrote:') || 
                    text.includes('replied:')) {
                    score -= 30;
                }
                
                return score;
            }
            
            return bestText;
        """, post_element)
        
        if extracted_text and len(extracted_text.strip()) > 10:
            log_message(log_file, f"다중 전략 텍스트 추출 성공: {len(extracted_text)}자")
            return extracted_text
        else:
            log_message(log_file, "다중 전략 텍스트 추출 실패")
            return ""
            
    except Exception as e:
        log_message(log_file, f"다중 전략 텍스트 추출 오류: {str(e)}")
        return ""

def attempt_multiple_more_button_clicks(driver, post_element, log_file):
    """🔥 다중 방식 더보기 버튼 클릭 시도"""
    try:
        clicked = driver.execute_script("""
            const postElement = arguments[0];
            
            console.log('🔥 강화된 다중 방식 더보기 클릭 시도');
            
            // 🔥 방법 1: 정확한 텍스트 매칭
            const exactTexts = ['더 보기', 'See more', '...더 보기', '… 더 보기', 'Show more'];
            
            for (const text of exactTexts) {
                const elements = Array.from(postElement.querySelectorAll('*')).filter(el => 
                    el.textContent.trim() === text
                );
                
                for (const element of elements) {
                    if (isValidMoreButton(element, postElement)) {
                        if (attemptClick(element, '정확한 텍스트: ' + text)) {
                            return true;
                        }
                    }
                }
            }
            
            // 🔥 방법 2: 부분 텍스트 매칭 (더 관대한 조건)
            const partialTexts = ['더 보기', 'more', 'More', '더보기'];
            
            for (const text of partialTexts) {
                const elements = Array.from(postElement.querySelectorAll('*')).filter(el => {
                    const elText = el.textContent.trim();
                    return elText.includes(text) && elText.length <= text.length + 10;
                });
                
                for (const element of elements) {
                    if (isValidMoreButton(element, postElement)) {
                        if (attemptClick(element, '부분 텍스트: ' + text)) {
                            return true;
                        }
                    }
                }
            }
            
            // 🔥 방법 3: CSS 선택자 기반 (페이스북 일반적인 클래스들)
            const cssSelectors = [
                'div[role="button"][tabindex="0"]',
                'span[role="button"]',
                'div[tabindex="0"]',
                '[data-testid*="more"]',
                '[aria-label*="more"]',
                '[aria-label*="더"]'
            ];
            
            for (const selector of cssSelectors) {
                try {
                    const elements = postElement.querySelectorAll(selector);
                    for (const element of elements) {
                        const text = element.textContent.trim();
                        if ((text.includes('더') || text.toLowerCase().includes('more')) && 
                            text.length < 20 && isValidMoreButton(element, postElement)) {
                            if (attemptClick(element, 'CSS 선택자: ' + selector)) {
                                return true;
                            }
                        }
                    }
                } catch (e) {
                    console.log('CSS 선택자 오류:', e);
                }
            }
            
            // 🔥 방법 4: 위치 기반 (게시물 중간~하단 영역의 클릭 가능한 요소들)
            const postRect = postElement.getBoundingClientRect();
            const middleArea = postRect.height * 0.3; // 30% 이후부터
            const bottomArea = postRect.height * 0.8;  // 80% 이전까지
            
            const clickableElements = postElement.querySelectorAll('[role="button"], button, [tabindex="0"]');
            for (const element of clickableElements) {
                const rect = element.getBoundingClientRect();
                const relativeTop = rect.top - postRect.top;
                
                if (relativeTop >= middleArea && relativeTop <= bottomArea) {
                    const text = element.textContent.trim();
                    if (text.length > 0 && text.length < 30 && 
                        (text.includes('더') || text.toLowerCase().includes('more') || 
                         text.includes('보기') || text.includes('show'))) {
                        if (attemptClick(element, '위치 기반: ' + text)) {
                            return true;
                        }
                    }
                }
            }
            
            // 🔥 유효한 더보기 버튼인지 확인하는 함수
            function isValidMoreButton(element, postElement) {
                // 댓글 영역이 아닌지 확인
                const commentKeywords = ['댓글', '답글', 'comment', 'reply', '좋아요', 'like'];
                let parent = element.parentElement;
                
                for (let i = 0; i < 4 && parent; i++) {
                    const parentText = parent.textContent.toLowerCase();
                    for (const keyword of commentKeywords) {
                        if (parentText.includes(keyword) && parentText.length < 300) {
                            return false;
                        }
                    }
                    parent = parent.parentElement;
                }
                
                // 요소가 보이는지 확인
                const rect = element.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0;
            }
            
            // 🔥 클릭 시도 함수
            function attemptClick(element, method) {
                try {
                    console.log('클릭 시도:', method);
                    
                    // 스크롤해서 보이게 하기
                    element.scrollIntoView({behavior: 'auto', block: 'center'});
                    
                    // 잠시 대기
                    const start = Date.now();
                    while (Date.now() - start < 200) {}
                    
                    // 🔥 다양한 클릭 방법 시도
                    
                    // 방법 1: 직접 클릭
                    try {
                        element.click();
                        console.log('직접 클릭 성공:', method);
                        return true;
                    } catch (e) {
                        console.log('직접 클릭 실패:', e);
                    }
                    
                    // 방법 2: 마우스 이벤트
                    try {
                        const mouseEvent = new MouseEvent('click', {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            detail: 1
                        });
                        element.dispatchEvent(mouseEvent);
                        console.log('마우스 이벤트 성공:', method);
                        return true;
                    } catch (e) {
                        console.log('마우스 이벤트 실패:', e);
                    }
                    
                    // 방법 3: 포커스 후 엔터
                    try {
                        element.focus();
                        const enterEvent = new KeyboardEvent('keydown', {
                            key: 'Enter',
                            code: 'Enter',
                            keyCode: 13,
                            bubbles: true
                        });
                        element.dispatchEvent(enterEvent);
                        console.log('엔터 키 성공:', method);
                        return true;
                    } catch (e) {
                        console.log('엔터 키 실패:', e);
                    }
                    
                    // 방법 4: 부모 요소 클릭
                    if (element.parentElement) {
                        try {
                            element.parentElement.click();
                            console.log('부모 요소 클릭 성공:', method);
                            return true;
                        } catch (e) {
                            console.log('부모 요소 클릭 실패:', e);
                        }
                    }
                    
                    return false;
                } catch (e) {
                    console.log('클릭 시도 전체 실패:', method, e);
                    return false;
                }
            }
            
            console.log('모든 더보기 클릭 방법 실패');
            return false;
        """, post_element)
        
        if clicked:
            log_message(log_file, "다중 방식 더보기 클릭 성공")
            return True
        else:
            log_message(log_file, "모든 더보기 클릭 방법 실패")
            return False
            
    except Exception as e:
        log_message(log_file, f"다중 방식 더보기 클릭 오류: {str(e)}")
        return False


def attempt_additional_more_clicks(driver, post_element, log_file):
    """🔥 추가 더보기 클릭 시도 (짧은 텍스트일 때)"""
    try:
        log_message(log_file, "추가 더보기 버튼 검색 중...")
        
        clicked = driver.execute_script("""
            const postElement = arguments[0];
            
            console.log('🔥 추가 더보기 버튼 검색');
            
            // 🔥 새로 나타난 더보기 버튼들 찾기
            const moreTexts = ['더 보기', 'See more', 'Show more', '...더 보기', '…'];
            
            // 모든 가능한 요소 검색
            const allElements = Array.from(postElement.querySelectorAll('*'));
            
            for (const element of allElements) {
                const text = element.textContent.trim();
                
                // 더보기 패턴 체크
                const isMoreButton = moreTexts.some(pattern => text === pattern) ||
                                   (text.includes('더') && text.length < 10) ||
                                   (text.toLowerCase().includes('more') && text.length < 15);
                
                if (isMoreButton) {
                    const rect = element.getBoundingClientRect();
                    
                    // 요소가 보이고 클릭 가능한지 확인
                    if (rect.width > 0 && rect.height > 0) {
                        // 댓글 영역이 아닌지 확인
                        let isCommentArea = false;
                        let parent = element.parentElement;
                        
                        for (let i = 0; i < 3 && parent; i++) {
                            const parentText = parent.textContent.toLowerCase();
                            if (parentText.includes('댓글') || parentText.includes('comment') ||
                                parentText.includes('좋아요') || parentText.includes('like')) {
                                isCommentArea = true;
                                break;
                            }
                            parent = parent.parentElement;
                        }
                        
                        if (!isCommentArea) {
                            try {
                                console.log('추가 더보기 클릭 시도:', text);
                                element.scrollIntoView({block: 'center'});
                                
                                // 대기
                                const start = Date.now();
                                while (Date.now() - start < 300) {}
                                
                                element.click();
                                console.log('추가 더보기 클릭 성공');
                                return true;
                            } catch (e) {
                                console.log('추가 더보기 클릭 실패:', e);
                            }
                        }
                    }
                }
            }
            
            return false;
        """, post_element)
        
        return clicked
        
    except Exception as e:
        log_message(log_file, f"추가 더보기 클릭 오류: {str(e)}")
        return False


def extract_text_multiple_strategies(driver, post_element, log_file):
    """🔥 다중 전략 텍스트 추출"""
    try:
        log_message(log_file, "다중 전략 텍스트 추출 시작")
        
        extracted_text = driver.execute_script("""
            const postElement = arguments[0];
            
            console.log('🔥 다중 전략 텍스트 추출');
            
            const commentIndicators = [
                '댓글', '답글', 'Reply', 'Comment', 'Comments', 
                '좋아요', 'Like', 'Liked', '시간 전', '분 전', '일 전',
                '님이', 'wrote:', 'replied:', 'commented:', 
                'View all', '모든 댓글', '댓글 보기',
                '공유', 'Share', 'Shared'
            ];
            
            const postRect = postElement.getBoundingClientRect();
            const contentBoundary = postRect.height * 0.7; // 상위 70% 영역
            
            let bestText = '';
            let bestScore = 0;
            const candidateTexts = [];
            
            // 🔥 전략 1: Facebook 표준 선택자들
            const standardSelectors = [
                '[data-ad-preview="message"]',
                '[data-testid="post_message"]',
                '[data-ad-comet-preview="message"]',
                '.userContent',
                '.text_exposed_root',
                '.text_exposed_show',
                'div[dir="auto"]',
                'span[dir="auto"]',
                '[role="article"] [dir="auto"]'
            ];
            
            for (const selector of standardSelectors) {
                try {
                    const elements = postElement.querySelectorAll(selector);
                    for (const element of elements) {
                        const text = extractCleanText(element);
                        if (text && text.length > 20 && !isCommentText(text)) {
                            candidateTexts.push({
                                text: text,
                                method: 'standard_' + selector,
                                score: calculateTextScore(text, element, postRect)
                            });
                        }
                    }
                } catch (e) {
                    console.log('표준 선택자 오류:', selector, e);
                }
            }
            
            // 🔥 전략 2: 클래스 기반 검색 (페이스북 일반적인 패턴들)
            const classPatterns = [
                '[class*="userContent"]',
                '[class*="text_exposed"]',
                '[class*="message"]',
                '[class*="content"]',
                '[class*="post"]'
            ];
            
            for (const pattern of classPatterns) {
                try {
                    const elements = postElement.querySelectorAll(pattern);
                    for (const element of elements) {
                        const text = extractCleanText(element);
                        if (text && text.length > 20 && !isCommentText(text)) {
                            candidateTexts.push({
                                text: text,
                                method: 'class_' + pattern,
                                score: calculateTextScore(text, element, postRect)
                            });
                        }
                    }
                } catch (e) {
                    console.log('클래스 패턴 오류:', pattern, e);
                }
            }
            
            // 🔥 전략 3: 구조적 분석 (div 계층 구조 기반)
            const mainDivs = postElement.querySelectorAll('div');
            for (const div of mainDivs) {
                const divRect = div.getBoundingClientRect();
                const relativeTop = divRect.top - postRect.top;
                
                // 상위 70% 영역에 있는 div만 고려
                if (relativeTop < contentBoundary && divRect.height > 30) {
                    const text = extractCleanText(div);
                    if (text && text.length > 30 && !isCommentText(text)) {
                        candidateTexts.push({
                            text: text,
                            method: 'structural_div',
                            score: calculateTextScore(text, div, postRect, relativeTop)
                        });
                    }
                }
            }
            
            // 🔥 전략 4: 텍스트 노드 직접 탐색
            const walker = document.createTreeWalker(
                postElement,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            let textNodes = [];
            let node;
            while (node = walker.nextNode()) {
                if (node.textContent.trim().length > 10) {
                    textNodes.push(node);
                }
            }
            
            // 텍스트 노드들을 결합하여 완전한 텍스트 구성
            if (textNodes.length > 0) {
                let combinedText = '';
                for (const textNode of textNodes) {
                    const parentElement = textNode.parentElement;
                    if (parentElement) {
                        const rect = parentElement.getBoundingClientRect();
                        const relativeTop = rect.top - postRect.top;
                        
                        if (relativeTop < contentBoundary) {
                            const nodeText = textNode.textContent.trim();
                            if (!isCommentText(nodeText)) {
                                combinedText += nodeText + ' ';
                            }
                        }
                    }
                }
                
                if (combinedText.trim().length > 30) {
                    candidateTexts.push({
                        text: combinedText.trim(),
                        method: 'text_nodes',
                        score: calculateTextScore(combinedText.trim(), null, postRect)
                    });
                }
            }
            
            // 🔥 최고 점수 텍스트 선택
            candidateTexts.sort((a, b) => b.score - a.score);
            
            console.log('텍스트 후보들:', candidateTexts.length + '개');
            for (let i = 0; i < Math.min(3, candidateTexts.length); i++) {
                console.log('후보 ' + (i+1) + ':', {
                    method: candidateTexts[i].method,
                    score: candidateTexts[i].score,
                    length: candidateTexts[i].text.length,
                    preview: candidateTexts[i].text.substring(0, 100) + '...'
                });
            }
            
            if (candidateTexts.length > 0) {
                bestText = candidateTexts[0].text;
                console.log('최종 선택:', candidateTexts[0].method);
            }
            
            // 🔥 헬퍼 함수들
            function extractCleanText(element) {
                if (!element) return '';
                
                // innerHTML을 사용하여 줄바꿈 보존
                let html = element.innerHTML;
                
                // <br> 태그를 줄바꿈으로 변환
                html = html.replace(/<br\\s*\\/?>/gi, '\\n');
                html = html.replace(/<\\/div>/gi, '\\n');
                html = html.replace(/<\\/p>/gi, '\\n');
                
                // HTML 태그 제거
                html = html.replace(/<[^>]*>/g, '');
                
                // HTML 엔티티 디코딩
                html = html.replace(/&nbsp;/g, ' ');
                html = html.replace(/&amp;/g, '&');
                html = html.replace(/&lt;/g, '<');
                html = html.replace(/&gt;/g, '>');
                
                // 공백 정리
                html = html.replace(/\\s+/g, ' ');
                html = html.replace(/\\n\\s+/g, '\\n');
                html = html.replace(/\\n{3,}/g, '\\n\\n');
                
                return html.trim();
            }
            
            function isCommentText(text) {
                for (const indicator of commentIndicators) {
                    if (text.includes(indicator)) {
                        // "더 보기"는 예외 처리
                        if (indicator === '더 보기' || indicator === 'See more') {
                            // 주변에 댓글 키워드가 있으면 댓글 영역
                            if (text.includes('댓글') || text.includes('Comment')) {
                                return true;
                            }
                        } else {
                            return true;
                        }
                    }
                }
                
                // 댓글 패턴 체크
                if (text.match(/^[가-힣A-Za-z\\s]+님이/) || 
                    text.match(/^[가-힣A-Za-z\\s]+\\s+(wrote|said|replied)/)) {
                    return true;
                }
                
                return false;
            }
            
            function calculateTextScore(text, element, postRect, relativeTop = 0) {
                let score = 0;
                
                // 기본 길이 점수
                score += text.length;
                
                // 해시태그 가점
                if (text.includes('#')) {
                    const hashtagCount = (text.match(/#/g) || []).length;
                    score += hashtagCount * 20;
                }
                
                // IBK 키워드 가점
                if (text.includes('IBK') || text.includes('기업은행')) {
                    score += 30;
                }
                
                // 한글 내용 가점
                if (/[가-힣]/.test(text)) {
                    score += 15;
                }
                
                // 상단 위치 가점
                if (element) {
                    const rect = element.getBoundingClientRect();
                    const elementRelativeTop = rect.top - postRect.top;
                    if (elementRelativeTop < postRect.height * 0.4) {
                        score += 25;
                    }
                } else if (relativeTop < postRect.height * 0.4) {
                    score += 25;
                }
                
                // 긴 텍스트 가점
                if (text.length > 100) {
                    score += 20;
                }
                
                // 구조화된 텍스트 가점 (줄바꿈, 문장 구조)
                if (text.includes('\\n') || text.split('.').length > 3) {
                    score += 15;
                }
                
                // 댓글 패턴 감점
                if (text.includes('님이') || text.includes('wrote:') || 
                    text.includes('replied:')) {
                    score -= 30;
                }
                
                return score;
            }
            
            return bestText;
        """, post_element)
        
        if extracted_text and len(extracted_text.strip()) > 10:
            log_message(log_file, f"다중 전략 텍스트 추출 성공: {len(extracted_text)}자")
            return extracted_text
        else:
            log_message(log_file, "다중 전략 텍스트 추출 실패")
            return ""
            
    except Exception as e:
        log_message(log_file, f"다중 전략 텍스트 추출 오류: {str(e)}")
        return ""

def clean_facebook_text(text):
    """페이스북 텍스트 정리"""
    if not text:
        return ""
    
    import re
    
    ui_elements = [
        "좋아요", "댓글", "공유하기", "댓글 달기",
        "Like", "Comment", "Share", 
        "· 공개", "· Public", "· 친구만", "· Friends",
        "번역 보기", "See translation"
    ]
    
    cleaned_text = text
    for element in ui_elements:
        cleaned_text = cleaned_text.replace(element, "")
    
    lines = cleaned_text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        cleaned_line = re.sub(r' +', ' ', line.strip())
        if cleaned_line:
            cleaned_lines.append(cleaned_line)
        elif cleaned_lines and cleaned_lines[-1]:
            cleaned_lines.append('')
    
    final_lines = []
    prev_empty = False
    
    for line in cleaned_lines:
        if line == '':
            if not prev_empty:
                final_lines.append(line)
            prev_empty = True
        else:
            final_lines.append(line)
            prev_empty = False
    
    result = '\n'.join(final_lines).strip()
    return result

def clean_facebook_text_enhanced(text):
    """페이스북 텍스트 정리 (댓글 제거 강화)"""
    if not text:
        return ""
    
    import re
    
    # 강화된 UI 요소 및 댓글 패턴 제거
    removal_patterns = [
        # 기본 UI 요소
        "좋아요", "댓글", "공유하기", "댓글 달기",
        "Like", "Comment", "Share", 
        "· 공개", "· Public", "· 친구만", "· Friends",
        "번역 보기", "See translation",
        
        # 댓글 관련 패턴
        "님이", "wrote:", "replied:", "commented:",
        "View all comments", "모든 댓글 보기", "댓글 보기",
        "답글", "Reply", "Replies",
        
        # 시간 표시
        "시간 전", "분 전", "일 전", "주 전", "개월 전", "년 전",
        "hours ago", "minutes ago", "days ago", "weeks ago", "months ago", "years ago",
        
        # 기타 UI 요소
        "더 보기", "See more", "Show more", "Hide", "숨기기"
    ]
    
    cleaned_text = text
    for pattern in removal_patterns:
        cleaned_text = cleaned_text.replace(pattern, "")
    
    # 정규식으로 댓글 패턴 제거
    comment_regex_patterns = [
        r'\d+시간( 전)?',
        r'\d+분( 전)?', 
        r'\d+일( 전)?',
        r'\d+주( 전)?',
        r'@[A-Za-z0-9_]+',  # 멘션
        r'^[가-힣A-Za-z\s]+\s+(wrote|said|replied).*',  # 영어 댓글 패턴
        r'[가-힣A-Za-z\s]+님이\s+.*',  # 한국어 댓글 패턴
    ]
    
    for pattern in comment_regex_patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.MULTILINE)
    
    # 줄바꿈 정리
    lines = cleaned_text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        cleaned_line = re.sub(r' +', ' ', line.strip())
        if cleaned_line and len(cleaned_line) > 2:  # 너무 짧은 줄은 제거
            cleaned_lines.append(cleaned_line)
        elif cleaned_lines and cleaned_lines[-1]:
            cleaned_lines.append('')
    
    # 연속된 빈 줄 제거
    final_lines = []
    prev_empty = False
    
    for line in cleaned_lines:
        if line == '':
            if not prev_empty:
                final_lines.append(line)
            prev_empty = True
        else:
            final_lines.append(line)
            prev_empty = False
    
    result = '\n'.join(final_lines).strip()
    
    # 너무 짧은 결과는 의미 없는 것으로 판단
    if len(result) < 10:
        return "텍스트 추출 실패 - 내용이 너무 짧음"
    
    return result

def extract_post_date(driver, post_element, log_file):
    """게시물에서 날짜 추출"""
    try:
        date_text = driver.execute_script("""
            const postElement = arguments[0];
            
            const spans = postElement.querySelectorAll('span');
            for (const span of spans) {
                const text = span.textContent.trim();
                if (text.match(/\\d+[시간분일주월년]|\\d+월\\s*\\d+일|\\d+년\\s*\\d+월\\s*\\d+일/)) {
                    return text;
                }
            }
            
            const abbrs = postElement.querySelectorAll('abbr');
            for (const abbr of abbrs) {
                if (abbr.title || abbr.textContent) {
                    return abbr.textContent.trim() || abbr.title;
                }
            }
            
            return '';
        """, post_element)
        
        return date_text or '날짜 정보 없음'
    except Exception as e:
        log_message(log_file, f"날짜 추출 오류: {str(e)}")
        return '날짜 정보 없음'

def extract_post_link_enhanced(driver, post_element, log_file, is_reels=False):
    """🔥 강화된 게시물 링크 추출 (릴스 대응)"""
    try:
        if is_reels:
            # 🔥 릴스 전용 링크 추출
            return extract_reels_link(driver, post_element, log_file)
        else:
            # 일반 게시물 링크 추출
            return extract_normal_post_link(driver, post_element, log_file)
            
    except Exception as e:
        log_message(log_file, f"링크 추출 오류: {str(e)}")
        return ''


def extract_reels_link(driver, post_element, log_file):
    """🔥 릴스 게시물 링크 추출"""
    try:
        log_message(log_file, "릴스 링크 추출 시작")
        
        link = driver.execute_script("""
            const postElement = arguments[0];
            
            console.log('🔥 릴스 링크 추출 시작');
            
            // 🔥 방법 1: 릴스 전용 링크 패턴 찾기
            const reelsLinkPatterns = [
                'a[href*="/reel/"]',
                'a[href*="/reels/"]', 
                'a[href*="reel"]',
                '[data-testid*="reel"] a',
                '[aria-label*="릴스"] a',
                '[aria-label*="Reel"] a'
            ];
            
            for (const pattern of reelsLinkPatterns) {
                try {
                    const links = postElement.querySelectorAll(pattern);
                    for (const link of links) {
                        const href = link.href;
                        if (href && (href.includes('/reel/') || href.includes('/reels/'))) {
                            console.log('방법 1 성공 - 릴스 링크:', href);
                            return href.split('?')[0]; // 파라미터 제거
                        }
                    }
                } catch (e) {
                    console.log('릴스 링크 패턴 오류:', pattern, e);
                }
            }
            
            // 🔥 방법 2: IBK 페이지 내의 모든 링크에서 릴스 찾기
            const allLinks = postElement.querySelectorAll('a[href*="IBK.bank.official"]');
            for (const link of allLinks) {
                const href = link.href;
                if (href && (href.includes('/reel/') || href.includes('/reels/'))) {
                    console.log('방법 2 성공 - IBK 릴스 링크:', href);
                    return href.split('?')[0];
                }
            }
            
            // 🔥 방법 3: 릴스 텍스트 주변의 링크 찾기
            const reelsIndicators = postElement.querySelectorAll('*');
            for (const element of reelsIndicators) {
                const text = element.textContent;
                if (text && (text.includes('릴스') || text.includes('Reels'))) {
                    // 릴스 텍스트 주변의 링크 찾기
                    const nearbyLinks = element.querySelectorAll('a') || 
                                       element.parentElement?.querySelectorAll('a') ||
                                       element.closest('[role="article"]')?.querySelectorAll('a');
                    
                    if (nearbyLinks) {
                        for (const link of nearbyLinks) {
                            const href = link.href;
                            if (href && href.includes('IBK.bank.official')) {
                                console.log('방법 3 성공 - 릴스 주변 링크:', href);
                                return href.split('?')[0];
                            }
                        }
                    }
                }
            }
            
            // 🔥 방법 4: 시간 표시 링크 (릴스도 시간 링크가 있음)
            const timeElements = postElement.querySelectorAll('span, a');
            for (const element of timeElements) {
                const text = element.textContent.trim();
                if (text.match(/\\d+[시간분일주월년]/) || text.match(/\\d+\\s*(h|m|d|w)/)) {
                    // 시간 요소의 링크 찾기
                    let linkElement = element;
                    if (element.tagName.toLowerCase() !== 'a') {
                        linkElement = element.closest('a') || element.querySelector('a');
                    }
                    
                    if (linkElement && linkElement.href && linkElement.href.includes('IBK.bank.official')) {
                        console.log('방법 4 성공 - 시간 링크:', linkElement.href);
                        return linkElement.href.split('?')[0];
                    }
                }
            }
            
            // 🔥 방법 5: 게시물 헤더 영역의 링크
            const headerArea = postElement.querySelector('h3, h4, [role="heading"]');
            if (headerArea) {
                const headerLinks = headerArea.querySelectorAll('a') || 
                                   headerArea.parentElement?.querySelectorAll('a');
                if (headerLinks) {
                    for (const link of headerLinks) {
                        const href = link.href;
                        if (href && href.includes('IBK.bank.official')) {
                            console.log('방법 5 성공 - 헤더 링크:', href);
                            return href.split('?')[0];
                        }
                    }
                }
            }
            
            // 🔥 방법 6: 게시물 전체에서 IBK 링크 찾기 (최후의 수단)
            const ibkLinks = postElement.querySelectorAll('a');
            for (const link of ibkLinks) {
                const href = link.href;
                if (href && href.includes('IBK.bank.official') && 
                    !href.includes('comment_id') && !href.includes('reply_comment_id')) {
                    console.log('방법 6 성공 - 일반 IBK 링크:', href);
                    return href.split('?')[0];
                }
            }
            
            console.log('모든 릴스 링크 추출 방법 실패');
            return '';
        """, post_element)
        
        if link:
            log_message(log_file, f"릴스 링크 추출 성공: {link}")
            return link
        else:
            log_message(log_file, "릴스 링크 추출 실패")
            # 🔥 릴스 링크가 없으면 임시 링크 생성
            return generate_fallback_reels_link(driver, post_element, log_file)
            
    except Exception as e:
        log_message(log_file, f"릴스 링크 추출 오류: {str(e)}")
        return generate_fallback_reels_link(driver, post_element, log_file)


def extract_normal_post_link(driver, post_element, log_file):
    """일반 게시물 링크 추출 (기존 로직 개선)"""
    try:
        link = driver.execute_script("""
            const postElement = arguments[0];
            
            // IBK 게시물 링크 찾기 (기존 로직 개선)
            const linkPatterns = [
                'a[href*="IBK.bank.official/posts/"]',
                'a[href*="IBK.bank.official/photos/"]',
                'a[href*="IBK.bank.official/videos/"]',
                'a[href*="IBK.bank.official"]'
            ];
            
            for (const pattern of linkPatterns) {
                const links = postElement.querySelectorAll(pattern);
                for (const link of links) {
                    const href = link.href;
                    if (href && 
                        !href.includes('comment_id') && 
                        !href.includes('reply_comment_id')) {
                        return href.split('?')[0];
                    }
                }
            }
            
            return '';
        """, post_element)
        
        return link
        
    except Exception as e:
        log_message(log_file, f"일반 게시물 링크 추출 오류: {str(e)}")
        return ''


def generate_fallback_reels_link(driver, post_element, log_file):
    """🔥 릴스 대체 링크 생성"""
    try:
        log_message(log_file, "릴스 대체 링크 생성 중...")
        
        # 게시물의 고유 특성을 이용해 링크 생성
        fallback_link = driver.execute_script("""
            const postElement = arguments[0];
            
            // 🔥 릴스 대체 링크 생성 전략
            let uniqueId = '';
            
            // 1. 게시물 텍스트에서 고유 식별자 생성
            const postText = postElement.textContent || '';
            const textHash = postText.replace(/[^a-zA-Z0-9가-힣]/g, '').substring(0, 20);
            
            // 2. 시간 정보 추출
            const timeElements = postElement.querySelectorAll('span, a');
            let timeInfo = '';
            for (const element of timeElements) {
                const text = element.textContent.trim();
                if (text.match(/\\d+[시간분일주월년]/)) {
                    timeInfo = text.replace(/[^0-9]/g, '');
                    break;
                }
            }
            
            // 3. 게시물 위치 정보
            const rect = postElement.getBoundingClientRect();
            const positionHash = Math.floor(rect.top).toString().slice(-4);
            
            // 4. 현재 시간 추가
            const timestamp = Date.now().toString().slice(-6);
            
            // 고유 ID 조합
            uniqueId = `reels_${textHash}_${timeInfo}_${positionHash}_${timestamp}`;
            
            // 릴스 링크 형태로 생성
            return `https://www.facebook.com/IBK.bank.official/reel/${uniqueId}`;
        """, post_element)
        
        if fallback_link:
            log_message(log_file, f"릴스 대체 링크 생성: {fallback_link}")
            return fallback_link
        else:
            return "https://www.facebook.com/IBK.bank.official/reels/unknown"
            
    except Exception as e:
        log_message(log_file, f"릴스 대체 링크 생성 오류: {str(e)}")
        return "https://www.facebook.com/IBK.bank.official/reels/error"

def extract_post_link(driver, post_element, log_file):
    """게시물에서 링크 추출"""
    try:
        link = driver.execute_script("""
            const postElement = arguments[0];
            
            const links = postElement.querySelectorAll('a');
            for (const link of links) {
                const href = link.href;
                if (href && 
                    href.includes('IBK.bank.official') &&
                    (href.includes('/posts/') || 
                     href.includes('/photos/') || 
                     href.includes('/videos/') ||
                     href.includes('/reel/')) &&
                    !href.includes('comment_id')) {
                    return href.split('?')[0];
                }
            }
            
            return '';
        """, post_element)
        
        return link
    except Exception as e:
        log_message(log_file, f"링크 추출 오류: {str(e)}")
        return ''


def extract_image_urls(driver, post_element, log_file):
    """이미지 URL 추출"""
    try:
        image_urls = driver.execute_script("""
            const postElement = arguments[0];
            const imageUrls = [];
            
            const images = postElement.querySelectorAll('img');
            for (const img of images) {
                if (img.src && 
                    img.src.includes('scontent') && 
                    !img.src.includes('emoji') && 
                    !img.src.includes('profile') &&
                    (img.width > 100 || !img.width)) {
                    imageUrls.push(img.src);
                }
            }
            
            return [...new Set(imageUrls)];
        """, post_element)
        
        return image_urls
    except Exception as e:
        log_message(log_file, f"이미지 URL 추출 오류: {str(e)}")
        return []


def extract_post_id_from_link_enhanced(link):
    """🔥 강화된 게시물 ID 추출 (릴스 대응)"""
    if not link:
        return f"unknown_{random.randint(10000, 99999)}"
    
    try:
        # 🔥 릴스 링크 처리
        if '/reel/' in link or '/reels/' in link:
            if '/reel/' in link:
                reel_id = link.split('/reel/')[-1].split('?')[0].split('/')[0]
            else:
                reel_id = link.split('/reels/')[-1].split('?')[0].split('/')[0]
            
            # 릴스 ID가 유효한지 확인
            if reel_id and len(reel_id) > 3:
                return f"reel_{reel_id}"
            else:
                return f"reel_{random.randint(10000, 99999)}"
        
        # 기존 게시물 링크 처리
        elif '/posts/' in link:
            post_id = link.split('/posts/')[-1].split('?')[0].split('/')[0]
            return post_id if post_id else f"post_{random.randint(10000, 99999)}"
        elif '/photos/' in link:
            photo_id = link.split('/photos/')[-1].split('?')[0].split('/')[0]
            return photo_id if photo_id else f"photo_{random.randint(10000, 99999)}"
        elif '/videos/' in link:
            video_id = link.split('/videos/')[-1].split('?')[0].split('/')[0]
            return video_id if video_id else f"video_{random.randint(10000, 99999)}"
        else:
            # 알 수 없는 링크 형태
            return f"unknown_{hashlib.md5(link.encode()).hexdigest()[:10]}"
            
    except Exception as e:
        return f"error_{random.randint(10000, 99999)}"


def parse_facebook_date(date_text):
    """페이스북 날짜 파싱"""
    if not date_text or date_text == "날짜 정보 없음":
        return datetime.datetime.now()
    
    try:
        parsed_date = dateparser.parse(date_text, languages=['ko', 'en'])
        if parsed_date:
            return parsed_date
        
        import re
        
        if "주" in date_text:
            weeks_match = re.search(r'(\d+)', date_text)
            if weeks_match:
                weeks = int(weeks_match.group(1))
                return datetime.datetime.now() - datetime.timedelta(weeks=weeks)
                
        elif "일" in date_text and "월" not in date_text:
            days_match = re.search(r'(\d+)', date_text)
            if days_match:
                days = int(days_match.group(1))
                return datetime.datetime.now() - datetime.timedelta(days=days)
                
        elif "시간" in date_text:
            hours_match = re.search(r'(\d+)', date_text)
            if hours_match:
                hours = int(hours_match.group(1))
                return datetime.datetime.now() - datetime.timedelta(hours=hours)
                
        elif "분" in date_text:
            minutes_match = re.search(r'(\d+)', date_text)
            if minutes_match:
                minutes = int(minutes_match.group(1))
                return datetime.datetime.now() - datetime.timedelta(minutes=minutes)
                
        elif re.search(r'(\d+)월\s*(\d+)일', date_text):
            match = re.search(r'(\d+)월\s*(\d+)일', date_text)
            month, day = map(int, match.groups())
            current_year = datetime.datetime.now().year
            return datetime.datetime(current_year, month, day)
            
        elif re.search(r'(\d+)년\s*(\d+)월\s*(\d+)일', date_text):
            match = re.search(r'(\d+)년\s*(\d+)월\s*(\d+)일', date_text)
            year, month, day = map(int, match.groups())
            return datetime.datetime(year, month, day)
            
    except Exception as e:
        print(f"날짜 파싱 오류: {e}")
    
    return datetime.datetime.now()

def is_target_date_reached(post_date_text, target_date):
    """목표 날짜에 도달했는지 확인"""
    try:
        if not target_date:
            return True  # 목표 날짜가 없으면 모든 게시물 수집
        
        # 게시물 날짜 파싱
        post_parsed_date = parse_facebook_date(post_date_text)
        post_formatted_date = format_date_for_filename(post_parsed_date)
        
        # 목표 날짜와 비교 (YYYY-MM-DD 형식) - 목표 날짜 이후 게시물만 수집
        return post_formatted_date >= target_date
        
    except Exception as e:
        print(f"날짜 비교 오류: {e}")
        return True  # 오류 시 수집


def should_stop_crawling(post_date_text, target_date):
    """크롤링을 중단해야 하는지 확인 (목표 날짜보다 오래된 게시물)"""
    try:
        if not target_date:
            return False  # 목표 날짜가 없으면 계속 수집
            
        post_parsed_date = parse_facebook_date(post_date_text)
        post_formatted_date = format_date_for_filename(post_parsed_date)
        
        # 목표 날짜보다 오래된 게시물이면 중단
        return post_formatted_date < target_date
        
    except Exception as e:
        print(f"중단 조건 확인 오류: {e}")
        return False

def format_date_for_filename(date_obj):
    """파일명용 날짜 포맷"""
    try:
        if isinstance(date_obj, datetime.datetime):
            return date_obj.strftime("%Y-%m-%d")
        elif isinstance(date_obj, str):
            parsed_date = parse_facebook_date(date_obj)
            return parsed_date.strftime("%Y-%m-%d")
        else:
            return datetime.datetime.now().strftime("%Y-%m-%d")
    except Exception as e:
        return datetime.datetime.now().strftime("%Y-%m-%d")


def scrape_enhanced_no_duplicate_batch(driver, page_name, target_date, batch_size, batch_dir, log_file, start_offset, batch_num, start_scroll_position, processed_signatures):
    """🔥 날짜 기준 중복 방지 강화된 배치 스크래핑"""
    log_message(log_file, f"날짜 기준 배치 스크래핑 시작: {target_date} 이후 게시물 수집 (최대 {batch_size}개)")
    
    # 이전 위치에서 시작
    if start_scroll_position > 0:
        log_message(log_file, f"이전 위치로 스크롤: {start_scroll_position}px")
        driver.execute_script(f"window.scrollTo(0, {start_scroll_position});")
        time.sleep(2)
    
    batch_posts = []
    processed_in_batch = 0
    date_limit_reached = False
    
    # 스크롤 설정
    scroll_position = start_scroll_position
    scroll_increment = 600
    max_scroll_attempts = 200  # 날짜 기준이므로 더 많은 스크롤 허용
    no_progress_count = 0
    max_no_progress = 15  # 더 많은 시도 허용
    
    for scroll_attempt in range(max_scroll_attempts):
        if date_limit_reached:
            log_message(log_file, "목표 날짜에 도달하여 배치 종료")
            break
        
        # 🔥 릴스 전체화면 감지 및 복구
        current_url = driver.current_url
        if '/reel/' in current_url:
            log_message(log_file, "🚨 릴스 전체화면 감지, 즉시 복구")
            driver.back()
            time.sleep(2)
            continue
        
        # 점진적 스크롤
        driver.execute_script(f"window.scrollTo(0, {scroll_position});")
        time.sleep(2)
        
        # 🔥 새 콘텐츠 로딩 대기
        if scroll_attempt % 5 == 0:
            wait_for_new_content_load(driver, log_file, max_wait_time=10)
        
        # 🔥 중복 방지 강화된 게시물 찾기
        current_posts = find_posts_with_enhanced_uniqueness(driver, log_file, processed_signatures)
        
        if not current_posts:
            no_progress_count += 1
            if no_progress_count >= max_no_progress:
                log_message(log_file, "새 콘텐츠 로딩을 위한 강화된 스크롤링 시도")
                new_position = enhanced_scroll_for_new_content(driver, log_file, scroll_position)
                
                # 강화된 스크롤링 후에도 새 게시물이 없으면 종료
                enhanced_posts = find_posts_with_enhanced_uniqueness(driver, log_file, processed_signatures)
                if not enhanced_posts:
                    log_message(log_file, "더 이상 새 게시물이 없어 배치 종료")
                    break
                else:
                    current_posts = enhanced_posts
                    scroll_position = new_position
                    no_progress_count = 0
            else:
                scroll_position += scroll_increment * 2
                continue
        
        # 새 게시물 처리
        new_posts_found = False
        for post_data in current_posts:
            # 배치 크기 제한 확인 (날짜 조건과 함께)
            if processed_in_batch >= batch_size:
                log_message(log_file, f"배치 크기 제한({batch_size}개)에 도달")
                break
                
            if date_limit_reached:
                break
            
            # 🔥 게시물 날짜 추출 및 확인
            post_element = post_data['element']
            post_date = extract_post_date(driver, post_element, log_file)
            
            # 목표 날짜보다 오래된 게시물이면 크롤링 중단
            if should_stop_crawling(post_date, target_date):
                log_message(log_file, f"목표 날짜({target_date})보다 오래된 게시물 발견: {post_date}")
                log_message(log_file, "날짜 기준에 따라 크롤링 종료")
                date_limit_reached = True
                break
            
            # 목표 날짜 범위에 있는 게시물만 처리
            if not is_target_date_reached(post_date, target_date):
                log_message(log_file, f"목표 날짜 범위 밖 게시물 스킵: {post_date}")
                continue
            
            # 🔥 시그니처 중복 확인
            post_signatures = post_data['signatures']
            is_duplicate = False
            
            for processed_sig in processed_signatures:
                if ((post_signatures['link'] and post_signatures['link'] == processed_sig['link']) or
                    (post_signatures['textHash'] and post_signatures['textHash'] == processed_sig['textHash']) or
                    (post_signatures['combined'] == processed_sig['combined'])):
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue
            
            new_posts_found = True
            current_order = start_offset + processed_in_batch + 1
            
            # 게시물 처리
            success = process_enhanced_post_no_duplicate(
                driver, post_data, current_order, batch_dir, log_file, batch_posts
            )
            
            if success:
                # 🔥 처리된 시그니처 추가
                processed_signatures.append(post_signatures)
                processed_in_batch += 1
                log_message(log_file, f"✅ 게시물 {current_order} 처리 완료 (날짜: {post_date})")
        
        if new_posts_found:
            no_progress_count = 0
        else:
            no_progress_count += 1
        
        scroll_position += scroll_increment
    
    log_message(log_file, f"🏁 날짜 기준 배치 완료: {processed_in_batch}개 수집")
    return batch_posts, scroll_position, date_limit_reached

def process_enhanced_post_no_duplicate(driver, post_data, order, save_dir, log_file, all_posts_data):
    """🔥 중복 방지 강화된 게시물 처리"""
    try:
        is_reels = post_data['isReels']
        has_video = post_data['hasVideo']
        post_type = post_data['postType']
        
        post_element = post_data['element']
        
        # 게시물 위치로 스크롤
        target_scroll = max(0, post_data['top'] - 300)
        driver.execute_script(f"window.scrollTo(0, {target_scroll});")
        time.sleep(1)
        
        # 🔥 텍스트 추출 (릴스는 특별 처리)
        full_text = extract_complete_text_with_more_button_enhanced(driver, post_element, is_reels, log_file)
        
        # 날짜 및 링크 정보
        post_date = extract_post_date(driver, post_element, log_file)
        is_reels = post_data['isReels']
        accurate_link = extract_post_link_enhanced(driver, post_element, log_file, is_reels) or post_data.get('originalLink', '')
        post_id = extract_post_id_from_link_enhanced(accurate_link)
        formatted_date = format_date_for_filename(parse_facebook_date(post_date))
        
        # 🔥 완전 고유한 ID 생성
        timestamp = int(time.time() * 1000)
        position_hash = f"{int(post_data['top'])}x{int(post_data['height'])}"
        unique_id = f"post_{order:04d}_{timestamp}_{position_hash}"
        
        # 콘텐츠 설명
        if is_reels:
            content_description = "릴스 게시물"
            image_note = "릴스 게시물이므로 이미지가 없습니다."
        elif has_video:
            content_description = "영상 게시물"
            image_note = "영상 게시물이므로 이미지가 없습니다."
        else:
            content_description = "일반 게시물"
            image_note = "이미지 다운로드 진행"
        
        # 폴더 생성
        post_dir = os.path.join(save_dir, f"{order:04d}_{formatted_date}_{unique_id}")
        os.makedirs(post_dir)
        
        # 이미지 다운로드
        saved_images = []
        if not is_reels and not has_video:
            image_urls = extract_image_urls(driver, post_element, log_file)
            
            for j, img_url in enumerate(image_urls):
                try:
                    img_name = f"image_{j+1}.jpg"
                    img_path = os.path.join(post_dir, img_name)
                    
                    response = requests.get(img_url, timeout=5, stream=True)
                    response.raise_for_status()
                    
                    with open(img_path, 'wb') as handler:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                handler.write(chunk)
                    
                    saved_images.append(img_path)
                    
                except Exception as e:
                    log_message(log_file, f"이미지 {j+1} 다운로드 오류: {str(e)}")
                    continue
            
            image_note = f"이미지 {len(saved_images)}개 다운로드 완료"
        
        # 최종 데이터 구성
        final_post_data = {
            'order': order,
            'unique_id': unique_id,
            'post_id': post_id,
            'signatures': post_data['signatures'],
            'page_name': 'IBK.bank.official',
            'text': full_text,
            'display_date': post_date,
            'parsed_date': formatted_date,
            'post_type': post_type,
            'is_reels': is_reels,
            'has_video': has_video,
            'content_description': content_description,
            'image_note': image_note,
            'saved_images': saved_images,
            'link': accurate_link,
            'folder': post_dir
        }
        
        # 파일 저장
        try:
            with open(os.path.join(post_dir, "post_info.txt"), 'w', encoding='utf-8') as f:
                f.write(f"=== IBK 기업은행 게시물 정보 ===\n\n")
                f.write(f"순서: {order}\n")
                f.write(f"고유 ID: {unique_id}\n")
                f.write(f"게시물 ID: {post_id}\n")
                f.write(f"게시일: {post_date}\n")
                f.write(f"정제된 날짜: {formatted_date}\n")
                f.write(f"게시물 링크: {accurate_link}\n")
                f.write(f"게시물 유형: {content_description}\n")
                f.write(f"\n=== 전체 텍스트 내용 ===\n")
                f.write(f"{full_text}\n")
                f.write(f"\n=== 이미지 정보 ===\n")
                f.write(f"{image_note}\n")
                
                if saved_images:
                    for idx, img_path in enumerate(saved_images, 1):
                        f.write(f"이미지 {idx}: {os.path.basename(img_path)}\n")
                
        except Exception as e:
            log_message(log_file, f"파일 저장 오류: {str(e)}")
        
        # JSON 저장
        try:
            # JSON 직렬화를 위해 시그니처 정리
            json_data = final_post_data.copy()
            json_data['signatures'] = str(post_data['signatures'])  # 문자열로 변환
            
            with open(os.path.join(post_dir, "post_data.json"), 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log_message(log_file, f"JSON 저장 오류: {str(e)}")
        
        all_posts_data.append(final_post_data)
        
        log_message(log_file, f"✅ 게시물 {order} 저장 완료 - {content_description}")
        return True
        
    except Exception as e:
        log_message(log_file, f"❌ 게시물 {order} 처리 오류: {str(e)}")
        return False


def save_final_results(all_posts_data, save_dir, log_file, page_name):
    """최종 결과 저장 (날짜 정보 강화)"""
    if not all_posts_data:
        log_message(log_file, "저장할 데이터가 없습니다.")
        return
    
    try:
        # CSV 저장을 위해 데이터 정리
        csv_data = []
        for post in all_posts_data:
            csv_post = post.copy()
            # 복잡한 객체는 문자열로 변환
            if 'signatures' in csv_post:
                csv_post['signatures'] = str(csv_post['signatures'])
            if 'saved_images' in csv_post:
                csv_post['saved_images'] = '; '.join(csv_post['saved_images']) if csv_post['saved_images'] else ''
            csv_data.append(csv_post)
        
        # CSV 저장 (날짜순 정렬)
        df = pd.DataFrame(csv_data)
        # 날짜 기준으로 정렬 (최신순)
        df = df.sort_values(by='parsed_date', ascending=False)
        df.to_csv(os.path.join(save_dir, "all_posts_final.csv"), index=False, encoding='utf-8')
        
        # JSON 저장
        json_data = []
        for post in all_posts_data:
            json_post = post.copy()
            if 'signatures' in json_post:
                json_post['signatures'] = str(json_post['signatures'])
            json_data.append(json_post)
        
        # 날짜순 정렬
        json_data.sort(key=lambda x: x.get('parsed_date', ''), reverse=True)
        
        with open(os.path.join(save_dir, "all_posts_final.json"), 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # 통계 계산
        total_count = len(all_posts_data)
        normal_count = len([p for p in all_posts_data if p.get('post_type') == 'normal'])
        reels_count = len([p for p in all_posts_data if p.get('post_type') == 'reels'])
        video_count = len([p for p in all_posts_data if p.get('post_type') == 'video'])
        
        # 날짜 범위 계산
        dates = [p.get('parsed_date', '') for p in all_posts_data if p.get('parsed_date')]
        date_range = f"{min(dates)} ~ {max(dates)}" if dates else "날짜 정보 없음"
        
        # 완료 보고서 작성
        with open(os.path.join(save_dir, "스크래핑_완료_보고서.txt"), 'w', encoding='utf-8') as f:
            f.write(f"페이스북 날짜 기준 중복 방지 강화 스크래핑 완료 보고서\n")
            f.write(f"=" * 60 + "\n\n")
            f.write(f"완료 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"대상 페이지: {page_name}\n")
            f.write(f"총 수집 게시물: {total_count}개\n")
            f.write(f"수집된 날짜 범위: {date_range}\n\n")
            
            f.write(f"게시물 유형별 통계:\n")
            f.write(f"- 일반 게시물: {normal_count}개\n")
            f.write(f"- 릴스 게시물: {reels_count}개\n")
            f.write(f"- 영상 게시물: {video_count}개\n\n")
            
            f.write(f"날짜 기준 수집 기능:\n")
            f.write(f"- 목표 날짜 이후 게시물만 수집\n")
            f.write(f"- 목표 날짜 도달 시 자동 중단\n")
            f.write(f"- 날짜 기준 정렬 및 저장\n\n")
            
            f.write(f"중복 방지 기능:\n")
            f.write(f"- 링크 기반 중복 방지\n")
            f.write(f"- 텍스트 해시 중복 방지\n")
            f.write(f"- 위치 기반 중복 방지\n")
            f.write(f"- 복합 시그니처 중복 방지\n\n")
            
            f.write(f"릴스 처리 개선:\n")
            f.write(f"- 전체화면 진입 완전 방지\n")
            f.write(f"- 안전한 더보기 클릭\n")
            f.write(f"- 자동 복구 기능\n")
        
        log_message(log_file, f"\n{'='*60}")
        log_message(log_file, f"날짜 기준 중복 방지 강화 스크래핑 완료!")
        log_message(log_file, f"총 수집: {total_count}개 게시물")
        log_message(log_file, f"날짜 범위: {date_range}")
        log_message(log_file, f"일반: {normal_count}, 릴스: {reels_count}, 영상: {video_count}")
        log_message(log_file, f"결과 저장 위치: {save_dir}")
        log_message(log_file, f"{'='*60}")
        
    except Exception as e:
        log_message(log_file, f"최종 저장 오류: {str(e)}")


def scrape_facebook_posts_enhanced_no_duplicate(page_name, target_date=None, batch_size=100, save_dir=None, manual_verification_timeout=600):
    """🔥 날짜 기준 중복 방지 강화된 페이스북 스크래핑 메인 함수"""
    if save_dir is None:
        date_suffix = f"_from_{target_date}" if target_date else ""
        save_dir = f"facebook_{page_name}_no_duplicates_enhanced{date_suffix}"
    
    os.makedirs(save_dir, exist_ok=True)
    log_file = setup_logging(save_dir)
    
    log_message(log_file, f"🔥 날짜 기준 중복 방지 강화 스크래핑 시작: {page_name}")
    if target_date:
        log_message(log_file, f"목표 날짜: {target_date} 이후 게시물 수집")
    else:
        log_message(log_file, "목표 날짜 없음: 모든 게시물 수집")
    log_message(log_file, f"배치 크기: {batch_size}개")
    log_message(log_file, f"특별 기능: 릴스 전체화면 진입 방지, 다중 시그니처 중복 방지")
    
    # 전체 결과 저장용
    all_posts_data = []
    total_processed = 0
    processed_signatures = []  # 🔥 다중 시그니처로 중복 방지
    current_scroll_position = 0
    
    # 브라우저 한 번만 생성
    driver = create_driver()
    
    try:
        # 첫 번째 배치에서만 로그인
        log_message(log_file, "🔐 페이스북 로그인 시도...")
        login_success = facebook_login_robust(
            driver, facebook_username, facebook_password, 
            log_file, page_name, manual_verification_timeout
        )
        
        if not login_success:
            log_message(log_file, "❌ 로그인 실패로 스크래핑 중단")
            return []
        
        log_message(log_file, "✅ 로그인 성공! 날짜 기준 중복 방지 강화 스크래핑 시작")
        
        # 게시물 탭 클릭 시도
        try:
            tabs = driver.find_elements(By.XPATH, "//div[@role='tab']")
            for tab in tabs:
                if "게시물" in tab.text or "Posts" in tab.text:
                    tab.click()
                    log_message(log_file, "게시물 탭 클릭 성공")
                    time.sleep(3)
                    break
        except Exception as e:
            log_message(log_file, f"게시물 탭 클릭 시도 중 오류: {e}")
        
        # 날짜 기준 배치 처리
        batch_num = 1
        date_limit_reached = False
        
        while not date_limit_reached:
            batch_start_time = time.time()
            
            log_message(log_file, f"\n{'='*70}")
            log_message(log_file, f"🔥 날짜 기준 배치 {batch_num} 시작")
            if target_date:
                log_message(log_file, f"목표 날짜: {target_date} 이후 게시물")
            log_message(log_file, f"현재 스크롤: {current_scroll_position}px")
            log_message(log_file, f"누적 시그니처: {len(processed_signatures)}개")
            log_message(log_file, f"{'='*70}")
            
            # 배치별 저장 디렉토리
            batch_dir = os.path.join(save_dir, f"batch_{batch_num:02d}")
            os.makedirs(batch_dir, exist_ok=True)
            
            # 🔥 날짜 기준 중복 방지 강화된 배치 스크래핑
            batch_posts, new_scroll_position, batch_date_limit = scrape_enhanced_no_duplicate_batch(driver, page_name, target_date, batch_size, batch_dir, log_file, total_processed,           # 7 (start_offset)
                        batch_num,                 
                        current_scroll_position,   
                        processed_signatures       
                    )
            
            # 결과 병합
            all_posts_data.extend(batch_posts)
            total_processed += len(batch_posts)
            current_scroll_position = new_scroll_position
            date_limit_reached = batch_date_limit
            
            # 배치 완료 시간 계산
            batch_time = (time.time() - batch_start_time) / 60
            log_message(log_file, f"🏁 배치 {batch_num} 완료: {len(batch_posts)}개 수집 ({batch_time:.1f}분)")
            
            # 배치별 통계
            if batch_posts:
                reels_count = len([p for p in batch_posts if p.get('is_reels', False)])
                video_count = len([p for p in batch_posts if p.get('has_video', False)])
                normal_count = len(batch_posts) - reels_count - video_count
                
                log_message(log_file, f"📊 배치 {batch_num} 통계: 일반 {normal_count}, 릴스 {reels_count}, 영상 {video_count}")
                
                # 첫 번째와 마지막 게시물 날짜 표시
                first_date = batch_posts[0].get('display_date', '알 수 없음')
                last_date = batch_posts[-1].get('display_date', '알 수 없음')
                log_message(log_file, f"📅 배치 {batch_num} 날짜 범위: {first_date} ~ {last_date}")
            
            # 전체 진행률 표시
            log_message(log_file, f"📈 총 수집된 게시물: {total_processed}개")
            
            # 빈 배치이거나 날짜 제한에 도달한 경우 종료
            if not batch_posts or date_limit_reached:
                if date_limit_reached:
                    log_message(log_file, "🎯 목표 날짜에 도달하여 크롤링 완료!")
                else:
                    log_message(log_file, "📭 더 이상 수집할 게시물이 없습니다.")
                break
            
            # 배치 간 휴식 (브라우저는 유지)
            log_message(log_file, "⏸️ 배치 간 휴식 중... (10초)")
            time.sleep(10)
            batch_num += 1
        
    except Exception as e:
        log_message(log_file, f"❌ 날짜 기준 중복 방지 강화 스크래핑 중 오류: {str(e)}")
        traceback.print_exc()
        
    finally:
        # 스크래핑 완료 후 브라우저 종료
        try:
            log_message(log_file, "🔚 스크래핑 완료, 브라우저 종료")
            driver.quit()
        except:
            pass
    
    # 최종 결과 저장
    save_final_results(all_posts_data, save_dir, log_file, page_name)
    
    return all_posts_data

def main_enhanced_scraping():
    """🔥 날짜 기준 강화 스크래핑 메인 함수"""
    print("🔥 날짜 기준 페이스북 스크래핑 시작...")
    
    # 로그인 정보
    global facebook_username, facebook_password
    facebook_username = os.getenv("FACEBOOK_USERNAME")
    facebook_password = os.getenv("FACEBOOK_PASSWORD")
    
    # 크롤링 설정
    target_page = "IBK.bank.official"
    target_date = "2024-01-01"  # YYYY-MM-DD 형식 (이 날짜 이후 게시물 수집)
    save_directory = f"facebook_{target_page}_from_{target_date}"
    
    # 배치 설정
    batch_size = 300  # 한 번에 처리할 최대 게시물 수
    
    try:
        print("🔥 설정 정보:")
        print(f"  - 대상 페이지: {target_page}")
        print(f"  - 목표 날짜: {target_date} 이후 게시물")
        print(f"  - 배치 크기: {batch_size}개")
        print(f"  - 저장 위치: {save_directory}")
        print(f"  - 특별 기능: 릴스 전체화면 방지, 다중 시그니처 중복 방지")
        print()
        
        collected_posts = scrape_facebook_posts_enhanced_no_duplicate(
            page_name=target_page,
            target_date=target_date,  # total_posts 대신 target_date 사용
            batch_size=batch_size,
            save_dir=save_directory,
            manual_verification_timeout=300
        )
        
        print(f"\n🎉 날짜 기준 스크래핑 완료!")
        print(f"📊 총 수집된 게시물: {len(collected_posts)}개")
        print(f"📁 저장 위치: {save_directory}")
        
        # 최종 통계
        if collected_posts:
            reels_count = len([p for p in collected_posts if p.get('is_reels', False)])
            video_count = len([p for p in collected_posts if p.get('has_video', False)])
            normal_count = len(collected_posts) - reels_count - video_count
            
            print(f"📈 최종 통계:")
            print(f"  - 일반 게시물: {normal_count}개")
            print(f"  - 릴스 게시물: {reels_count}개")
            print(f"  - 영상 게시물: {video_count}개")
            
            # 날짜 범위 표시
            if len(collected_posts) > 0:
                first_date = collected_posts[0].get('display_date', '알 수 없음')
                last_date = collected_posts[-1].get('display_date', '알 수 없음')
                print(f"📅 수집된 게시물 날짜 범위: {first_date} ~ {last_date}")
        
        print(f"\n✅ 모든 작업 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        traceback.print_exc()

# 실행
if __name__ == "__main__":
    main_enhanced_scraping()