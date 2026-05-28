"""
collect_bot_data.py  — 봇 데이터 수집기 (CAPTCHA 자동 풀이 포함)
사용법: python collect_bot_data.py
저장:   dataset/bot/session_YYYYMMDD_HHMMSS.json
"""

import json
import time
import random
import re
import string
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

from mouse_tracker import MouseTracker
from selenium_actions import random_delay, click_element, drag_element
from pymongo import MongoClient

# ── 로깅 설정 ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("selenium.webdriver").setLevel(logging.WARNING)
logging.getLogger("selenium.webdriver.remote").setLevel(logging.WARNING)

# ── 설정 ──────────────────────────────────────────────────
URL         = "http://localhost:3000"
OUTPUT_DIR  = Path("dataset/bot")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── MongoDB 설정 ──────────────────────────────────────────
MONGO_URI  = "mongodb://localhost:27017"
MONGO_DB   = "captcha_data"
MONGO_COL  = "bot_events"

# 테스트 계정
BOT_EMAIL    = "bot123@bot.com"
BOT_PASSWORD = "bot123"

# 대기 시간 (초)
PAGE_LOAD_TIMEOUT    = 20
ELEMENT_WAIT_TIMEOUT = 15

# ── 한글→영어 역매핑 (CAPTCHA 키보드 문제 풀이용) ──────────
KR_TO_EN = {
    'ㅂ': 'q', 'ㅈ': 'w', 'ㄷ': 'e', 'ㄱ': 'r', 'ㅅ': 't',
    'ㅛ': 'y', 'ㅕ': 'u', 'ㅑ': 'i', 'ㅐ': 'o', 'ㅔ': 'p',
    'ㅁ': 'a', 'ㄴ': 's', 'ㅇ': 'd', 'ㄹ': 'f', 'ㅎ': 'g',
    'ㅗ': 'h', 'ㅓ': 'j', 'ㅏ': 'k', 'ㅣ': 'l',
    'ㅋ': 'z', 'ㅌ': 'x', 'ㅊ': 'c', 'ㅍ': 'v', 'ㅠ': 'b',
    'ㅜ': 'n', 'ㅡ': 'm',
    'ㅃ': 'Q', 'ㅉ': 'W', 'ㄸ': 'E', 'ㄲ': 'R', 'ㅆ': 'T',
    'ㅒ': 'O', 'ㅖ': 'P',
}

# ── 기록 저장소 ───────────────────────────────────────────
session_id: str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
start_time: float = time.time()
events: List[Dict[str, Any]] = []


def record(event_type: str, x: Optional[int] = None, y: Optional[int] = None,
           extra: Optional[Dict[str, Any]] = None) -> None:
    """이벤트 하나를 타임스탬프와 함께 기록."""
    entry: Dict[str, Any] = {
        "seq":        len(events),
        "type":       event_type,
        "timestamp":  round(time.time(), 3),
        "elapsed_ms": round((time.time() - start_time) * 1000),
    }
    if x is not None:
        entry["x"] = x
    if y is not None:
        entry["y"] = y
    if extra:
        entry["extra"] = extra

    events.append(entry)
    coord_str = f" ({x},{y})" if x is not None and y is not None else ""
    logger.debug(f"  [EVENT {entry['seq']:03d}] {event_type}{coord_str}")


def enrich_events(events):
    """기존 이벤트에 행동 분석 feature를 추가한 사본을 반환한다."""
    enriched = []
    prev = None
    prev_vel = 0.0
    for e in events:
        r = dict(e)
        if prev is not None and "x" in e and "y" in e and "x" in prev and "y" in prev:
            dt = e["timestamp"] - prev["timestamp"]
            dx = e["x"] - prev["x"]
            dy = e["y"] - prev["y"]
            dist = math.hypot(dx, dy)
            vel  = dist / dt if dt > 0 else 0.0
            acc  = (vel - prev_vel) / dt if dt > 0 else 0.0

            r["delta_x"]      = dx
            r["delta_y"]      = dy
            r["distance"]     = round(dist, 2)
            r["idle_time"]    = round(dt * 1000)
            r["velocity"]     = round(vel, 2)
            r["acceleration"] = round(acc, 2)
            prev_vel = vel
            prev = e
        else:
            r["delta_x"] = r["delta_y"] = 0
            r["distance"]     = 0.0
            r["idle_time"]    = 0
            r["velocity"]     = 0.0
            r["acceleration"] = 0.0
            if "x" in e and "y" in e:
                prev = e
        enriched.append(r)
    return enriched


def wait_and_find(driver, by, value, timeout=ELEMENT_WAIT_TIMEOUT,
                  condition="visible", step_name=""):
    """요소를 대기하며 찾는 헬퍼. Timeout 시 상세 진단 로그 출력."""
    logger.debug(f"    대기중: {step_name} (by={by}, value='{value}', {timeout}s)")

    wait = WebDriverWait(driver, timeout)

    try:
        if condition == "clickable":
            el = wait.until(EC.element_to_be_clickable((by, value)))
        elif condition == "present":
            el = wait.until(EC.presence_of_element_located((by, value)))
        else:
            el = wait.until(EC.visibility_of_element_located((by, value)))

        logger.debug(f"    발견: {step_name} -> <{el.tag_name}> {el.size}")
        return el

    except TimeoutException:
        logger.error(f"{'='*60}")
        logger.error(f"  TIMEOUT: {step_name}")
        logger.error(f"  Selector: by={by}, value='{value}'")
        logger.error(f"  현재 URL: {driver.current_url}")
        logger.error(f"  페이지 타이틀: {driver.title}")
        try:
            body = driver.find_element(By.TAG_NAME, "body").text[:300]
            logger.error(f"  Body 텍스트: {body}")
        except Exception:
            pass
        logger.error(f"{'='*60}")
        raise


def get_center(el):
    """요소의 중심 좌표 반환."""
    return (
        int(el.location["x"] + el.size.get("width", 0) // 2),
        int(el.location["y"] + el.size.get("height", 0) // 2),
    )


# ───────────────────────────────────────────────────────────
# CAPTCHA 자동 풀이 함수들
# ───────────────────────────────────────────────────────────

def solve_bookshelf(driver) -> Optional[str]:
    """
    책장 문제 풀이.
    DOM에서 각 책의 inline height와 숫자를 읽어 높이 오름차순으로 정렬.
    """
    try:
        books = driver.find_elements(By.CSS_SELECTOR, '[class*="book_"], [class*="book "]')
        if not books:
            bookshelf = driver.find_element(By.CSS_SELECTOR, '[class*="bookshelf"]')
            books = bookshelf.find_elements(By.XPATH, './/div[.//span]')

        if not books:
            logger.warning("  책 요소를 찾지 못했습니다.")
            return None

        book_data = []
        for book_el in books:
            style = book_el.get_attribute("style") or ""
            height_match = re.search(r'height:\s*(\d+)px', style)
            if not height_match:
                continue

            height = int(height_match.group(1))

            try:
                number_span = book_el.find_element(By.CSS_SELECTOR, 'span')
                number = number_span.text.strip()
                if number.isdigit():
                    book_data.append((height, int(number)))
            except NoSuchElementException:
                continue

        if not book_data:
            logger.warning("  책 데이터를 파싱하지 못했습니다.")
            return None

        book_data.sort(key=lambda x: x[0])
        answer = ' '.join(str(num) for _, num in book_data)

        logger.info(f"  책장 풀이 완료: {book_data} -> 정답: '{answer}'")
        return answer

    except Exception as e:
        logger.error(f"  책장 풀이 실패: {e}")
        return None


def solve_keyboard(driver) -> Optional[str]:
    """
    한영 변환 문제 풀이.
    DOM에서 한글 자모 텍스트를 읽어 영어로 변환.
    """
    try:
        korean_el = driver.find_element(By.CSS_SELECTOR, '[class*="koreanText"]')
        korean_text = korean_el.text.strip()

        if not korean_text:
            logger.warning("  한글 텍스트가 비어있습니다.")
            return None

        answer = ''
        for ch in korean_text:
            if ch in KR_TO_EN:
                answer += KR_TO_EN[ch]

        logger.info(f"  키보드 풀이 완료: '{korean_text}' -> 정답: '{answer}'")
        return answer if answer else None

    except NoSuchElementException:
        logger.error("  한글 텍스트 요소를 찾지 못했습니다.")
        return None
    except Exception as e:
        logger.error(f"  키보드 풀이 실패: {e}")
        return None


def solve_symbol(driver) -> Optional[str]:
    """
    기호 세기 문제 풀이.
    DOM에서 타겟 기호와 전체 셀을 읽어 개수를 센다.
    """
    try:
        target_el = driver.find_element(By.CSS_SELECTOR, '[class*="targetSymbol"]')
        target_symbol = target_el.text.strip()

        cells = driver.find_elements(By.CSS_SELECTOR, '[class*="symbolCell"]')
        if not cells:
            logger.warning("  기호 셀을 찾지 못했습니다.")
            return None

        count = 0
        for cell in cells:
            cell_text = cell.text.strip()
            if cell_text == target_symbol:
                count += 1

        answer = str(count)
        logger.info(f"  기호 풀이 완료: '{target_symbol}' x {count}개 -> 정답: '{answer}'")
        return answer

    except NoSuchElementException:
        logger.error("  타겟 기호 요소를 찾지 못했습니다.")
        return None
    except Exception as e:
        logger.error(f"  기호 풀이 실패: {e}")
        return None


def detect_and_solve_captcha(driver) -> Optional[str]:
    """
    모달 제목(h2)을 읽어 CAPTCHA 유형을 판별하고 자동 풀이.
    """
    try:
        title_el = driver.find_element(By.CSS_SELECTOR, '[class*="modalTitle"]')
        title_text = title_el.text.strip()
        logger.info(f"  CAPTCHA 유형 감지: '{title_text}'")
    except NoSuchElementException:
        logger.warning("  모달 제목을 찾지 못함 - 기본으로 책장 시도")
        title_text = ""

    if '책장' in title_text:
        return solve_bookshelf(driver)
    elif '암호' in title_text or '해독' in title_text:
        return solve_keyboard(driver)
    elif '기호' in title_text or '탐색' in title_text:
        return solve_symbol(driver)
    else:
        logger.info("  제목으로 판별 실패, DOM 기반 판별 시도...")
        try:
            driver.find_element(By.CSS_SELECTOR, '[class*="bookshelf"]')
            return solve_bookshelf(driver)
        except NoSuchElementException:
            pass
        try:
            driver.find_element(By.CSS_SELECTOR, '[class*="koreanText"]')
            return solve_keyboard(driver)
        except NoSuchElementException:
            pass
        try:
            driver.find_element(By.CSS_SELECTOR, '[class*="symbolGrid"]')
            return solve_symbol(driver)
        except NoSuchElementException:
            pass

        logger.error("  CAPTCHA 유형을 판별하지 못했습니다.")
        return None


# ───────────────────────────────────────────────────────────
# 메인 실행
# ───────────────────────────────────────────────────────────

options = webdriver.ChromeOptions()
options.add_argument("--window-size=1280,800")
driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

logger.info(f"--- 봇 세션 시작: {session_id} ---")

try:
    # ─────────────────────────────────────────────────────
    # STEP 1: 페이지 접속
    # ─────────────────────────────────────────────────────
    logger.info("STEP 1: 페이지 접속")
    driver.get(URL)
    record("page_load", extra={"url": URL})
    time.sleep(2)

    # ─────────────────────────────────────────────────────
    # STEP 2: 이메일 입력
    # ─────────────────────────────────────────────────────
    logger.info("STEP 2: 이메일 입력")
    email_input = wait_and_find(driver, By.ID, "login-email",
                                step_name="#login-email")
    ex, ey = get_center(email_input)

    ActionChains(driver).move_to_element(email_input).pause(0.3).perform()
    record("mouse_move", x=ex, y=ey, extra={"target": "login-email"})
    random_delay(200, 400)

    email_input.click()
    record("click", x=ex, y=ey, extra={"selector": "#login-email"})
    random_delay(100, 300)

    for ch in BOT_EMAIL:
        email_input.send_keys(ch)
        random_delay(30, 120)
    record("input_text", extra={"field": "email", "text": BOT_EMAIL})
    random_delay(300, 600)

    # ─────────────────────────────────────────────────────
    # STEP 3: 비밀번호 입력
    # ─────────────────────────────────────────────────────
    logger.info("STEP 3: 비밀번호 입력")
    pw_input = wait_and_find(driver, By.ID, "login-password",
                             step_name="#login-password")
    px, py_ = get_center(pw_input)

    ActionChains(driver).move_to_element(pw_input).pause(0.2).perform()
    record("mouse_move", x=px, y=py_, extra={"target": "login-password"})
    random_delay(200, 400)

    pw_input.click()
    record("click", x=px, y=py_, extra={"selector": "#login-password"})
    random_delay(100, 300)

    for ch in BOT_PASSWORD:
        pw_input.send_keys(ch)
        random_delay(30, 120)
    record("input_text", extra={"field": "password", "text": "***"})
    random_delay(300, 500)

    # ─────────────────────────────────────────────────────
    # STEP 4: 로그인 버튼 클릭
    # ─────────────────────────────────────────────────────
    logger.info("STEP 4: 로그인 버튼 클릭")
    login_btn = wait_and_find(driver, By.ID, "login-submit",
                               condition="clickable",
                               step_name="#login-submit")
    lx, ly = get_center(login_btn)

    ActionChains(driver).move_to_element(login_btn).pause(0.3).perform()
    record("mouse_move", x=lx, y=ly, extra={"target": "login-submit"})
    random_delay(200, 400)

    login_btn.click()
    record("click", x=lx, y=ly, extra={"selector": "#login-submit", "action": "login"})
    logger.info("  로그인 완료, EscapeRoom 전환 대기...")
    time.sleep(3)

    # ─────────────────────────────────────────────────────
    # STEP 5: 핫스팟 클릭 → CaptchaModal 열기
    # ─────────────────────────────────────────────────────
    logger.info("STEP 5: EscapeRoom 핫스팟 클릭")

    hotspot_ids = ["hotspot-bookshelf", "hotspot-desk", "hotspot-safe"]
    chosen = random.choice(hotspot_ids)
    logger.info(f"  선택: #{chosen}")

    hotspot = wait_and_find(driver, By.ID, chosen,
                            condition="clickable",
                            step_name=f"#{chosen}")
    hx, hy = get_center(hotspot)

    ActionChains(driver).move_to_element(hotspot).pause(0.4).perform()
    record("mouse_move", x=hx, y=hy, extra={"target": chosen})
    random_delay(300, 600)

    hotspot.click()
    record("click", x=hx, y=hy, extra={"selector": f"#{chosen}", "action": "open_captcha"})
    logger.info("  핫스팟 클릭 완료, CaptchaModal 대기...")
    time.sleep(2)

    # ─────────────────────────────────────────────────────
    # STEP 6: CaptchaModal 감지
    # ─────────────────────────────────────────────────────
    logger.info("STEP 6: CaptchaModal 모달 감지")
    captcha_input = wait_and_find(driver, By.ID, "captcha-answer",
                                  step_name="#captcha-answer (모달 감지)")
    record("modal_appeared", extra={"detected_by": "#captcha-answer"})
    time.sleep(1)

    # ─────────────────────────────────────────────────────
    # STEP 7: CAPTCHA 자동 풀이 (DOM 기반)
    # ─────────────────────────────────────────────────────
    logger.info("STEP 7: CAPTCHA 자동 풀이")
    answer = detect_and_solve_captcha(driver)

    if answer is None:
        answer = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        logger.warning(f"  자동 풀이 실패, 랜덤 답 사용: '{answer}'")
        record("captcha_solve_failed", extra={"fallback_answer": answer})
    else:
        logger.info(f"  CAPTCHA 정답 계산 완료: '{answer}'")
        record("captcha_solved", extra={"answer": answer, "method": "dom_parsing"})

    # ─────────────────────────────────────────────────────
    # STEP 8: 정답 입력
    # ─────────────────────────────────────────────────────
    logger.info("STEP 8: 캡챠 정답 입력")
    ix, iy = get_center(captcha_input)

    ActionChains(driver).move_to_element(captcha_input).pause(0.2).perform()
    record("mouse_move_to_input", x=ix, y=iy, extra={"field": "captcha-answer"})
    random_delay(200, 400)

    captcha_input.click()
    record("click", x=ix, y=iy, extra={"selector": "#captcha-answer"})
    random_delay(150, 300)

    for ch in answer:
        captcha_input.send_keys(ch)
        random_delay(20, 80)
    record("input_text", extra={"text": answer, "length": len(answer)})
    random_delay(300, 500)

    # ─────────────────────────────────────────────────────
    # STEP 9: 마우스 랜덤 움직임 (봇 패턴 수집)
    # ─────────────────────────────────────────────────────
    logger.info("STEP 9: 랜덤 마우스 움직임 (봇 패턴)")
    for i in range(5):
        ox = random.randint(-40, 40)
        oy = random.randint(-40, 40)
        ActionChains(driver).move_by_offset(ox, oy).pause(
            random.uniform(0.05, 0.15)
        ).perform()
        record("mouse_move", x=ix + ox, y=iy + oy,
               extra={"step": i, "offset": [ox, oy]})
    random_delay(200, 400)

    # ─────────────────────────────────────────────────────
    # STEP 10: 제출 버튼 클릭
    # ─────────────────────────────────────────────────────
    logger.info("STEP 10: 캡챠 제출 버튼 클릭")
    submit_btn = wait_and_find(driver, By.ID, "captcha-submit",
                               condition="clickable",
                               step_name="#captcha-submit")
    sx, sy = get_center(submit_btn)

    ActionChains(driver).move_to_element(submit_btn).pause(0.3).perform()
    record("mouse_move", x=sx, y=sy, extra={"target": "captcha-submit"})
    random_delay(200, 400)

    submit_btn.click()
    record("click", x=sx, y=sy,
           extra={"selector": "#captcha-submit", "action": "submit_captcha"})
    logger.info("  캡챠 제출 완료!")

    # ─────────────────────────────────────────────────────
    # STEP 11: 응답 대기 (행동 점수 판정 대기)
    # ─────────────────────────────────────────────────────
    logger.info("STEP 11: 행동 점수 판정 대기 (2초)")
    time.sleep(2)
    record("response_wait", extra={"wait_seconds": 2})

    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if '봇' in body_text or '로봇' in body_text or '실패' in body_text or '자동화된' in body_text or '제한' in body_text:
            logger.info("  결과: 봇으로 탐지됨 (행동 패턴 기반)")
            record("result", extra={"detected_as": "bot"})
        elif '인증 성공' in body_text or '완료되었습니다' in body_text:
            logger.info("  결과: 인증 통과됨 (예상과 다름)")
            record("result", extra={"detected_as": "human"})
        else:
            logger.info("  결과: 판정 불명")
            record("result", extra={"detected_as": "unknown", "body_preview": body_text[:200]})
    except Exception:
        record("result", extra={"detected_as": "unknown"})

    logger.info("--- 봇 시나리오 완료 ---")

except TimeoutException as e:
    record("error", extra={"type": "TimeoutException", "reason": str(e)})
    logger.error(f"TimeoutException: {e}")
except NoSuchElementException as e:
    record("error", extra={"type": "NoSuchElementException", "reason": str(e)})
    logger.error(f"NoSuchElementException: {e}")
except StaleElementReferenceException as e:
    record("error", extra={"type": "StaleElementReferenceException", "reason": str(e)})
    logger.error(f"StaleElementReferenceException: {e}")
except Exception as e:
    record("error", extra={"type": type(e).__name__, "reason": str(e)})
    logger.exception(f"Unexpected error: {e}")

finally:
    # ─────────────────────────────────────────────────────
    # STEP 12: JSON 저장 및 드라이버 종료
    # ─────────────────────────────────────────────────────
    try:
        out = OUTPUT_DIR / f"session_{session_id}.json"
        payload = {
            "session_id":  session_id,
            "label":       "bot",
            "start_time":  round(start_time, 3),
            "end_time":    round(time.time(), 3),
            "duration_ms": round((time.time() - start_time) * 1000),
            "total":       len(events),
            "events":      events,
        }
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info(f"세션 저장 완료: {out} (이벤트 {len(events)}개)")
    except PermissionError:
        logger.error(f"Permission denied: {out}")
    except IOError as e:
        logger.error(f"I/O error: {e}")
    except Exception as e:
        logger.error(f"저장 실패: {e}")

    # ── MongoDB 저장 (enriched 데이터) ───────────────────────
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        col    = client[MONGO_DB][MONGO_COL]
        result = col.insert_one({
            "session_id": session_id,
            "label":      "bot",
            "start_time": round(start_time, 3),
            "total":      len(events),
            "events":     enrich_events(events),
        })
        logger.info(f"MongoDB 저장 완료: {MONGO_DB}.{MONGO_COL} (_id={result.inserted_id})")
        client.close()
    except Exception as mongo_err:
        logger.error(f"MongoDB 저장 실패: {mongo_err}")

    finally:
        driver.quit()
        logger.info("WebDriver 종료")