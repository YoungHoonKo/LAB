# =========================================================
# 히비스커스티 블로그 수집 + 4개 모델 감정 분석 비교
# - Naver Blog Search API로 링크 수집
# - 블로그 본문 크롤링
# - GPT / Gemini / Ollama / Qwen 감정 분석 비교
# - 크롤링 단계에서는 점수화하지 않음
# =========================================================

import os
import re
import json
import time
import html
import requests
import pandas as pd

from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()  


# =========================================================
# 0. 환경변수
# =========================================================
# 꼭 본인 키로 바꿔서 export 하세요.
#
# export NAVER_CLIENT_ID="..."
# export NAVER_CLIENT_SECRET="..."
# export OPENAI_API_KEY="..."
# export GEMINI_API_KEY="..."
# export DASHSCOPE_API_KEY="..."
#
# 선택:
# export OLLAMA_BASE_URL="http://localhost:11434"
# export OLLAMA_MODEL="qwen3:8b"
# export OPENAI_MODEL="gpt-4.1-mini"
# export GEMINI_MODEL="gemini-2.0-flash"
# export QWEN_MODEL="qwen-plus"


def read_env(name: str) -> str:
    value = os.environ.get(name, "")
    return value.strip() if isinstance(value, str) else ""


def get_naver_credentials() -> tuple[str, str]:
    return read_env("NAVER_CLIENT_ID"), read_env("NAVER_CLIENT_SECRET")


NAVER_CLIENT_ID, NAVER_CLIENT_SECRET = get_naver_credentials()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "").strip()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b").strip()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus").strip()

# Qwen 글로벌 엔드포인트 예시 (싱가포르)
QWEN_BASE_URL = os.getenv(
    "QWEN_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
).strip()


NAVER_BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"
NAVER_SHOP_SEARCH_URL = "https://openapi.naver.com/v1/search/shop.json"

OUTPUT_RAW_CSV = "hibiscus_tea_raw_crawled.csv"
OUTPUT_COMPARE_CSV = "hibiscus_tea_sentiment_compare.csv"
OUTPUT_BRAND_CSV = "hibiscus_tea_brand_candidates.csv"
OUTPUT_BRAND_MAPPING_CSV = "hibiscus_tea_brand_mapping.csv"
OUTPUT_COLLECTED_BRANDS_CSV = "hibiscus_tea_collected_brands.csv"
OUTPUT_OVERVIEW_CSV = "hibiscus_tea_assignment_overview.csv"
OUTPUT_SUMMARY_CSV = "hibiscus_tea_assignment_summary.csv"
OUTPUT_SENTIMENT_SUMMARY_CSV = "hibiscus_tea_sentiment_summary.csv"

SEARCH_QUERY = "히비스커스티"
SHOPPING_BRAND_QUERIES = [
    "히비스커스티",
    "히비스커스 차",
    "히비스커스 티백",
    "히비스커스 허브티",
    "hibiscus tea",
]
MAX_SEARCH_ITEMS = 1000   # Naver Blog Search API start 범위 기준 최대 후보 수집량
MAX_SHOPPING_BRAND_ITEMS_PER_QUERY = 1000
REQUEST_SLEEP = 0.25
CRAWL_TIMEOUT = 10

# 과제 요구사항이 "브랜드 후보군/맵핑" 중심이므로 감정 분석은 기본값으로 끕니다.
# 감정 분석까지 실행하려면 터미널에서 RUN_SENTIMENT_ANALYSIS=1 로 설정하면 됩니다.
RUN_SENTIMENT_ANALYSIS = read_env("RUN_SENTIMENT_ANALYSIS") == "1"
SENTIMENT_MAX_ITEMS = int(read_env("SENTIMENT_MAX_ITEMS") or "50")

# =========================================================
# 브랜드 후보군 사전
# - 교수님 과제: "브랜드 후보군을 정해서 오기"
# - 자동 추출이 어려운 경우를 대비해 대표 브랜드명을 직접 맵핑합니다.
# - 필요하면 아래 BRAND_KEYWORD_MAP에 브랜드/표기 변형을 계속 추가하면 됩니다.
# =========================================================
BRAND_KEYWORD_MAP = {
    "오설록": ["오설록", "OSULLOC", "osulloc"],
    "티젠": ["티젠", "TEAZEN", "teazen"],
    "쌍계명차": ["쌍계명차", "쌍계", "Ssanggye", "ssanggye"],
    "담터": ["담터", "Damtuh", "damtuh"],
    "녹차원": ["녹차원", "Nokchawon", "nokchawon"],
    "트와이닝": ["트와이닝", "Twinings", "twinings"],
    "아마드티": ["아마드티", "Ahmad Tea", "ahmad tea", "Ahmad", "ahmad"],
    "립톤": ["립톤", "Lipton", "lipton"],
    "티칸네": ["티칸네", "Teekanne", "teekanne"],
    "포트넘앤메이슨": ["포트넘앤메이슨", "Fortnum", "fortnum", "Fortnum & Mason", "fortnum & mason"],
    "하니앤손스": ["하니앤손스", "Harney", "harney", "Harney & Sons", "harney & sons"],
    "요기티": ["요기티", "Yogi Tea", "yogi tea"],
    "푸카": ["푸카", "Pukka", "pukka"],
    "셀레셜시즈닝스": ["셀레셜시즈닝스", "Celestial Seasonings", "celestial seasonings"],
    "타바론": ["타바론", "Tavalon", "tavalon"],
    "티소믈리에": ["티소믈리에", "Tea Sommelier", "tea sommelier"],
    "공차": ["공차", "Gong cha", "gong cha", "gongcha"],
    "스타벅스": ["스타벅스", "Starbucks", "starbucks"],
    "투썸플레이스": ["투썸플레이스", "투썸", "A Twosome Place", "twosome"],
    "이디야": ["이디야", "EDIYA", "ediya"],
}

# 쇼핑 API에서 수집한 브랜드 후보 중 너무 일반적이거나 오탐 가능성이 높은 단어는 제외합니다.
BRAND_STOPWORDS = {
    "기타", "상세설명참조", "상세설명 참고", "상품상세참조", "해당없음", "없음", "무관",
    "수입", "수입품", "국내", "해외", "자체제작", "주식회사", "유한회사", "농업회사법인",
    "차", "티", "허브", "허브티", "티백", "히비스커스", "히비스커스티", "분말", "가루",
}

# 브랜드가 직접 언급되지 않아도 상품/키워드 기반으로 후보군을 묶기 위한 맵핑입니다.
# 이 맵핑은 "확정 브랜드"가 아니라 "분석용 후보군"입니다.
PRODUCT_CATEGORY_KEYWORDS = {
    "히비스커스 계열": ["히비스커스", "hibiscus", "하이비스커스"],
    "허브티 계열": ["허브티", "허브 티", "herbal tea", "herb tea"],
    "차/티백 계열": ["티백", "tea bag", "teabag", "tea bags", "침출차", "티", "차"],
    "카페인 프리 계열": ["카페인 프리", "카페인프리", "무카페인", "논카페인", "decaf", "caffeine free", "non caffeine", "non-caffeine"],
    "다이어트/붓기 계열": ["다이어트", "붓기", "부기", "이너뷰티", "inner beauty", "diet"],
    "항산화/비타민 계열": ["항산화", "비타민", "vitamin", "안토시아닌", "anthocyanin"],
    "아이스티/음료 계열": ["아이스티", "ice tea", "iced tea", "에이드", "ade", "음료", "drink"],
    "블렌딩티 계열": ["블렌딩", "블렌드", "blend", "blending", "로즈힙", "rosehip", "베리", "berry"],
}


# =========================================================
# 1. 공통 유틸
# =========================================================
def remove_invalid_unicode(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return re.sub(r"[\ud800-\udfff]", "", text)


def clean_text(text: Optional[str]) -> str:
    if not isinstance(text, str):
        return ""
    text = remove_invalid_unicode(text)
    text = html.unescape(text)
    text = text.replace("<b>", "").replace("</b>", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate_text(text: str, max_len: int = 6000) -> str:
    text = clean_text(text)
    if len(text) <= max_len:
        return text
    return text[:max_len]


def safe_get(obj, path, default=None):
    cur = obj
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        elif isinstance(cur, list) and isinstance(p, int) and 0 <= p < len(cur):
            cur = cur[p]
        else:
            return default
    return cur


def sanitize_dataframe_for_csv(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    clean_df = df.copy()
    for col in clean_df.columns:
        if clean_df[col].dtype == "object":
            clean_df[col] = clean_df[col].map(
                lambda value: remove_invalid_unicode(value) if isinstance(value, str) else value
            )
    return clean_df


def normalize_for_match(text: str) -> str:
    """
    브랜드/상품명 매칭용 정규화 함수입니다.
    - 대소문자 차이 제거
    - HTML 태그 제거
    - 공백 중복 제거
    """
    text = clean_text(text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_keywords_in_text(text: str, keyword_map: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    keyword_map 형식:
    {
        "대표명": ["표기1", "표기2", ...]
    }

    반환 형식:
    {
        "대표명": ["실제로 매칭된 표기1", ...]
    }
    """
    normalized_text = normalize_for_match(text)
    matched = {}

    for canonical_name, keywords in keyword_map.items():
        hit_keywords = []
        for keyword in keywords:
            normalized_keyword = normalize_for_match(keyword)
            if normalized_keyword and normalized_keyword in normalized_text:
                hit_keywords.append(keyword)

        if hit_keywords:
            matched[canonical_name] = sorted(set(hit_keywords))

    return matched


def build_brand_analysis_text(row: pd.Series) -> str:
    """
    브랜드 후보군 분석에 사용할 텍스트를 하나로 합칩니다.
    제목/설명/본문/블로거명을 모두 사용합니다.
    """
    parts = [
        str(row.get("title", "")),
        str(row.get("description", "")),
        str(row.get("blogger", "")),
        str(row.get("body_text", "")),
    ]
    return " ".join(parts)


# =========================================================
# 2. 네이버 블로그 검색 API
# =========================================================
def naver_blog_search(query: str, display: int = 100, start: int = 1) -> List[dict]:
    client_id, client_secret = get_naver_credentials()
    if not client_id or not client_secret:
        print("⚠️ NAVER API 키가 설정되지 않았습니다. 크롤링을 건너뜁니다.")
        print(f"DEBUG NAVER ENV: CLIENT_ID={bool(client_id)}, CLIENT_SECRET={bool(client_secret)}")
        return []

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {
        "query": query,
        "display": min(display, 100),
        "start": start,
        "sort": "date",
    }

    res = requests.get(
        NAVER_BLOG_SEARCH_URL,
        headers=headers,
        params=params,
        timeout=CRAWL_TIMEOUT,
    )
    res.raise_for_status()
    data = res.json()
    return data.get("items", [])


def collect_blog_candidates(query: str, max_items: int = 80) -> List[dict]:
    rows = []
    seen = set()

    start = 1
    display = 100

    while len(rows) < max_items and start <= 1000:
        items = naver_blog_search(query=query, display=display, start=start)

        if not items:
            break

        for it in items:
            if len(rows) >= max_items:
                break

            link = it.get("link", "").strip()
            if not link or link in seen:
                continue
            seen.add(link)

            rows.append({
                "search_query": query,
                "title": clean_text(it.get("title", "")),
                "description": clean_text(it.get("description", "")),
                "blogger": clean_text(it.get("bloggername", "")),
                "postdate": it.get("postdate", ""),
                "link": link,
            })

        start += display
        time.sleep(REQUEST_SLEEP)

    return rows


def naver_shopping_search(query: str, display: int = 100, start: int = 1) -> List[dict]:
    """
    네이버 쇼핑 검색 API에서 상품 후보를 가져옵니다.
    브랜드 후보군 자동 수집을 위해 brand/maker 필드를 사용합니다.
    """
    client_id, client_secret = get_naver_credentials()
    if not client_id or not client_secret:
        print("⚠️ NAVER API 키가 설정되지 않았습니다. 쇼핑 브랜드 수집을 건너뜁니다.")
        return []

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {
        "query": query,
        "display": min(display, 100),
        "start": start,
        "sort": "sim",
    }

    try:
        res = requests.get(
            NAVER_SHOP_SEARCH_URL,
            headers=headers,
            params=params,
            timeout=CRAWL_TIMEOUT,
        )
        res.raise_for_status()
        data = res.json()
        return data.get("items", [])
    except Exception as e:
        print(f"⚠️ 쇼핑 검색 실패: query={query}, start={start}, error={e}")
        return []


def normalize_brand_name(name: str) -> str:
    """
    네이버 쇼핑 API의 brand/maker 값을 브랜드 후보군으로 쓰기 위한 정규화 함수입니다.
    """
    name = clean_text(name)
    name = re.sub(r"[\[\]\(\){}<>]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def is_valid_brand_candidate(name: str) -> bool:
    """
    브랜드 후보로 사용하기 어려운 값 제거.
    - 너무 짧은 값 제거
    - 일반 상품군 단어 제거
    - 숫자/기호 중심 값 제거
    """
    if not name:
        return False

    normalized = normalize_brand_name(name)
    lowered = normalized.lower()

    if len(normalized) < 2:
        return False
    if normalized in BRAND_STOPWORDS or lowered in {w.lower() for w in BRAND_STOPWORDS}:
        return False
    if re.fullmatch(r"[0-9\W_]+", normalized):
        return False

    return True


def collect_brand_candidates_from_shopping(queries: List[str], max_items_per_query: int = 1000) -> pd.DataFrame:
    """
    업로드된 brand_collect 노트북의 핵심 로직을 스크립트에 통합한 함수입니다.
    네이버 쇼핑 API의 brand/maker 필드에서 브랜드 후보군을 수집합니다.
    """
    brand_records = {}

    print("[0] 쇼핑 API 기반 브랜드 후보군 수집 시작")

    for query in queries:
        print(f"    쇼핑 브랜드 수집 중: {query}")
        start = 1
        display = 100
        collected_for_query = 0

        while collected_for_query < max_items_per_query and start <= 1000:
            items = naver_shopping_search(query=query, display=display, start=start)
            if not items:
                break

            for item in items:
                collected_for_query += 1
                raw_brand = normalize_brand_name(item.get("brand", ""))
                raw_maker = normalize_brand_name(item.get("maker", ""))

                for source_field, candidate in [("brand", raw_brand), ("maker", raw_maker)]:
                    if not is_valid_brand_candidate(candidate):
                        continue

                    if candidate not in brand_records:
                        brand_records[candidate] = {
                            "brand": candidate,
                            "source_queries": set(),
                            "source_fields": set(),
                            "shopping_mention_count": 0,
                        }

                    brand_records[candidate]["source_queries"].add(query)
                    brand_records[candidate]["source_fields"].add(source_field)
                    brand_records[candidate]["shopping_mention_count"] += 1

            start += display
            time.sleep(REQUEST_SLEEP)

    rows = []
    for record in brand_records.values():
        rows.append({
            "brand": record["brand"],
            "shopping_mention_count": record["shopping_mention_count"],
            "source_queries": ", ".join(sorted(record["source_queries"])),
            "source_fields": ", ".join(sorted(record["source_fields"])),
        })

    brand_df = pd.DataFrame(rows)
    if not brand_df.empty:
        brand_df = brand_df.sort_values(
            ["shopping_mention_count", "brand"],
            ascending=[False, True]
        ).reset_index(drop=True)

    brand_df = sanitize_dataframe_for_csv(brand_df)
    brand_df.to_csv(OUTPUT_COLLECTED_BRANDS_CSV, index=False, encoding="utf-8-sig")
    print(f"[0] 쇼핑 기반 브랜드 후보군 저장 완료: {OUTPUT_COLLECTED_BRANDS_CSV} ({len(brand_df)}개)")
    return brand_df


def build_dynamic_brand_keyword_map(collected_brand_df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    쇼핑 API에서 수집한 브랜드 후보군을 기존 매칭 사전 형식으로 변환합니다.
    수동 브랜드 사전과 병합해서 블로그 본문 매칭에 사용합니다.
    """
    dynamic_map = {}

    if collected_brand_df.empty or "brand" not in collected_brand_df.columns:
        return dynamic_map

    for brand in collected_brand_df["brand"].dropna().astype(str):
        brand = normalize_brand_name(brand)
        if not is_valid_brand_candidate(brand):
            continue
        dynamic_map[brand] = [brand]

    return dynamic_map


def merge_brand_keyword_maps(static_map: Dict[str, List[str]], dynamic_map: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    수동 브랜드 사전과 쇼핑 API 기반 동적 브랜드 사전을 병합합니다.
    같은 브랜드가 있으면 키워드 목록을 합칩니다.
    """
    merged = {brand: list(keywords) for brand, keywords in static_map.items()}

    for brand, keywords in dynamic_map.items():
        if brand not in merged:
            merged[brand] = []
        merged[brand].extend(keywords)
        merged[brand] = sorted(set(merged[brand]))

    return merged


# =========================================================
# 3. 네이버 블로그 본문 크롤링
# =========================================================
def normalize_blog_url(url: str) -> str:
    """
    네이버 블로그는 PC/모바일/iframe 구조가 섞여 있어서
    모바일 주소로 바꾸면 비교적 본문 추출이 쉬운 경우가 많습니다.
    """
    if "blog.naver.com" in url and "m.blog.naver.com" not in url:
        return url.replace("https://blog.naver.com", "https://m.blog.naver.com")
    return url


def fetch_html(url: str) -> Optional[str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
        )
    }
    try:
        res = requests.get(url, headers=headers, timeout=CRAWL_TIMEOUT)
        res.raise_for_status()
        return res.text
    except Exception:
        return None


def extract_text_from_selectors(soup: BeautifulSoup, selectors: List[str]) -> str:
    texts = []
    for sel in selectors:
        for node in soup.select(sel):
            txt = clean_text(node.get_text(" ", strip=True))
            if txt:
                texts.append(txt)

    joined = " ".join(texts)
    joined = re.sub(r"\s+", " ", joined).strip()
    return joined


def crawl_naver_blog_body(url: str) -> Dict[str, str]:
    """
    반환:
    {
        "final_url": "...",
        "content": "...",
        "status": "ok" | "fail"
    }
    """
    mobile_url = normalize_blog_url(url)
    html_text = fetch_html(mobile_url)

    if not html_text:
        return {"final_url": mobile_url, "content": "", "status": "fail"}

    soup = BeautifulSoup(html_text, "html.parser")

    # 네이버 블로그에서 자주 보이는 본문 셀렉터들
    selectors = [
        "div.se-main-container",
        "div#postViewArea",
        "div.post_ct",
        "div.contents_style",
        "div.se_component_wrap",
        "div.blog2_series",
        "div.post_view",
        "div#viewTypeSelector",
        "div#post-area",
    ]

    content = extract_text_from_selectors(soup, selectors)

    # 너무 짧으면 iframe 구조를 한 번 더 시도
    if len(content) < 80:
        iframe = soup.select_one("iframe#mainFrame")
        if iframe and iframe.get("src"):
            iframe_url = iframe.get("src")
            if iframe_url.startswith("/"):
                iframe_url = "https://blog.naver.com" + iframe_url

            iframe_html = fetch_html(iframe_url)
            if iframe_html:
                iframe_soup = BeautifulSoup(iframe_html, "html.parser")
                content = extract_text_from_selectors(iframe_soup, selectors)
                return {
                    "final_url": iframe_url,
                    "content": content,
                    "status": "ok" if content else "fail",
                }

    return {
        "final_url": mobile_url,
        "content": content,
        "status": "ok" if content else "fail",
    }


# =========================================================
# 4. 감정 분석 프롬프트
# =========================================================
def build_sentiment_prompt(title: str, description: str, body_text: str) -> str:
    body_text = truncate_text(body_text, 5000)

    return f"""
너는 제품 후기 텍스트 분석가다.
아래 텍스트는 '히비스커스티'와 관련된 블로그 글이다.

반드시 JSON만 출력해라.
설명 문장, 마크다운, 코드블록 없이 순수 JSON만 출력해라.

출력 형식:
{{
  "label": "positive | neutral | negative",
  "reason": "한글 한 문장 요약",
  "evidence": ["근거1", "근거2"],
  "confidence": 0.0
}}

판단 기준:
- 제품/음용 경험/맛/향/만족도/불만/활용성/구매의사/효용성 중심
- 광고성 문장처럼 보이면 reason이나 evidence에 그 단서를 반영
- 정보가 부족하면 neutral
- confidence는 0~1 사이 숫자

[제목]
{title}

[설명]
{description}

[본문]
{body_text}
""".strip()


def parse_model_json(text: str) -> dict:
    """
    모델이 JSON 외 텍스트를 섞어도 최대한 복구
    """
    if not text:
        return {
            "label": "error",
            "reason": "empty response",
            "evidence": [],
            "confidence": 0.0,
        }

    text = text.strip()

    # 코드블록 제거
    text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    # JSON 부분만 추출
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        text = match.group(0)

    try:
        data = json.loads(text)
        return {
            "label": data.get("label", "error"),
            "reason": data.get("reason", ""),
            "evidence": data.get("evidence", []) if isinstance(data.get("evidence", []), list) else [],
            "confidence": float(data.get("confidence", 0.0)),
        }
    except Exception:
        return {
            "label": "error",
            "reason": f"json parse failed: {text[:200]}",
            "evidence": [],
            "confidence": 0.0,
        }


# =========================================================
# 5. API 호출기
# =========================================================
def call_openai(prompt: str, model: str) -> dict:
    if not OPENAI_API_KEY:
        return {"provider": "openai", "model": model, "raw_text": "", "error": "OPENAI_API_KEY missing"}

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()

        raw_text = ""
        choices = data.get("choices", [])
        if choices:
            raw_text = choices[0].get("message", {}).get("content", "").strip()

        return {"provider": "openai", "model": model, "raw_text": raw_text, "error": ""}
    except Exception as e:
        return {"provider": "openai", "model": model, "raw_text": "", "error": str(e)}


def call_gemini(prompt: str, model: str) -> dict:
    if not GEMINI_API_KEY:
        return {"provider": "gemini", "model": model, "raw_text": "", "error": "GEMINI_API_KEY missing"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
        }
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()

        raw_text = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = safe_get(candidates[0], ["content", "parts"], [])
            texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")]
            raw_text = "\n".join(texts).strip()

        return {"provider": "gemini", "model": model, "raw_text": raw_text, "error": ""}
    except Exception as e:
        return {"provider": "gemini", "model": model, "raw_text": "", "error": str(e)}


def call_ollama(prompt: str, model: str) -> dict:
    """
    로컬 Ollama를 기본 가정
    기본 엔드포인트: http://localhost:11434/api/generate
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0
        }
    }

    try:
        res = requests.post(url, json=payload, timeout=120)
        res.raise_for_status()
        data = res.json()
        raw_text = data.get("response", "").strip()
        return {"provider": "ollama", "model": model, "raw_text": raw_text, "error": ""}
    except Exception as e:
        return {"provider": "ollama", "model": model, "raw_text": "", "error": str(e)}


def call_qwen(prompt: str, model: str) -> dict:
    if not DASHSCOPE_API_KEY:
        return {"provider": "qwen", "model": model, "raw_text": "", "error": "DASHSCOPE_API_KEY missing"}

    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
    }

    try:
        res = requests.post(QWEN_BASE_URL, headers=headers, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()

        raw_text = safe_get(data, ["choices", 0, "message", "content"], "")
        return {"provider": "qwen", "model": model, "raw_text": raw_text, "error": ""}
    except Exception as e:
        return {"provider": "qwen", "model": model, "raw_text": "", "error": str(e)}


def run_all_models(prompt: str) -> List[dict]:
    results = []
    results.append(call_openai(prompt, OPENAI_MODEL))
    results.append(call_gemini(prompt, GEMINI_MODEL))
    results.append(call_ollama(prompt, OLLAMA_MODEL))
    results.append(call_qwen(prompt, QWEN_MODEL))
    return results


# =========================================================
# 6. 메인 파이프라인
# =========================================================
def crawl_pipeline():
    print(f"[1] 검색 시작: {SEARCH_QUERY}")
    candidates = collect_blog_candidates(SEARCH_QUERY, max_items=MAX_SEARCH_ITEMS)
    print(f"    후보 수집 완료: {len(candidates)}개")

    rows = []
    for i, item in enumerate(candidates, start=1):
        print(f"[2] 본문 크롤링 {i}/{len(candidates)}")
        body_result = crawl_naver_blog_body(item["link"])

        rows.append({
            **item,
            "crawled_url": body_result["final_url"],
            "crawl_status": body_result["status"],
            "body_text": body_result["content"],
            "body_length": len(body_result["content"]),
        })

        time.sleep(REQUEST_SLEEP)

    raw_df = pd.DataFrame(rows, columns=[
        "search_query", "title", "description", "blogger", "postdate", "link",
        "crawled_url", "crawl_status", "body_text", "body_length"
    ])
    raw_df = sanitize_dataframe_for_csv(raw_df)
    raw_df.to_csv(OUTPUT_RAW_CSV, index=False, encoding="utf-8-sig")
    print(f"    원본 저장 완료: {OUTPUT_RAW_CSV}")

    return raw_df


def sentiment_compare_pipeline(raw_df: pd.DataFrame):
    required_cols = {"crawl_status", "body_length"}

    if raw_df.empty or not required_cols.issubset(raw_df.columns):
        print("[3] 감정 분석 대상이 없습니다. 빈 결과 파일을 저장합니다.")
        compare_df = pd.DataFrame(columns=[
            "title", "description", "blogger", "postdate", "link", "crawled_url",
            "body_length",
            "openai_model", "openai_api_error", "openai_label", "openai_reason", "openai_evidence", "openai_confidence", "openai_raw_output",
            "gemini_model", "gemini_api_error", "gemini_label", "gemini_reason", "gemini_evidence", "gemini_confidence", "gemini_raw_output",
            "ollama_model", "ollama_api_error", "ollama_label", "ollama_reason", "ollama_evidence", "ollama_confidence", "ollama_raw_output",
            "qwen_model", "qwen_api_error", "qwen_label", "qwen_reason", "qwen_evidence", "qwen_confidence", "qwen_raw_output"
        ])
        compare_df = sanitize_dataframe_for_csv(compare_df)
        compare_df.to_csv(OUTPUT_COMPARE_CSV, index=False, encoding="utf-8-sig")
        print(f"    비교 저장 완료: {OUTPUT_COMPARE_CSV}")
        return compare_df

    usable_df = raw_df[
        (raw_df["crawl_status"] == "ok") &
        (raw_df["body_length"] >= 80)
    ].copy()

    if SENTIMENT_MAX_ITEMS > 0:
        usable_df = usable_df.head(SENTIMENT_MAX_ITEMS)

    print(f"[3] 감정 분석 대상: {len(usable_df)}개")

    compare_rows = []

    for idx, row in usable_df.iterrows():
        print(f"[4] 모델 비교 중: {row['title'][:40]}")

        prompt = build_sentiment_prompt(
            title=row["title"],
            description=row["description"],
            body_text=row["body_text"],
        )

        model_results = run_all_models(prompt)

        grouped = {
            "openai": {
                "model": "", "api_error": "", "label": "", "reason": "",
                "evidence": "[]", "confidence": 0.0, "raw_output": ""
            },
            "gemini": {
                "model": "", "api_error": "", "label": "", "reason": "",
                "evidence": "[]", "confidence": 0.0, "raw_output": ""
            },
            "ollama": {
                "model": "", "api_error": "", "label": "", "reason": "",
                "evidence": "[]", "confidence": 0.0, "raw_output": ""
            },
            "qwen": {
                "model": "", "api_error": "", "label": "", "reason": "",
                "evidence": "[]", "confidence": 0.0, "raw_output": ""
            },
        }

        for r in model_results:
            parsed = parse_model_json(r["raw_text"])
            provider = r["provider"]
            if provider not in grouped:
                continue

            grouped[provider] = {
                "model": r["model"],
                "api_error": r["error"],
                "label": parsed["label"],
                "reason": parsed["reason"],
                "evidence": json.dumps(parsed["evidence"], ensure_ascii=False),
                "confidence": parsed["confidence"],
                "raw_output": r["raw_text"],
            }

        compare_rows.append({
            "title": row["title"],
            "description": row["description"],
            "blogger": row["blogger"],
            "postdate": row["postdate"],
            "link": row["link"],
            "crawled_url": row["crawled_url"],
            "body_length": row["body_length"],

            "openai_model": grouped["openai"]["model"],
            "openai_api_error": grouped["openai"]["api_error"],
            "openai_label": grouped["openai"]["label"],
            "openai_reason": grouped["openai"]["reason"],
            "openai_evidence": grouped["openai"]["evidence"],
            "openai_confidence": grouped["openai"]["confidence"],
            "openai_raw_output": grouped["openai"]["raw_output"],

            "gemini_model": grouped["gemini"]["model"],
            "gemini_api_error": grouped["gemini"]["api_error"],
            "gemini_label": grouped["gemini"]["label"],
            "gemini_reason": grouped["gemini"]["reason"],
            "gemini_evidence": grouped["gemini"]["evidence"],
            "gemini_confidence": grouped["gemini"]["confidence"],
            "gemini_raw_output": grouped["gemini"]["raw_output"],

            "ollama_model": grouped["ollama"]["model"],
            "ollama_api_error": grouped["ollama"]["api_error"],
            "ollama_label": grouped["ollama"]["label"],
            "ollama_reason": grouped["ollama"]["reason"],
            "ollama_evidence": grouped["ollama"]["evidence"],
            "ollama_confidence": grouped["ollama"]["confidence"],
            "ollama_raw_output": grouped["ollama"]["raw_output"],

            "qwen_model": grouped["qwen"]["model"],
            "qwen_api_error": grouped["qwen"]["api_error"],
            "qwen_label": grouped["qwen"]["label"],
            "qwen_reason": grouped["qwen"]["reason"],
            "qwen_evidence": grouped["qwen"]["evidence"],
            "qwen_confidence": grouped["qwen"]["confidence"],
            "qwen_raw_output": grouped["qwen"]["raw_output"],
        })

        time.sleep(0.5)

    compare_df = pd.DataFrame(compare_rows)
    compare_df = sanitize_dataframe_for_csv(compare_df)
    compare_df.to_csv(OUTPUT_COMPARE_CSV, index=False, encoding="utf-8-sig")
    print(f"    비교 저장 완료: {OUTPUT_COMPARE_CSV}")
    return compare_df


# =========================================================
# 7. 브랜드 후보군 추출 / 맵핑 파이프라인
# =========================================================
def brand_candidate_pipeline(raw_df: pd.DataFrame, brand_keyword_map: Optional[Dict[str, List[str]]] = None):
    """
    교수님 과제용 브랜드 후보군 생성 파이프라인입니다.

    목적:
    1. 크롤링된 텍스트에서 브랜드명을 직접 매칭합니다.
    2. 브랜드명이 직접 나오지 않으면 상품군 키워드로 보조 맵핑합니다.
    3. 결과를 두 개 파일로 저장합니다.
       - hibiscus_tea_brand_candidates.csv: 브랜드별 등장 빈도 요약
       - hibiscus_tea_brand_mapping.csv: 게시글별 브랜드/상품군 맵핑 결과
    """
    if brand_keyword_map is None:
        brand_keyword_map = BRAND_KEYWORD_MAP

    if raw_df.empty:
        print("[5] 브랜드 후보군 분석 대상이 없습니다.")
        brand_df = pd.DataFrame(columns=[
            "brand_candidate", "mention_count", "post_count", "matched_keywords", "mapping_type"
        ])
        mapping_df = pd.DataFrame(columns=[
            "title", "blogger", "postdate", "link", "brand_candidates",
            "brand_matched_keywords", "product_category_candidates", "product_category_matched_keywords",
            "mapping_note"
        ])
        brand_df = sanitize_dataframe_for_csv(brand_df)
        mapping_df = sanitize_dataframe_for_csv(mapping_df)
        brand_df.to_csv(OUTPUT_BRAND_CSV, index=False, encoding="utf-8-sig")
        mapping_df.to_csv(OUTPUT_BRAND_MAPPING_CSV, index=False, encoding="utf-8-sig")
        return brand_df, mapping_df

    mapping_rows = []
    brand_counter = {}
    brand_post_counter = {}
    brand_keyword_hits = {}
    category_counter = {}
    category_post_counter = {}
    category_keyword_hits = {}

    for _, row in raw_df.iterrows():
        analysis_text = build_brand_analysis_text(row)

        matched_brands = find_keywords_in_text(analysis_text, brand_keyword_map)
        matched_categories = find_keywords_in_text(analysis_text, PRODUCT_CATEGORY_KEYWORDS)

        for brand, keywords in matched_brands.items():
            brand_counter[brand] = brand_counter.get(brand, 0) + len(keywords)
            brand_post_counter[brand] = brand_post_counter.get(brand, 0) + 1
            brand_keyword_hits.setdefault(brand, set()).update(keywords)

        for category, keywords in matched_categories.items():
            category_counter[category] = category_counter.get(category, 0) + len(keywords)
            category_post_counter[category] = category_post_counter.get(category, 0) + 1
            category_keyword_hits.setdefault(category, set()).update(keywords)

        mapping_note = "brand_direct_match"
        if not matched_brands and matched_categories:
            mapping_note = "brand_not_found_product_category_mapping"
        elif not matched_brands and not matched_categories:
            mapping_note = "no_brand_or_category_match"

        mapping_rows.append({
            "title": row.get("title", ""),
            "blogger": row.get("blogger", ""),
            "postdate": row.get("postdate", ""),
            "link": row.get("link", ""),
            "brand_candidates": ", ".join(matched_brands.keys()),
            "brand_matched_keywords": json.dumps(matched_brands, ensure_ascii=False),
            "product_category_candidates": ", ".join(matched_categories.keys()),
            "product_category_matched_keywords": json.dumps(matched_categories, ensure_ascii=False),
            "mapping_note": mapping_note,
        })

    brand_rows = []

    for brand, mention_count in brand_counter.items():
        brand_rows.append({
            "brand_candidate": brand,
            "mention_count": mention_count,
            "post_count": brand_post_counter.get(brand, 0),
            "matched_keywords": ", ".join(sorted(brand_keyword_hits.get(brand, []))),
            "mapping_type": "direct_brand_match",
        })

    for category, mention_count in category_counter.items():
        brand_rows.append({
            "brand_candidate": category,
            "mention_count": mention_count,
            "post_count": category_post_counter.get(category, 0),
            "matched_keywords": ", ".join(sorted(category_keyword_hits.get(category, []))),
            "mapping_type": "product_category_mapping",
        })

    brand_df = pd.DataFrame(brand_rows)
    if not brand_df.empty:
        brand_df = brand_df.sort_values(
            ["mapping_type", "post_count", "mention_count"],
            ascending=[True, False, False]
        ).reset_index(drop=True)

    mapping_df = pd.DataFrame(mapping_rows)

    brand_df = sanitize_dataframe_for_csv(brand_df)
    mapping_df = sanitize_dataframe_for_csv(mapping_df)
    brand_df.to_csv(OUTPUT_BRAND_CSV, index=False, encoding="utf-8-sig")
    mapping_df.to_csv(OUTPUT_BRAND_MAPPING_CSV, index=False, encoding="utf-8-sig")

    print(f"[5] 브랜드 후보군 저장 완료: {OUTPUT_BRAND_CSV}")
    print(f"[5] 게시글별 브랜드 맵핑 저장 완료: {OUTPUT_BRAND_MAPPING_CSV}")

    if not brand_df.empty:
        print("\n[브랜드 후보군 요약]")
        print(brand_df.head(20).to_string(index=False))
    else:
        print("\n[브랜드 후보군 요약] 매칭된 브랜드/상품군이 없습니다.")

    return brand_df, mapping_df


# =========================================================
# 8. 과제 제출용 CSV 결과 생성
# =========================================================
def build_sentiment_summary(compare_df: pd.DataFrame) -> pd.DataFrame:
    """
    모델별 감정 라벨 분포를 CSV 요약 파일용 DataFrame으로 만듭니다.
    """
    if compare_df.empty:
        return pd.DataFrame(columns=["provider", "label", "count"])

    summary_rows = []
    for provider in ["openai", "gemini", "ollama", "qwen"]:
        label_col = f"{provider}_label"
        if label_col not in compare_df.columns:
            continue

        counts = compare_df[label_col].value_counts(dropna=False)
        for label, count in counts.items():
            summary_rows.append({
                "provider": provider,
                "label": label,
                "count": int(count),
            })

    if not summary_rows:
        return pd.DataFrame(columns=["provider", "label", "count"])

    return pd.DataFrame(summary_rows).sort_values(
        ["provider", "count"],
        ascending=[True, False]
    ).reset_index(drop=True)


def build_assignment_overview(raw_df: pd.DataFrame, brand_df: pd.DataFrame, mapping_df: pd.DataFrame, compare_df: pd.DataFrame) -> pd.DataFrame:
    """
    과제 요구사항을 한눈에 보여주는 개요 CSV용 DataFrame입니다.
    """
    crawled_ok_count = 0
    if not raw_df.empty and "crawl_status" in raw_df.columns:
        crawled_ok_count = int((raw_df["crawl_status"] == "ok").sum())

    direct_brand_count = 0
    product_mapping_count = 0
    if not brand_df.empty and "mapping_type" in brand_df.columns:
        direct_brand_count = int((brand_df["mapping_type"] == "direct_brand_match").sum())
        product_mapping_count = int((brand_df["mapping_type"] == "product_category_mapping").sum())

    no_match_count = 0
    if not mapping_df.empty and "mapping_note" in mapping_df.columns:
        no_match_count = int((mapping_df["mapping_note"] == "no_brand_or_category_match").sum())

    sentiment_target_count = 0
    if not compare_df.empty:
        sentiment_target_count = len(compare_df)

    rows = [
        {"항목": "검색 키워드", "값": SEARCH_QUERY, "설명": "Naver Blog Search API에 사용한 검색어"},
        {"항목": "최대 수집 후보 수", "값": MAX_SEARCH_ITEMS, "설명": "API start 범위 기준 최대 후보 수"},
        {"항목": "수집된 후보 게시글 수", "값": len(raw_df), "설명": "중복 링크 제거 후 수집된 블로그 후보 수"},
        {"항목": "본문 크롤링 성공 수", "값": crawled_ok_count, "설명": "본문 텍스트 추출에 성공한 게시글 수"},
        {"항목": "직접 브랜드 후보 수", "값": direct_brand_count, "설명": "수동 브랜드 사전과 쇼핑 API 기반 브랜드 후보군에서 직접 매칭된 후보 수"},
        {"항목": "상품군 맵핑 후보 수", "값": product_mapping_count, "설명": "브랜드 직접 추출이 어려울 때 상품군으로 보조 맵핑한 후보 수"},
        {"항목": "브랜드/상품군 미매칭 게시글 수", "값": no_match_count, "설명": "브랜드와 상품군 모두 매칭되지 않은 게시글 수"},
        {"항목": "감정 분석 실행 여부", "값": "실행" if RUN_SENTIMENT_ANALYSIS else "미실행", "설명": "RUN_SENTIMENT_ANALYSIS=1일 때만 감정 분석을 실행"},
        {"항목": "감정 분석 대상 수", "값": sentiment_target_count, "설명": "본문 길이 기준을 통과하고 SENTIMENT_MAX_ITEMS 제한을 적용한 게시글 수"},
    ]
    return pd.DataFrame(rows)


def build_assignment_summary(raw_df: pd.DataFrame, brand_df: pd.DataFrame, mapping_df: pd.DataFrame, compare_df: pd.DataFrame) -> pd.DataFrame:
    """
    과제 제출용 핵심 요약 CSV를 생성하기 위한 DataFrame입니다.
    - 수집 요약
    - 브랜드 직접 매칭 결과
    - 상품군 맵핑 결과
    - 게시글별 분류
    - 감정 분석 요약
    """
    summary_rows = []

    summary_rows.append({
        "구분": "수집 요약",
        "항목": "수집 글 수",
        "게시글 수": len(raw_df),
        "비고": "중복 링크 제거 후 수집된 게시글 수",
    })

    if not raw_df.empty and "crawl_status" in raw_df.columns:
        crawled_ok_count = int((raw_df["crawl_status"] == "ok").sum())
    else:
        crawled_ok_count = 0

    summary_rows.append({
        "구분": "수집 요약",
        "항목": "본문 크롤링 성공",
        "게시글 수": crawled_ok_count,
        "비고": "crawl_status가 ok인 게시글 수",
    })

    if not raw_df.empty and "body_length" in raw_df.columns:
        avg_body_length = round(float(raw_df["body_length"].mean()), 2)
    else:
        avg_body_length = 0

    summary_rows.append({
        "구분": "수집 요약",
        "항목": "평균 본문 길이",
        "게시글 수": avg_body_length,
        "비고": "body_length 평균값",
    })

    if not brand_df.empty and "mapping_type" in brand_df.columns:
        direct_brand_df = brand_df[brand_df["mapping_type"] == "direct_brand_match"].copy()
        if not direct_brand_df.empty:
            direct_brand_df = direct_brand_df.sort_values(["post_count", "mention_count"], ascending=[False, False])

        for _, row in direct_brand_df.iterrows():
            summary_rows.append({
                "구분": "브랜드 직접 매칭 결과",
                "항목": row.get("brand_candidate", ""),
                "게시글 수": int(row.get("post_count", 0)),
                "비고": row.get("matched_keywords", ""),
            })

    if not brand_df.empty and "mapping_type" in brand_df.columns:
        product_mapping_df = brand_df[brand_df["mapping_type"] == "product_category_mapping"].copy()
        if not product_mapping_df.empty:
            product_mapping_df = product_mapping_df.sort_values(["post_count", "mention_count"], ascending=[False, False])

        for _, row in product_mapping_df.iterrows():
            summary_rows.append({
                "구분": "상품군 맵핑 결과",
                "항목": row.get("brand_candidate", ""),
                "게시글 수": int(row.get("post_count", 0)),
                "비고": row.get("matched_keywords", ""),
            })

    if not mapping_df.empty and "mapping_note" in mapping_df.columns:
        mapping_counts = mapping_df["mapping_note"].value_counts()
    else:
        mapping_counts = pd.Series(dtype="int64")

    label_map = {
        "brand_direct_match": "브랜드 직접 매칭",
        "brand_not_found_product_category_mapping": "브랜드 없음 → 상품군 맵핑",
        "no_brand_or_category_match": "브랜드/상품군 모두 미매칭",
    }

    for key, label in label_map.items():
        summary_rows.append({
            "구분": "게시글별 분류",
            "항목": label,
            "게시글 수": int(mapping_counts.get(key, 0)),
            "비고": key,
        })

    if compare_df.empty:
        summary_rows.append({
            "구분": "감정 분석",
            "항목": "감정 분석 성공",
            "게시글 수": 0,
            "비고": "기본 설정에서는 감정 분석 미실행",
        })
    else:
        label_columns = [col for col in compare_df.columns if col.endswith("_label")]
        success_count = 0
        if label_columns:
            success_count = int((compare_df[label_columns] != "").any(axis=1).sum())

        summary_rows.append({
            "구분": "감정 분석",
            "항목": "감정 분석 대상 수",
            "게시글 수": len(compare_df),
            "비고": "RUN_SENTIMENT_ANALYSIS=1 실행 시 생성",
        })
        summary_rows.append({
            "구분": "감정 분석",
            "항목": "감정 분석 성공 추정 수",
            "게시글 수": success_count,
            "비고": "하나 이상의 모델 label 값이 존재하는 게시글 수",
        })

    return pd.DataFrame(summary_rows, columns=["구분", "항목", "게시글 수", "비고"])


def save_assignment_csv_results(raw_df: pd.DataFrame, brand_df: pd.DataFrame, mapping_df: pd.DataFrame, compare_df: pd.DataFrame):
    """
    과제 제출용 결과를 CSV 파일로 저장합니다.

    생성 파일:
    1. hibiscus_tea_assignment_overview.csv: 과제 결과 개요
    2. hibiscus_tea_assignment_summary.csv: 과제 핵심 요약
    3. hibiscus_tea_collected_brands.csv: 쇼핑 API 기반 브랜드 후보군 원본
    4. hibiscus_tea_brand_candidates.csv: 브랜드 후보군 요약
    5. hibiscus_tea_brand_mapping.csv: 게시글별 브랜드/상품군 맵핑 결과
    6. hibiscus_tea_sentiment_summary.csv: 모델별 감정 라벨 분포
    7. hibiscus_tea_sentiment_compare.csv: 게시글별 모델 감정 분석 결과
    8. hibiscus_tea_raw_crawled.csv: 원본 크롤링 결과
    """
    overview_df = build_assignment_overview(raw_df, brand_df, mapping_df, compare_df)
    assignment_summary_df = build_assignment_summary(raw_df, brand_df, mapping_df, compare_df)
    sentiment_summary_df = build_sentiment_summary(compare_df)

    overview_df = sanitize_dataframe_for_csv(overview_df)
    assignment_summary_df = sanitize_dataframe_for_csv(assignment_summary_df)
    brand_df = sanitize_dataframe_for_csv(brand_df)
    mapping_df = sanitize_dataframe_for_csv(mapping_df)
    sentiment_summary_df = sanitize_dataframe_for_csv(sentiment_summary_df)
    compare_df = sanitize_dataframe_for_csv(compare_df)
    raw_df = sanitize_dataframe_for_csv(raw_df)

    overview_df.to_csv(OUTPUT_OVERVIEW_CSV, index=False, encoding="utf-8-sig")
    assignment_summary_df.to_csv(OUTPUT_SUMMARY_CSV, index=False, encoding="utf-8-sig")
    brand_df.to_csv(OUTPUT_BRAND_CSV, index=False, encoding="utf-8-sig")
    mapping_df.to_csv(OUTPUT_BRAND_MAPPING_CSV, index=False, encoding="utf-8-sig")
    sentiment_summary_df.to_csv(OUTPUT_SENTIMENT_SUMMARY_CSV, index=False, encoding="utf-8-sig")
    compare_df.to_csv(OUTPUT_COMPARE_CSV, index=False, encoding="utf-8-sig")
    raw_df.to_csv(OUTPUT_RAW_CSV, index=False, encoding="utf-8-sig")

    print(f"[6] 과제 개요 CSV 저장 완료: {OUTPUT_OVERVIEW_CSV}")




# =========================================================
# 9. 실행
# =========================================================
if __name__ == "__main__":
    collected_brand_df = collect_brand_candidates_from_shopping(
        SHOPPING_BRAND_QUERIES,
        max_items_per_query=MAX_SHOPPING_BRAND_ITEMS_PER_QUERY,
    )
    dynamic_brand_map = build_dynamic_brand_keyword_map(collected_brand_df)
    merged_brand_map = merge_brand_keyword_maps(BRAND_KEYWORD_MAP, dynamic_brand_map)

    raw_df = crawl_pipeline()
    brand_df, mapping_df = brand_candidate_pipeline(raw_df, brand_keyword_map=merged_brand_map)

    if RUN_SENTIMENT_ANALYSIS:
        compare_df = sentiment_compare_pipeline(raw_df)
    else:
        print("[3] 감정 분석은 기본 실행에서 제외합니다. 실행하려면 RUN_SENTIMENT_ANALYSIS=1 로 설정하세요.")
        compare_df = pd.DataFrame(columns=[
            "title", "description", "blogger", "postdate", "link", "crawled_url",
            "body_length",
            "openai_model", "openai_api_error", "openai_label", "openai_reason", "openai_evidence", "openai_confidence", "openai_raw_output",
            "gemini_model", "gemini_api_error", "gemini_label", "gemini_reason", "gemini_evidence", "gemini_confidence", "gemini_raw_output",
            "ollama_model", "ollama_api_error", "ollama_label", "ollama_reason", "ollama_evidence", "ollama_confidence", "ollama_raw_output",
            "qwen_model", "qwen_api_error", "qwen_label", "qwen_reason", "qwen_evidence", "qwen_confidence", "qwen_raw_output"
        ])
        compare_df = sanitize_dataframe_for_csv(compare_df)
        compare_df.to_csv(OUTPUT_COMPARE_CSV, index=False, encoding="utf-8-sig")

    save_assignment_csv_results(raw_df, brand_df, mapping_df, compare_df)

    print("\n=== 완료 ===")
    print(f"- 과제 개요: {OUTPUT_OVERVIEW_CSV}")
    print(f"- 과제 핵심 요약: {OUTPUT_SUMMARY_CSV}")
    print(f"- 크롤링 원본: {OUTPUT_RAW_CSV}")
    print(f"- 쇼핑 기반 브랜드 원본: {OUTPUT_COLLECTED_BRANDS_CSV}")
    print(f"- 브랜드 후보군: {OUTPUT_BRAND_CSV}")
    print(f"- 게시글별 브랜드 맵핑: {OUTPUT_BRAND_MAPPING_CSV}")
    print(f"- 감정 분석 요약: {OUTPUT_SENTIMENT_SUMMARY_CSV}")
    print(f"- 모델 비교: {OUTPUT_COMPARE_CSV}")

    if RUN_SENTIMENT_ANALYSIS and not compare_df.empty:
        summary = build_sentiment_summary(compare_df)
        if not summary.empty:
            print("\n[라벨 분포 요약]")
            print(summary.to_string(index=False))