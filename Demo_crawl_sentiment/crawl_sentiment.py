import os
import requests
import pandas as pd
import time
import re
from datetime import datetime
from transformers import pipeline
import torch


# =========================
# 감정 분석 모델 초기화
# =========================

DEVICE = 0 if torch.cuda.is_available() else -1  # 0: GPU, -1: CPU

try:
    SENTIMENT_MODEL = pipeline(
        "text-classification",
        model="beomi/KcELECTRA-base-finetuned-nsmc",
        device=DEVICE
    )
    print(f"✓ 감정 분석 모델 로드 성공 (Device: {'GPU' if DEVICE == 0 else 'CPU'})\n")
    SENTIMENT_METHOD = "transformer_koelectra_nsmc"

except Exception as e:
    print(f"✗ 모델 로드 실패: {e}")
    SENTIMENT_MODEL = None
    SENTIMENT_METHOD = "rule_based_custom_korean_lexicon_v1"

# =========================
# 네이버 API 설정
# =========================
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "NzRzfyoeRbwh0r4Id_XR").strip()
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "pxLw89g_2N").strip()
if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
    print("⚠️ NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 비어 있습니다. API 호출이 실패합니다.\n")

NAVER_BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"

COLLECTION_DATE = "2025-01-15"
PLATFORM = "naver_blog"
SORT_OPTION = "date"  # date/sim

# =========================
# 카테고리 정의
# =========================
CATEGORIES = [
    {
        "category_name": "에너지-조명",
        "queries": {
            "ko": "수동발전 랜턴 핸드크랭크 랜턴 비상용 랜턴 자가발전 랜턴 손전등 비상용 손전등",
            "en": "hand crank emergency lantern self powered flashlight emergency light"
        }
    },
    {
        "category_name": "수면-이완",
        "queries": {
            "ko": "수면 이완 담요 수면개선 힐링 편안 포근한 담요",
            "en": "sleep relaxation blanket cozy blanket weighted blanket sleep aid"
        }
    },
]

# 단순 감정 사전(폴백용)
POSITIVE_STRONG = [
    "매우 만족", "정말 만족", "완전 만족", "강력 추천", "정말 좋다", "최고",
    "인생템", "대만족", "대박", "완전 좋아요",
    "highly recommend", "absolutely love", "super satisfied", "best ever"
]
POSITIVE = [
    "좋다", "좋아요", "좋았습니다", "괜찮다", "괜찮아요", "괜찮았습니다",
    "편하다", "편안하다", "도움", "도움이 된다", "도움이 됐다",
    "만족", "만족스럽다", "만족스러웠다", "유용하다", "유용했다",
    "힐링", "추천", "추천해요", "추천합니다", "개선", "따뜻하다",
    "쓸만하다", "쓸만해요", "무난하다", "무난해요",
    "밝기 좋다", "밝기가 좋다", "밝고 좋다", "밝아서 좋다",
    "충전 잘 된다", "충전이 잘 된다",
    "튼튼하다", "튼튼해요", "내구성 좋다", "내구성이 좋다",
    "가볍다", "가볍고 좋다", "휴대성 좋다", "휴대하기 좋다", "휴대성이 좋다",
    "good", "pretty good", "comfortable", "useful", "works well", "satisfied", "helpful"
]
NEGATIVE_STRONG = [
    "최악", "완전 별로", "다시는 안 산다", "돈 아깝다", "형편없다", "비추",
    "절대 비추천", "쓰레기", "후회막심",
    "terrible", "worst ever", "never buying again", "complete trash"
]
NEGATIVE = [
    "별로", "별로다", "별로였어요",
    "불편", "불편하다", "불편해요",
    "문제", "고장", "망가졌다",
    "실망", "실망했다", "실망스러웠다",
    "짜증", "짜증난다", "짜증났다",
    "피곤", "피곤하다",
    "악몽", "후회", "후회된다", "후회해요",
    "부정적", "아쉽다", "아쉬웠다", "아쉬움이 남는다",
    "밝기가 약하다", "밝기 약함", "생각보다 어둡다", "너무 어둡다",
    "금방 꺼진다", "배터리 빨리 닳는다", "배터리가 빨리 닳는다",
    "무겁다", "너무 무겁다", "손잡이 약하다", "내구성이 약하다", "내구성 떨어진다",
    "not good", "disappointed", "inconvenient", "annoying", "tired", "regret buying", "waste of money"
]

# =========================
# 텍스트 전처리
# =========================
def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.replace("<b>", "").replace("</b>", "")
    text = text.replace("&quot;", "'").replace("&amp;", "&")
    return text

def detect_language(query: str) -> str:
    has_korean = bool(re.search(r"[가-힣]", query))
    has_english = bool(re.search(r"[A-Za-z]", query))
    if has_korean and not has_english:
        return "ko"
    elif has_english and not has_korean:
        return "en"
    elif has_korean and has_english:
        return "mixed"
    return "unknown"

# =========================
# 감정 점수
# =========================
def compute_sentiment(text: str) -> int:
    if SENTIMENT_MODEL is not None:
        if not isinstance(text, str) or len(text.strip()) < 2:
            return 0
        try:
            text_truncated = text[:512]
            result = SENTIMENT_MODEL(text_truncated)
            label = result[0]["label"]
            score = result[0]["score"]
            if label == "POSITIVE":
                return 2 if score > 0.8 else 1
            else:
                return -2 if score > 0.8 else -1
        except Exception as e:
            print(f"감정 분석 오류: {e}")
            return 0

    if not isinstance(text, str):
        return 0
    score = 0
    for w in POSITIVE_STRONG:
        if w in text:
            score += 2 * text.count(w)
    for w in POSITIVE:
        if w in text:
            score += 1 * text.count(w)
    for w in NEGATIVE_STRONG:
        if w in text:
            score -= 2 * text.count(w)
    for w in NEGATIVE:
        if w in text:
            score -= 1 * text.count(w)
    return score

def interpret_sentiment(score: int, category: str) -> str:
    if category == "에너지-조명":
        target_desc = "에너지-조명(수동발전 랜턴 등) 제품에 대한 평가"
    elif category == "수면-이완":
        target_desc = "수면·이완(담요/수면 보조/힐링 관련) 제품에 대한 평가"
    else:
        target_desc = "해당 제품군에 대한 평가"

    if score >= 2:
        return f"전반적으로 강한 긍정 경향이 나타나며, {target_desc}에서 기능과 활용도에 대한 만족도가 높습니다."
    elif score == 1:
        return f"대체로 약한 긍정 경향이 나타나며, {target_desc}에서 기본적인 효용과 실용성이 인정됩니다."
    elif score == 0:
        return f"긍정과 부정이 혼재하거나 뚜렷한 감정 표현이 적어, {target_desc}에 대해 중립에 가까운 평가가 많습니다."
    elif score == -1:
        return f"대체로 약한 부정 경향이 나타나며, {target_desc}에서 일부 기능·편의성·성능에 대한 아쉬움이 보고됩니다."
    else:
        return f"전반적으로 부정적인 경향이 강하게 나타나며, {target_desc}에서 성능, 사용성, 만족도 측면의 불만이 두드러집니다."

# =========================
# 네이버 블로그 API 호출
# =========================
def naver_blog_search(query, display=100, start=1):
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return []

    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": SORT_OPTION,
    }

    try:
        res = requests.get(
            NAVER_BLOG_SEARCH_URL,
            headers=headers,
            params=params,
            timeout=8,
        )
    except requests.exceptions.RequestException as e:
        print("=== 네이버 API 요청 중 예외 발생 ===")
        print("예외 타입:", type(e).__name__)
        print("예외 메시지:", e)
        return []

    if res.status_code != 200:
        print("=== 네이버 API 호출 실패 ===")
        print("status_code:", res.status_code)
        try:
            print("response body:", res.text[:500])
        except Exception as e:
            print("response 출력 중 예외:", type(e).__name__, e)
        return []

    try:
        data = res.json()
    except ValueError as e:
        print("=== 응답 JSON 파싱 실패 ===")
        print("에러:", e)
        print("raw response (앞 500자):", res.text[:500])
        return []

    return data.get("items", [])

# =========================
# 카테고리별 크롤링
# =========================
def crawl_category(category_name, query, max_items=1000):
    collected = []
    seen_links = set()
    search_lang = detect_language(query)

    display = 100
    start = 1
    consecutive_empty = 0

    while len(collected) < max_items:
        items = naver_blog_search(query, display=display, start=start)

        if not items:
            consecutive_empty += 1
            print(f"[{category_name}] start={start}에서 결과 없음 ({consecutive_empty}회)")
            if consecutive_empty >= 3:
                print(f"[{category_name}] 더 이상 수집할 데이터가 없습니다.")
                break
            start += display
            time.sleep(0.3)
            continue

        consecutive_empty = 0

        for it in items:
            if len(collected) >= max_items:
                break

            title = clean_text(it.get("title", ""))
            desc = clean_text(it.get("description", ""))
            link = it.get("link", "")
            blogger = it.get("bloggername", "")
            date = it.get("postdate", "")  # ✅ YYYYMMDD

            if link and link in seen_links:
                continue
            if link:
                seen_links.add(link)

            merged = f"{title} {desc}"
            score = compute_sentiment(merged)
            interpretation = interpret_sentiment(score, category_name)

            collected.append({
                "category": category_name,
                "title": title,
                "description": desc,
                "blogger": blogger,
                "date": date,
                "link": link,
                "sentiment_score": score,
                "sentiment_interpretation": interpretation,
                "search_query": query,
                "search_lang": search_lang,
                "collected_at": COLLECTION_DATE,
                "platform": PLATFORM,
                "sort_option": SORT_OPTION,
                "sentiment_method": SENTIMENT_METHOD
            })

        print(f"[{category_name}] 진행 중... 수집된 데이터: {len(collected)}/{max_items}")
        start += display
        time.sleep(0.3)

    print(f"[{category_name}] — {len(collected)}개 수집 완료")
    return collected

# =========================
# 메인 실행 (카테고리별 파일 저장)
# =========================
def main():
    for cat in CATEGORIES:
        name = cat["category_name"]
        queries = cat.get("queries", {})

        for lang_tag, query in queries.items():
            if not query:
                continue

            rows = crawl_category(name, query, max_items=1000)
            df = pd.DataFrame(rows)
            print(f"[{name}/{lang_tag}] 원본 개수: {len(df)}")

            if df.empty:
                print(f"[{name}/{lang_tag}] ⚠️ 수집된 데이터가 0개라서 CSV 저장을 건너뜁니다. (API 키/쿼리 확인)\n")
                continue

            # ✅ 날짜 오름차순 정렬 (가장 오래된 글 → 가장 최신 글)
            # postdate(YYYYMMDD) -> datetime 변환 후 정렬 (안전)
            df["date_dt"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
            df = df.sort_values(by=["date_dt"], ascending=True).drop(columns=["date_dt"])

            filename = f"{name}_{lang_tag}_sentiment_sorted_by_date_asc_max1000.csv"
            df.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"저장 완료 → {filename}\n")

if __name__ == "__main__":
    main()