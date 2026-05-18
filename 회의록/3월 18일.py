import nest_asyncio
nest_asyncio.apply()
import re
import asyncio
import aiohttp
import pandas as pd
import time
from bs4 import BeautifulSoup
 
INPUT_FILE  = "step2_캐모마일.csv"
OUTPUT_FILE = "step3_캐모마일.csv"
LOG_FILE    = "log_step3_캐모마일.csv"
PRODUCT     = "캐모마일"
 
MIN_CONTENT_LENGTH      = 50
MAX_RETRIES             = 5    #타임아웃
REQUEST_TIMEOUT         = 15   
SHORT_CONTENT_THRESHOLD = 300  
MAX_CONCURRENCY         = 15   
 
# ── regex 패턴 (모듈 로드 시 1회만 컴파일) ────────────────────────────────
 
AD_REGEX = re.compile(
    r"협찬|체험단|제공받았습니다|제공 받았습니다|유료광고"
    r"|소정의 원고료|원고료를 받고|광고입니다|서포터즈"
    r"|앰배서더|무상으로 제공|무료로 제공"
)
 
EXCLUDE_REGEX = re.compile(
    r"마스크팩|스킨케어|세럼|에센스"
    r"|만드는 법|레시피|DIY"
    r"|디퓨저|향초|아로마"
)
 
TOPIC_REGEX = re.compile(r"캐모마일|카모마일|케모마일")
 
CAFE_REGEX = re.compile(r"스타벅스|커피빈|투썸|공차|카페베네")
MENU_REGEX = re.compile(r"라떼|프라푸치노|주문했|음료수")  # "음료","메뉴" 제거 — 일반 후기에도 나옴
 
FIRST_PERSON_REGEX = re.compile(
    r"마셨어요|마셔봤|마시고|마신 후|마셨더니|마셨는데"
    r"|마셔보니|마시니|마시는 중|마시고 있|마셔왔|마셔볼"
    r"|먹어봤|먹었는데|먹고|먹어보니|먹는 중|챙겨 ?먹"
    r"|저는|제가|저도|저한테|제 경우"
    r"|사봤|구매해서|구입해서|주문해서|우려서"
    r"|꾸준히 마|매일 마|한 달째|일주일째|계속 마"
    r"|요즘 마|요즘 캐모마일|빠졌는데|즐겨 마"
)
 
# ── HTML 파싱 셀렉터 리스트 (네이버 구조 변경 대응) ──────────────────────
HTML_SELECTORS = [
    ("div", {"class": "se-main-container"}),
    ("div", {"id": "postViewArea"}),
    ("div", {"class": "post-view"}),
]
 
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
 
 
# ── 텍스트 파싱 ───────────────────────────────────────────────────────────
def parse_content(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag, attrs in HTML_SELECTORS:
        el = soup.find(tag, attrs)
        if el:
            return el.get_text(separator=" ").strip()
    return ""
 
 
# ── 비동기 단일 URL 크롤링 ────────────────────────────────────────────────
async def fetch_blog_content(session: aiohttp.ClientSession, url: str) -> str:
    mobile_url = url.replace("blog.naver.com", "m.blog.naver.com")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with session.get(mobile_url, headers=HEADERS,
                                   timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as resp:
                html = await resp.text(errors="replace")
                text = parse_content(html)
                if text:
                    return text
                print(f"  본문 비어있음, 재시도 {attempt}/{MAX_RETRIES}: {url[:50]}")
        except Exception as e:
            print(f"  오류 ({attempt}/{MAX_RETRIES}): {e} | {url[:50]}")
        await asyncio.sleep(0.5 * attempt)
    return ""
 
 
# ── 필터링 ───────────────────────────────────────────────────────────────
def apply_filters(row: dict, content: str) -> tuple[dict | None, str]:
    """통과하면 (완성된 row dict, "통과"), 제거면 (None, 사유)
    역할: 광고 + 명백히 무관한 글만 제거. 나머지는 Ollama에게 넘김.
    """
    # 1. 광고
    if AD_REGEX.search(content):
        return None, "광고제거"
 
    # 2. 본문 너무 짧음
    if len(content) < MIN_CONTENT_LENGTH:
        return None, "짧은본문"
 
    # 3. 캐모마일 언급 없음
    if not TOPIC_REGEX.search(content):
        return None, "주제무관"
 
    # 4. 화장품·방향제·만들기
    if EXCLUDE_REGEX.search(content):
        return None, "무관주제"
 
    # 5. 카페 메뉴 후기 — 카페+메뉴 키워드 둘 다 있을 때만 제거
    if CAFE_REGEX.search(content) and MENU_REGEX.search(content):
        return None, "카페맛후기"
 
    # 6. 정보성 글 제거
    # 300자 미만 짧은 글은 완화 (짧은 개인 후기가 1인칭 없이도 많음)
    if len(content) >= SHORT_CONTENT_THRESHOLD:
        if not FIRST_PERSON_REGEX.search(content):
            return None, "정보성글"
 
    # 통과 — 감정/효과/브랜드 판단은 Ollama(step4)에게
    result            = dict(row)
    result["content"] = content[:3000]
    return result, "통과"
 
 
# ── 세마포어로 동시 요청 수 제한 ─────────────────────────────────────────
async def process_row(sem: asyncio.Semaphore, session: aiohttp.ClientSession,
                      idx: int, total: int, row: dict) -> tuple[dict | None, str, dict | None]:
    async with sem:
        print(f"크롤링 {idx}/{total}: {str(row['url'])[:60]}")
        content = await fetch_blog_content(session, row["url"])
        if not content:
            print(f"  → 크롤링 실패, 제외")
            removed = dict(row)
            removed["제거사유"] = "크롤링실패"
            removed["content"]  = ""
            return None, "크롤링실패", removed
 
        result, reason = apply_filters(row, content)
        print(f"  → {reason}")
 
        if result is None:
            # 제거된 경우 — 사유 + 본문 앞 200자 저장 (나중에 검토용)
            removed = dict(row)
            removed["제거사유"] = reason
            removed["content"]  = content[:200]
            return None, reason, removed
 
        return result, reason, None
 
 
# ── 전체 비동기 크롤링 ────────────────────────────────────────────────────
async def crawl_all_async(df: pd.DataFrame):
    stat    = {"크롤링실패": 0, "광고제거": 0, "짧은본문": 0,
               "주제무관": 0, "무관주제": 0, "카페맛후기": 0,
               "정보성글": 0, "통과": 0}
    results = []
    removed = []   # 제거된 항목 저장
    total   = len(df)
    rows    = df.to_dict("records")
 
    concurrency = min(MAX_CONCURRENCY, total)
    sem         = asyncio.Semaphore(concurrency)
 
    connector = aiohttp.TCPConnector(limit=concurrency, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            process_row(sem, session, idx, total, row)
            for idx, row in enumerate(rows, 1)
        ]
        for coro in asyncio.as_completed(tasks):
            result, reason, removed_row = await coro
            stat[reason] += 1
            if result:
                results.append(result)
            elif removed_row:
                removed.append(removed_row)
 
    return pd.DataFrame(results), pd.DataFrame(removed), stat
 
 
# ── 진입점 ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print(f"STEP 3 (고속): {PRODUCT} 본문 크롤링 + 2차 필터")
    print(f"동시 요청 수: 최대 {MAX_CONCURRENCY} | 타임아웃: {REQUEST_TIMEOUT}s | 재시도: {MAX_RETRIES}회")
    print("=" * 50)
 
    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
 
    # URL 중복 제거 안전장치 (step2에서 했더라도 한 번 더)
    before = len(df)
    df = df.drop_duplicates(subset="url").reset_index(drop=True)
    if before != len(df):
        print(f"중복 URL {before - len(df)}개 제거")
 
    print(f"입력: {len(df)}개\n")
 
    t0 = time.time()
    df_crawled, df_removed, stat = asyncio.run(crawl_all_async(df))
    elapsed = time.time() - t0
 
    df_crawled.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    df_removed.to_csv(f"step3_제거목록_{PRODUCT}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([stat]).to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
 
    print(f"\n✅ 저장 완료: {OUTPUT_FILE} ({len(df_crawled)}개)")
    print(f"✅ 제거 목록: step3_제거목록_{PRODUCT}.csv ({len(df_removed)}개)")
    print(f"✅ 로그 저장: {LOG_FILE}")
    print(f"⏱  소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
    print("\n[필터링 통계]")
    for k, v in stat.items():
        print(f"  {k}: {v}개")