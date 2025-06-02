# markcloud_intern

# Instagram Scraper

Instagram 계정의 모든 게시물(일반 게시물 + 릴스)을 자동으로 수집하는 Python 스크래퍼입니다.

## 주요 기능

- **완전 자동화**: 로그인부터 게시물 수집까지 모든 과정이 자동화
- **릴스 지원**: 일반 게시물과 릴스를 모두 수집
- **다중 이미지 지원**: 캐러셀 게시물의 모든 이미지를 수집
- **진행 상황 저장**: 중단된 경우 이어서 실행 가능
- **상세한 로깅**: 모든 과정을 로그 파일에 기록
- **데이터 구조화**: CSV, JSON 형태로 체계적으로 저장

## 필요 조건

### Python 패키지

```bash
pip install selenium webdriver-manager requests pandas dateparser

```

### 시스템 요구사항

- Python 3.7+
- Chrome 브라우저
- 안정적인 인터넷 연결

## 설치 및 설정

1. **필요 패키지 설치**

```bash
pip install -r requirements.txt
```

1. **로그인 정보 설정**
    - `instagram_scraper.py` 파일에서 다음 부분을 수정:

```python
instagram_username = "your_username"
instagram_password = "your_password"
```

1. **타겟 계정 설정**

```python
target_account = "target_instagram_username"
```

## 사용법

### 기본 실행

```bash
python instagram_scraper.py
```

### 게시물 수 설정

**코드에서 수집할 게시물 수 변경:**

```python
# 메인 실행 블록에서 수정
collected_posts = scrape_all_posts_sequential(
    username=target_account,
    max_posts=100,              # 여기서 원하는 게시물 수 설정
    save_dir=save_directory,
    start_index=start_index,
    driver=main_driver
)
```

**추천 설정값:**

- **테스트용**: `max_posts=10` (빠른 테스트)
- **소규모**: `max_posts=50` (최근 게시물만)
- **중간 규모**: `max_posts=200` (적당한 양)
- **대규모**: `max_posts=1000` (거의 모든 게시물)
- **전체**: `max_posts=5000` (모든 게시물, 시간 오래 걸림)

### 기타 설정 옵션

```python
# 저장 디렉토리 커스터마이징
save_directory = f"instagram_{target_account}_custom_name"

# 헤드리스 모드 (백그라운드 실행)
chrome_options.add_argument("--headless")  # 주석 해제하면 백그라운드 실행

# 특정 인덱스부터 시작 (수동 설정 시)
start_index = 50  # 51번째 게시물부터 시작
```

## 수집되는 데이터

### 각 게시물별로 수집되는 정보:

- **텍스트 내용**: 게시물의 모든 텍스트
- **이미지**: 모든 이미지 파일 (릴스 제외)
- **메타데이터**: 날짜, 게시물 ID, 타입 등
- **링크**: 원본 게시물 URL

### 출력 파일 구조:

```
instagram_username_all/
├── scraping_log.txt                    # 스크래핑 로그
├── all_posts_summary.csv              # 모든 게시물 요약 (CSV)
├── all_posts_summary.json             # 모든 게시물 요약 (JSON)
├── progress.json                      # 진행 상황 저장
├── SCRAPING_COMPLETE.txt              # 완료 표시
├── 001_2024-01-15_post_ABC123/        # 개별 게시물 폴더
│   ├── info.txt                       # 게시물 정보 (텍스트)
│   ├── info.json                      # 게시물 정보 (JSON)
│   ├── image.jpg                      # 단일 이미지
│   ├── image_01.jpg                   # 다중 이미지 1
│   └── image_02.jpg                   # 다중 이미지 2
└── 002_2024-01-14_reel_DEF456/        # 릴스 폴더
    ├── info.txt
    └── info.json
```

## 고급 기능

### 중단 후 재시작

- 스크래핑이 중단된 경우, 다시 실행하면 자동으로 이어서 진행
- `progress.json` 파일이 진행 상황을 추적

### 헤드리스 모드

```python
chrome_options.add_argument("--headless")  # 주석 해제
```

### 커스텀 설정

**함수 매개변수 상세 설명:**

```python
def scrape_all_posts_sequential(
    username,           # 타겟 계정명 (필수)
    max_posts=100,      # 수집할 최대 게시물 수 (기본값: 100)
    save_dir=None,      # 저장 디렉토리 (기본값: instagram_{username}_all)
    start_index=0,      # 시작 인덱스 (기본값: 0, 처음부터)
    driver=None         # 기존 드라이버 재사용 (기본값: None, 새로 생성)
):
```

**실제 사용 예시:**

```python
# 최근 50개 게시물만 수집
collected_posts = scrape_all_posts_sequential(
    username="goodibk",
    max_posts=50,
    save_dir="recent_posts_only"
)

# 500개 게시물 수집 (대용량)
collected_posts = scrape_all_posts_sequential(
    username="goodibk",
    max_posts=500
)
```

## 주의사항 및 제한사항

### ⚠️ 중요 주의사항

1. **Instagram 이용약관 준수**: Instagram의 이용약관을 반드시 확인하고 준수하세요
2. **개인정보 보호**: 다른 사용자의 개인정보를 무단으로 수집하지 마세요
3. **법적 책임**: 스크래핑으로 인한 모든 법적 책임은 사용자에게 있습니다

### 기술적 제한사항

- **속도 제한**: Instagram의 제한을 피하기 위해 요청 간 딜레이 적용
- **Private 계정**: 비공개 계정은 팔로우 승인 후에만 접근 가능
- **2FA**: 2단계 인증이 활성화된 계정은 수동 처리 필요
- **계정 차단 위험**: 과도한 요청 시 임시 차단 가능성

## 문제 해결

### 일반적인 문제들

**1. 로그인 실패**

```
해결방법:
- 사용자명/비밀번호 확인
- 2단계 인증 비활성화 또는 앱 비밀번호 사용
- IP 차단 여부 확인
```

**2. 크롬드라이버 오류**

```bash
# 최신 버전으로 업데이트
pip install --upgrade webdriver-manager
```

**3. 메모리 부족**

```python
# 배치 크기 줄이기
max_posts = 50  # 기본값을 낮춤
```

**4. 네트워크 타임아웃**

```python
# 타임아웃 시간 증가
response = requests.get(img_url, timeout=30)  # 기본 15초에서 30초로
```

### 로그 확인

- 모든 활동이 `scraping_log.txt`에 기록됨
- 오류 발생 시 로그 파일을 먼저 확인

## 성능 최적화

### 권장 설정

```python
# 빠른 수집을 위한 설정
chrome_options.add_argument("--disable-images")      # 이미지 로딩 비활성화
chrome_options.add_argument("--disable-javascript")  # JavaScript 비활성화 (주의: 일부 기능 제한)
```

### 처리 방식

**순차적 처리:**

- 이 스크래퍼는 모든 게시물을 한 번에 순차적으로 처리합니다
- 중간에 중단되어도 `progress.json`을 통해 이어서 실행 가능
- 5개 게시물마다 자동으로 중간 저장하여 데이터 손실 방지

**예상 소요 시간:**

| 게시물 수 | 예상 시간 | 특징 |
| --- | --- | --- |
| 10-50개 | 5-15분 | 빠른 테스트 |
| 100-200개 | 30-60분 | 일반적 사용 |
| 500개 | 2-3시간 | 장시간 실행 |
| 1000개+ | 5시간+ | 매우 장시간, 안정적 네트워크 필요 |

**중단 및 재시작:**

```python
# 실행 중 중단되면 자동으로 진행 상황 저장
# 다시 실행하면 중단된 지점부터 자동 재개
python instagram_scraper.py  # 이어서 실행됨
```

## 변경 이력

### v1.0.0

- 기본 게시물 스크래핑 기능
- 릴스 지원 추가
- 다중 이미지 지원
- 진행 상황 저장 기능
- 자동 재시작 기능


# Facebook Scraper - IBK 기업은행 게시물 수집기

## 📋 개요

IBK 기업은행 Facebook 페이지의 게시물을 자동으로 수집하는 웹 스크래핑 도구입니다. 날짜 기준 수집, 중복 방지, 릴스 처리 등의 기능을 제공합니다.

## ⭐ 주요 특징

### 🔥 날짜 기준 수집

- **설정 날짜 이후** 게시물만 선별적으로 수집
- **자동 중단**: 목표 날짜보다 오래된 게시물 발견 시 크롤링 자동 종료
- **날짜 파싱**: 한국어 시간 표현 ("1시간 전", "3일 전" 등) 파싱 지원

### 🛡️ 중복 방지 시스템

- **다중 시그니처 방식**: 링크, 텍스트 해시, 위치, 복합 시그니처 기반
- **정확한 중복 탐지**: 동일한 게시물의 반복 수집 완벽 차단
- **실시간 중복 확인**: 스크롤 중 이미 처리된 게시물 즉시 필터링

### 🎬 릴스 특화 처리

- **전체화면 진입 방지**: 릴스 클릭 시 전체화면 모드 진입 완전 차단
- **안전한 텍스트 추출**: 전체화면 진입 없이 릴스 본문 내용 추출
- **자동 복구**: 실수로 전체화면 진입 시 자동으로 메인 페이지 복귀
- **릴스 더보기 처리**: 릴스의 축약된 텍스트 안전하게 확장

### 📦 배치 처리 시스템

- **배치 단위 처리**: 설정 가능한 배치 크기로 메모리 효율적 처리
- **진행률 추적**: 실시간 수집 진행상황 모니터링
- **안정성**: 중간 오류 발생 시에도 이미 수집된 데이터 보존

### 🔍 강화된 텍스트 추출

- **다중 방식 더보기 클릭**: 정확한 텍스트/CSS 선택자/위치 기반 다중 방식
- **댓글 영역 제거**: 게시물 본문에서 댓글/UI 요소 자동 제거
- **다중 전략 텍스트 추출**: Facebook 표준 선택자, 클래스 패턴, 구조적 분석, 텍스트 노드 탐색

## 🛠️ 설치 요구사항

### Python 패키지

```bash
pip install selenium webdriver-manager requests pandas beautifulsoup4 dateparser
```

### 시스템 요구사항

- Python 3.7 이상
- Google Chrome 브라우저 (ChromeDriver는 자동 설치)

## 📁 프로젝트 구조

```
facebook_scraper/
├── facebook_scraper.py          # 메인 스크래퍼 코드
├── README.md                    # 이 파일
└── 결과 폴더/
    ├── facebook_IBK.bank.official_from_2024-01-01/
    │   ├── batch_01/            # 배치별 게시물 저장
    │   │   ├── 0001_2024-01-15_post_xxx/
    │   │   │   ├── post_info.txt
    │   │   │   ├── post_data.json
    │   │   │   └── image_1.jpg
    │   │   └── ...
    │   ├── all_posts_final.csv  # 전체 결과 CSV
    │   ├── all_posts_final.json # 전체 결과 JSON
    │   └── 스크래핑_완료_보고서.txt
    └── scraping_log.txt         # 상세 로그

```

## 🚀 사용 방법

### 1. 기본 설정

```python
# facebook_scraper.py 파일에서 설정 변경
facebook_username = "your_email@example.com"  # Facebook 로그인 이메일
facebook_password = "your_password"           # Facebook 비밀번호
target_page = "IBK.bank.official"             # 수집할 페이지
target_date = "2024-01-01"                    # 수집 시작 날짜 (YYYY-MM-DD)
```

### 2. 실행

```bash
python facebook_scraper.py
```

### 3. 로그인 처리

- 2단계 인증이 활성화된 경우 브라우저에서 직접 수동으로 인증 필요
- 보안 검증 요청 시 안내에 따라 수동 인증
- 인증 완료 후 콘솔에서 Enter 키를 눌러 계속 진행

## ⚙️ 주요 설정 옵션

### 날짜 설정

```python
target_date = "2024-01-01"  # 이 날짜 이후 게시물만 수집
target_date = None          # 모든 게시물 수집 (날짜 제한 없음)
```

### 배치 크기

```python
batch_size = 300  # 한 배치당 최대 처리할 게시물 수
```

### 저장 디렉토리

```python
save_directory = f"facebook_{target_page}_from_{target_date}"
```

## 📊 출력 데이터 형식

### CSV 파일 (all_posts_final.csv)

| 컬럼명 | 설명 |
| --- | --- |
| order | 수집 순서 |
| unique_id | 고유 식별자 |
| post_id | Facebook 게시물 ID |
| page_name | 페이지 명 |
| text | 게시물 전체 텍스트 |
| display_date | 게시물 표시 날짜 |
| parsed_date | 파싱된 날짜 (YYYY-MM-DD) |
| post_type | 게시물 유형 (normal/reels/video) |
| is_reels | 릴스 여부 |
| has_video | 영상 포함 여부 |
| link | 게시물 링크 |
| saved_images | 저장된 이미지 목록 |

### JSON 파일 (all_posts_final.json)

```json
{
  "order": 1,
  "unique_id": "post_0001_1640995200000_1000x500",
  "post_id": "12345678901234567",
  "page_name": "IBK.bank.official",
  "text": "게시물 전체 내용...",
  "display_date": "1시간 전",
  "parsed_date": "2024-01-01",
  "post_type": "normal",
  "is_reels": false,
  "has_video": false,
  "link": "https://www.facebook.com/IBK.bank.official/posts/...",
  "saved_images": ["image_1.jpg", "image_2.jpg"]
}
```

## 🔧 코드의 핵심 기능

### 1. 중복 방지 시스템

```python
signatures = {
    'link': post_link,                    # 게시물 링크
    'textHash': text_hash,               # 텍스트 해시 (100자)
    'position': scroll_position,         # 화면 위치 (100px 단위)
    'size': element_height,              # 요소 크기 (50px 단위)
    'combined': combined_signature       # 복합 시그니처
}
```

### 2. 릴스 안전 처리

```python
# 전체화면 진입 감지 및 복구
if '/reel/' in current_url:
    driver.back()  # 즉시 뒤로가기
    time.sleep(2)
```

### 3. 다중 방식 더보기 클릭

- **정확한 텍스트 매칭**: "더 보기", "See more" 등
- **CSS 선택자 기반**: role="button", tabindex="0" 등
- **위치 기반 탐지**: 게시물 중간~하단 영역의 클릭 가능한 요소
- **다양한 클릭 방법**: 직접 클릭, 마우스 이벤트, 엔터 키, 부모 요소 클릭

### 4. Facebook 구조 분석

- **표준 선택자**: data-ad-preview="message", userContent 등
- **클래스 패턴**: class*="userContent", class*="text_exposed" 등
- **구조적 분석**: div 계층 구조 기반 텍스트 추출
- **텍스트 노드 탐색**: DOM TreeWalker를 통한 직접 텍스트 노드 접근

## 📈 추가 최적화 기능

### 로그인 및 보안

- **2단계 인증 지원**: 수동 인증 대기 및 안내
- **다중 로그인 상태 확인**: URL, 요소, 사용자 입력 기반 확인
- **보안 검증 처리**: checkpoint, two_step_verification 등 자동 감지

### 스크롤링 최적화

- **점진적 스크롤**: 600px씩 자연스러운 스크롤
- **새 콘텐츠 로딩 대기**: 동적 콘텐츠 로딩 완료까지 대기
- **강화된 스크롤 패턴**: 여러 스크롤 방식(scrollBy, scrollTo, Space키) 조합

## 🚨 주의사항

### Facebook 이용약관 준수

- Facebook의 이용약관 및 로봇 배제 표준 확인 필요
- 과도한 요청으로 인한 계정 제재 방지
- 개인정보 포함 데이터 처리 시 주의

### 기술적 제한사항

- Facebook 페이지 구조 변경 시 코드 수정 필요
- 대량 수집 시 IP 차단 가능성
- 로그인 보안 정책 변경에 따른 인증 과정 변화

## 🔍 문제 해결

### 로그인 실패

- 이메일/비밀번호 확인
- 2단계 인증 설정 확인
- 브라우저에서 수동 인증 완료 후 Enter 키

### 게시물 추출 실패

- Chrome 브라우저 및 ChromeDriver 업데이트
- 로그 파일(scraping_log.txt)에서 상세 오류 확인
- Facebook 페이지 구조 변경 여부 확인

### 릴스 처리 오류

- 브라우저 창 크기 조절
- 스크롤 속도 및 대기 시간 조절
- 전체화면 진입 방지 기능 동작 확인# markcloud_intern
# markcloud_intern
