# =========================================================
# 아로마 오일 블로그/쇼핑 브랜드 수집 및 감정 분석 비교
# - 네이버 쇼핑 브랜드 후보군 수집
# - 네이버 블로그 수집 및 본문 크롤링
# - 브랜드 후보군 맵핑 및 동적 확장
# - 감정 분석 비교 (옵션)
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
# 0. 환경 변수 및 상수
# =========================================================
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
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions").strip()

NAVER_BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"
NAVER_SHOP_SEARCH_URL = "https://openapi.naver.com/v1/search/shop.json"

OUTPUT_RAW_CSV = "aroma_oil_raw_crawled.csv"
OUTPUT_COMPARE_CSV = "aroma_oil_sentiment_compare.csv"
OUTPUT_BRAND_CSV = "aroma_oil_brand_candidates.csv"
OUTPUT_BRAND_MAPPING_CSV = "aroma_oil_brand_mapping.csv"
OUTPUT_OVERVIEW_CSV = "aroma_oil_assignment_overview.csv"
OUTPUT_SUMMARY_CSV = "aroma_oil_assignment_summary.csv"
OUTPUT_SENTIMENT_SUMMARY_CSV = "aroma_oil_sentiment_summary.csv"
OUTPUT_COLLECTED_BRANDS_CSV = "aroma_oil_collected_shopping_brands.csv"

SEARCH_QUERY = "아로마 오일"
MAX_SEARCH_ITEMS = 1000
REQUEST_SLEEP = 0.25
CRAWL_TIMEOUT = 10
RUN_SENTIMENT_ANALYSIS = read_env("RUN_SENTIMENT_ANALYSIS") == "1"
SENTIMENT_MAX_ITEMS = int(read_env("SENTIMENT_MAX_ITEMS") or "50")

# 네이버 쇼핑 브랜드 후보군 수집용 쿼리
SHOPPING_BRAND_QUERIES = [
    "아로마 오일", "에센셜 오일", "에센셜오일", "아로마에센셜", "아로마오일", "에센셜오일 세트"
]
# 쇼핑 브랜드명 후보에서 제외할 단어
BRAND_STOPWORDS = [
    "정품", "공식", "본사", "국내", "병", "ml", "세트", "세트형", "아로마", "에센셜", "오일", "향", "오일세트", "아로마오일", "에센셜오일", "블렌드", "향오일", "향기"
]

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

def normalize_for_match(text: str) -> str:
    text = clean_text(text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text

def find_keywords_in_text(text: str, keyword_map: Dict[str, List[str]]) -> Dict[str, List[str]]:
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
    parts = [
        str(row.get("title", "")),
        str(row.get("description", "")),
        str(row.get("blogger", "")),
        str(row.get("body_text", "")),
    ]
    return " ".join(parts)

# =========================================================
# 2. 네이버 쇼핑 브랜드 후보군 수집
# =========================================================
def naver_shopping_search(query: str, display: int = 100, start: int = 1) -> List[dict]:
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
        res = requests.get(NAVER_SHOP_SEARCH_URL, headers=headers, params=params, timeout=CRAWL_TIMEOUT)
        res.raise_for_status()
        data = res.json()
        return data.get("items", [])
    except Exception as e:
        print(f"쇼핑 API 오류: {e}")
        return []

def collect_brand_candidates_from_shopping(queries: List[str], max_items_per_query: int = 100) -> pd.DataFrame:
    all_brands = []
    for query in queries:
        print(f"[쇼핑] 쿼리: {query}")
        seen = set()
        start = 1
        while start <= max_items_per_query:
            items = naver_shopping_search(query, display=100, start=start)
            if not items:
                break
            for it in items:
                title = clean_text(it.get("title", ""))
                mall_name = clean_text(it.get("mallName", ""))
                maker = clean_text(it.get("maker", ""))
                brand = clean_text(it.get("brand", ""))
                for candidate in [brand, maker, mall_name]:
                    norm = normalize_for_match(candidate)
                    if norm and norm not in seen and not any(sw in norm for sw in BRAND_STOPWORDS):
                        seen.add(norm)
                        all_brands.append({
                            "query": query,
                            "brand_candidate": candidate,
                            "from_field": "brand" if candidate == brand else ("maker" if candidate == maker else "mallName"),
                            "title_sample": title,
                        })
            start += 100
            time.sleep(REQUEST_SLEEP)
    df = pd.DataFrame(all_brands)
    if not df.empty:
        df = df.drop_duplicates(subset=["brand_candidate"])
    df = sanitize_dataframe_for_csv(df)
    df.to_csv(OUTPUT_COLLECTED_BRANDS_CSV, index=False, encoding="utf-8-sig")
    print(f"[쇼핑] 브랜드 후보군 저장 완료: {OUTPUT_COLLECTED_BRANDS_CSV} ({len(df)})")
    return df

def build_dynamic_brand_keyword_map(brand_df: pd.DataFrame, min_len: int = 2) -> Dict[str, List[str]]:
    brand_map = {}
    if brand_df.empty:
        return brand_map
    for _, row in brand_df.iterrows():
        candidate = str(row["brand_candidate"]).strip()
        if not candidate or len(candidate) < min_len:
            continue
        if candidate not in brand_map:
            brand_map[candidate] = [candidate]
    return brand_map

def merge_brand_keyword_maps(static_map: Dict[str, List[str]], dynamic_map: Dict[str, List[str]]) -> Dict[str, List[str]]:
    merged = {**static_map}
    for k, v in dynamic_map.items():
        if k in merged:
            merged[k] = list(sorted(set(merged[k] + v)))
        else:
            merged[k] = v
    return merged

# =========================================================
# 3. 네이버 블로그 검색/크롤링 (기존과 동일)
# =========================================================
def naver_blog_search(query: str, display: int = 100, start: int = 1) -> List[dict]:
    client_id, client_secret = get_naver_credentials()
    if not client_id or not client_secret:
        print("⚠️ NAVER API 키가 설정되지 않았습니다. 크롤링을 건너뜁니다.")
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
    res = requests.get(NAVER_BLOG_SEARCH_URL, headers=headers, params=params, timeout=CRAWL_TIMEOUT)
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

def normalize_blog_url(url: str) -> str:
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
    mobile_url = normalize_blog_url(url)
    html_text = fetch_html(mobile_url)
    if not html_text:
        return {"final_url": mobile_url, "content": "", "status": "fail"}
    soup = BeautifulSoup(html_text, "html.parser")
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
# 4. 브랜드 후보군 사전/상품군 키워드
# =========================================================
BRAND_KEYWORD_MAP = {
    "도테라": ["도테라", "doTERRA", "doterra", "도테라 오일"],
    "영리빙": ["영리빙", "Young Living", "youngliving", "영리빙 오일"],
    "나우푸드": ["나우푸드", "NOW Foods", "now foods", "now essential oil", "NOW 에센셜", "now 에센셜"],
    "프라나롬": ["프라나롬", "Pranarom", "pranarom"],
    "아로마티카": ["아로마티카", "Aromatica", "aromatica"],
    "허브테라피": ["허브테라피", "Herb Therapy", "herb therapy"],
    "생활도감": ["생활도감"],
    "무인양품": ["무인양품", "MUJI", "muji"],
    "이솝": ["이솝", "Aesop", "aesop"],
    "록시땅": ["록시땅", "L'OCCITANE", "loccitane", "록시땅 아로마"],
    "더바디샵": ["더바디샵", "The Body Shop", "body shop"],
    "센틀리에": ["센틀리에", "Scentlier", "scentlier"],
    "쿤달": ["쿤달", "Kundal", "kundal"],
    "아로마랩": ["아로마랩", "Aromalab", "aromalab"],
    "아로마용": ["아로마용"],
    "앳네이처": ["앳네이처", "At Nature", "atnature", "at nature"],
    "네이처스웨이": ["네이처스웨이", "Nature's Way", "natures way", "nature's way"],
    "플랜트테라피": ["플랜트테라피", "Plant Therapy", "plant therapy"],
    "에센허브": ["에센허브", "essenHERB", "essenherb"],
    "허브누리": ["허브누리"],
}
PRODUCT_CATEGORY_KEYWORDS = {
    "라벤더 계열": ["라벤더", "lavender"],
    "페퍼민트 계열": ["페퍼민트", "peppermint"],
    "티트리 계열": ["티트리", "tea tree"],
    "유칼립투스 계열": ["유칼립투스", "eucalyptus"],
    "레몬 계열": ["레몬", "lemon"],
    "오렌지 계열": ["오렌지", "orange", "스위트오렌지"],
    "로즈마리 계열": ["로즈마리", "rosemary"],
    "일랑일랑 계열": ["일랑일랑", "ylang"],
    "블렌딩 오일 계열": ["블렌딩", "블렌드", "blend", "릴렉스", "수면", "숙면", "스트레스"],
}

# =========================================================
# 5. 감정 분석 프롬프트/파싱/모델 호출기
# =========================================================
def build_sentiment_prompt(title: str, description: str, body_text: str) -> str:
    body_text = truncate_text(body_text, 5000)

    return f"""
너는 제품 후기 텍스트 분석가다.
아래 텍스트는 '아로마 오일'과 관련된 블로그 글이다.

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
- 제품/사용경험/만족도/불만/활용성/구매의사/효용성 중심
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
    모델이 JSON 외 텍스트를 섞어도 최대한 복구합니다.
    """
    if not text:
        return {
            "label": "error",
            "reason": "empty response",
            "evidence": [],
            "confidence": 0.0,
        }

    text = text.strip()
    text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

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
        raw_text = safe_get(data, ["choices", 0, "message", "content"], "")
        return {"provider": "openai", "model": model, "raw_text": raw_text.strip(), "error": ""}
    except Exception as e:
        return {"provider": "openai", "model": model, "raw_text": "", "error": str(e)}


def call_gemini(prompt: str, model: str) -> dict:
    if not GEMINI_API_KEY:
        return {"provider": "gemini", "model": model, "raw_text": "", "error": "GEMINI_API_KEY missing"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0},
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        parts = safe_get(data, ["candidates", 0, "content", "parts"], [])
        texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")]
        raw_text = "\n".join(texts).strip()
        return {"provider": "gemini", "model": model, "raw_text": raw_text, "error": ""}
    except Exception as e:
        return {"provider": "gemini", "model": model, "raw_text": "", "error": str(e)}


def call_ollama(prompt: str, model: str) -> dict:
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }

    try:
        res = requests.post(url, json=payload, timeout=120)
        res.raise_for_status()
        data = res.json()
        return {"provider": "ollama", "model": model, "raw_text": data.get("response", "").strip(), "error": ""}
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
        "messages": [{"role": "user", "content": prompt}],
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
    return [
        call_openai(prompt, OPENAI_MODEL),
        call_gemini(prompt, GEMINI_MODEL),
        call_ollama(prompt, OLLAMA_MODEL),
        call_qwen(prompt, QWEN_MODEL),
    ]


def sentiment_compare_pipeline(raw_df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "title", "description", "blogger", "postdate", "link", "crawled_url", "body_length",
        "openai_model", "openai_api_error", "openai_label", "openai_reason", "openai_evidence", "openai_confidence", "openai_raw_output",
        "gemini_model", "gemini_api_error", "gemini_label", "gemini_reason", "gemini_evidence", "gemini_confidence", "gemini_raw_output",
        "ollama_model", "ollama_api_error", "ollama_label", "ollama_reason", "ollama_evidence", "ollama_confidence", "ollama_raw_output",
        "qwen_model", "qwen_api_error", "qwen_label", "qwen_reason", "qwen_evidence", "qwen_confidence", "qwen_raw_output",
    ]

    if raw_df.empty or not {"crawl_status", "body_length"}.issubset(raw_df.columns):
        print("[3] 감정 분석 대상이 없습니다. 빈 결과 파일을 저장합니다.")
        compare_df = pd.DataFrame(columns=columns)
        compare_df = sanitize_dataframe_for_csv(compare_df)
        compare_df.to_csv(OUTPUT_COMPARE_CSV, index=False, encoding="utf-8-sig")
        return compare_df

    usable_df = raw_df[
        (raw_df["crawl_status"] == "ok") &
        (raw_df["body_length"] >= 80)
    ].copy()

    if SENTIMENT_MAX_ITEMS > 0:
        usable_df = usable_df.head(SENTIMENT_MAX_ITEMS)

    print(f"[3] 감정 분석 대상: {len(usable_df)}개")

    compare_rows = []

    for _, row in usable_df.iterrows():
        print(f"[4] 모델 비교 중: {str(row['title'])[:40]}")

        prompt = build_sentiment_prompt(
            title=row["title"],
            description=row["description"],
            body_text=row["body_text"],
        )

        model_results = run_all_models(prompt)

        grouped = {
            provider: {
                "model": "", "api_error": "", "label": "", "reason": "",
                "evidence": "[]", "confidence": 0.0, "raw_output": ""
            }
            for provider in ["openai", "gemini", "ollama", "qwen"]
        }

        for result in model_results:
            parsed = parse_model_json(result["raw_text"])
            provider = result["provider"]

            grouped[provider] = {
                "model": result["model"],
                "api_error": result["error"],
                "label": parsed["label"],
                "reason": parsed["reason"],
                "evidence": json.dumps(parsed["evidence"], ensure_ascii=False),
                "confidence": parsed["confidence"],
                "raw_output": result["raw_text"],
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
# 6. 브랜드 후보군 추출/맵핑 (동적 브랜드 후보군 확장)
# =========================================================
def brand_candidate_pipeline(raw_df: pd.DataFrame, brand_keyword_map: Optional[Dict[str, List[str]]] = None):
    """
    브랜드 후보군 생성 파이프라인
    - brand_keyword_map이 주어지면 동적 맵을 사용, 아니면 기본 사전만 사용
    """
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

    # 브랜드 후보군 맵
    if brand_keyword_map is None:
        brand_keyword_map = BRAND_KEYWORD_MAP

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
# 7. 과제 제출용 CSV 결과 생성
# =========================================================
def build_sentiment_summary(compare_df: pd.DataFrame) -> pd.DataFrame:
    """
    모델별 감정 라벨 분포를 CSV 요약 파일용 DataFrame으로 만듭니다.
    감정 분석을 실행하지 않은 경우 빈 요약 파일을 생성합니다.
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


def build_assignment_overview(
    raw_df: pd.DataFrame,
    brand_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
    compare_df: pd.DataFrame,
    shopping_brand_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
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

    shopping_brand_count = 0
    if shopping_brand_df is not None and not shopping_brand_df.empty:
        shopping_brand_count = len(shopping_brand_df)

    rows = [
        {"항목": "검색 키워드", "값": SEARCH_QUERY, "설명": "Naver Blog Search API에 사용한 검색어"},
        {"항목": "최대 블로그 수집 후보 수", "값": MAX_SEARCH_ITEMS, "설명": "Naver Blog Search API start 범위 기준 최대 후보 수"},
        {"항목": "쇼핑 기반 브랜드 후보 수", "값": shopping_brand_count, "설명": "Naver Shopping API의 brand/maker/mallName 기반 후보 수"},
        {"항목": "수집된 블로그 게시글 수", "값": len(raw_df), "설명": "중복 링크 제거 후 수집된 블로그 후보 수"},
        {"항목": "본문 크롤링 성공 수", "값": crawled_ok_count, "설명": "crawl_status가 ok인 게시글 수"},
        {"항목": "직접 브랜드 후보 수", "값": direct_brand_count, "설명": "수동 브랜드 사전과 쇼핑 API 기반 브랜드 후보군에서 직접 매칭된 후보 수"},
        {"항목": "상품군 맵핑 후보 수", "값": product_mapping_count, "설명": "브랜드 직접 추출이 어려울 때 상품군으로 보조 맵핑한 후보 수"},
        {"항목": "브랜드/상품군 미매칭 게시글 수", "값": no_match_count, "설명": "브랜드와 상품군 모두 매칭되지 않은 게시글 수"},
        {"항목": "감정 분석 실행 여부", "값": "실행" if RUN_SENTIMENT_ANALYSIS else "미실행", "설명": "RUN_SENTIMENT_ANALYSIS=1일 때만 감정 분석 실행"},
        {"항목": "감정 분석 대상 수", "값": len(compare_df), "설명": "감정 분석 결과 파일의 행 수"},
    ]
    return pd.DataFrame(rows)


def build_assignment_summary(
    raw_df: pd.DataFrame,
    brand_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
    compare_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    과제 제출용 핵심 요약 CSV를 생성합니다.
    """
    summary_rows = []

    crawled_ok_count = 0
    if not raw_df.empty and "crawl_status" in raw_df.columns:
        crawled_ok_count = int((raw_df["crawl_status"] == "ok").sum())

    avg_body_length = 0
    if not raw_df.empty and "body_length" in raw_df.columns:
        avg_body_length = round(float(raw_df["body_length"].mean()), 2)

    summary_rows.extend([
        {"구분": "수집 요약", "항목": "수집 글 수", "게시글 수": len(raw_df), "비고": "중복 링크 제거 후 수집된 게시글 수"},
        {"구분": "수집 요약", "항목": "본문 크롤링 성공", "게시글 수": crawled_ok_count, "비고": "crawl_status가 ok인 게시글 수"},
        {"구분": "수집 요약", "항목": "평균 본문 길이", "게시글 수": avg_body_length, "비고": "body_length 평균값"},
    ])

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

    mapping_counts = pd.Series(dtype="int64")
    if not mapping_df.empty and "mapping_note" in mapping_df.columns:
        mapping_counts = mapping_df["mapping_note"].value_counts()

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

    summary_rows.append({
        "구분": "감정 분석",
        "항목": "감정 분석 대상 수",
        "게시글 수": len(compare_df),
        "비고": "기본 설정에서는 감정 분석 미실행",
    })

    return pd.DataFrame(summary_rows, columns=["구분", "항목", "게시글 수", "비고"])


def save_assignment_csv_results(
    raw_df: pd.DataFrame,
    brand_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
    compare_df: pd.DataFrame,
    shopping_brand_df: Optional[pd.DataFrame] = None,
):
    """
    과제 제출용 결과 CSV 파일을 저장합니다.
    """
    overview_df = build_assignment_overview(raw_df, brand_df, mapping_df, compare_df, shopping_brand_df)
    assignment_summary_df = build_assignment_summary(raw_df, brand_df, mapping_df, compare_df)
    sentiment_summary_df = build_sentiment_summary(compare_df)

    output_map = {
        OUTPUT_OVERVIEW_CSV: overview_df,
        OUTPUT_SUMMARY_CSV: assignment_summary_df,
        OUTPUT_BRAND_CSV: brand_df,
        OUTPUT_BRAND_MAPPING_CSV: mapping_df,
        OUTPUT_SENTIMENT_SUMMARY_CSV: sentiment_summary_df,
        OUTPUT_COMPARE_CSV: compare_df,
        OUTPUT_RAW_CSV: raw_df,
    }

    if shopping_brand_df is not None:
        output_map[OUTPUT_COLLECTED_BRANDS_CSV] = shopping_brand_df

    for path, df in output_map.items():
        df = sanitize_dataframe_for_csv(df)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"[6] CSV 저장 완료: {path}")

# =========================================================
# 7. 실행
# =========================================================
if __name__ == "__main__":
    # 1. 네이버 쇼핑에서 브랜드 후보군 수집
    shopping_brand_df = collect_brand_candidates_from_shopping(SHOPPING_BRAND_QUERIES, max_items_per_query=200)
    dynamic_brand_map = build_dynamic_brand_keyword_map(shopping_brand_df)
    merged_brand_map = merge_brand_keyword_maps(BRAND_KEYWORD_MAP, dynamic_brand_map)

    # 2. 네이버 블로그 크롤링
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

    # 3. 브랜드 후보군/맵핑 (동적 맵 사용)
    brand_df, mapping_df = brand_candidate_pipeline(raw_df, brand_keyword_map=merged_brand_map)

    # 4. 감정 분석 (옵션)
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
        compare_df.to_csv(OUTPUT_COMPARE_CSV, index=False, encoding="utf-8-sig")

    # 5. 과제 제출용 CSV 저장
    save_assignment_csv_results(raw_df, brand_df, mapping_df, compare_df, shopping_brand_df)

    print("\n=== 완료 ===")
    print(f"- 과제 개요: {OUTPUT_OVERVIEW_CSV}")
    print(f"- 과제 핵심 요약: {OUTPUT_SUMMARY_CSV}")
    print(f"- 크롤링 원본: {OUTPUT_RAW_CSV}")
    print(f"- 브랜드 후보군: {OUTPUT_BRAND_CSV}")
    print(f"- 게시글별 브랜드 맵핑: {OUTPUT_BRAND_MAPPING_CSV}")
    print(f"- 감정 분석 요약: {OUTPUT_SENTIMENT_SUMMARY_CSV}")
    print(f"- 모델 비교: {OUTPUT_COMPARE_CSV}")
    print(f"- 쇼핑 브랜드 후보군: {OUTPUT_COLLECTED_BRANDS_CSV}")