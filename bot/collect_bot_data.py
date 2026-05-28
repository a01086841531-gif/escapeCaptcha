"""
collect_bot_data.py  — MVP 봇 데이터 수집기
사용법: python collect_bot_data.py
저장:   dataset/bot/session_20260522_15:43.json

플로우:
  1) localhost:3000 접속 (로그인 페이지)
  2) 이메일 / 비밀번호 입력 → 로그인 버튼 클릭
  3) EscapeRoom 화면 → 핫스팟 클릭
  4) CaptchaModal 표시 → 정답 입력 → 제출
  5) 결과 대기 → 세션 JSON 저장
"""

import json
import time
import random
import string
import logging
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

# ── 로깅 설정 ──────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(asctime)s %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

# ── 설정 ──────────────────────────────────────────────────
URL         = "http://localhost:3000"
OUTPUT_DIR  = Path("dataset/bot")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 테스트 계정
BOT_EMAIL    = "bot123@bot.com"
BOT_PASSWORD = "bot123"

# 대기 시간 (초)
PAGE_LOAD_TIMEOUT   = 20
ELEMENT_WAIT_TIMEOUT = 15

# ── 기록 저장소 ───────────────────────────────────────────
session_id: str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
start_time: float = time.time()
events: List[Dict[str, Any]] = []


def record(event_type: str, x: Optional[int] = None, y: Optional[int] = None, extra: Optional[Dict[str, Any]] = None) -> None:
    """
    이벤트 하나를 타임스탬프와 함께 기록한다.

    Args:
        event_type: 이벤트 타입 (page_load, login, click, mouse_move 등)
        x: X 좌표 (선택사항)
        y: Y 좌표 (선택사항)
        extra: 추가 정보 딕셔너리 (선택사항)
    """
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
    logger.info(f"[EVENT {entry['seq']:03d}] {event_type}{coord_str}")


def wait_and_find(driver, by, value, timeout=ELEMENT_WAIT_TIMEOUT, condition="visible", step_name=""):
    """
    요소를 대기하면서 찾는 헬퍼. 디버깅 로그 포함.

    Args:
        driver: WebDriver 인스턴스
        by: By 타입 (By.ID, By.CSS_SELECTOR 등)
        value: selector 값
        timeout: 대기 시간 (초)
        condition: "visible" | "clickable" | "present"
        step_name: 디버깅용 단계 이름

    Returns:
        찾은 WebElement

    Raises:
        TimeoutException: 요소를 찾지 못한 경우
    """
    logger.debug(f"[WAIT] {step_name} → by={by}, value='{value}', timeout={timeout}s, condition={condition}")

    wait = WebDriverWait(driver, timeout)

    try:
        if condition == "clickable":
            el = wait.until(EC.element_to_be_clickable((by, value)))
        elif condition == "present":
            el = wait.until(EC.presence_of_element_located((by, value)))
        else:  # visible
            el = wait.until(EC.visibility_of_element_located((by, value)))

        logger.debug(f"[FOUND] {step_name} → tag={el.tag_name}, size={el.size}, location={el.location}")
        return el

    except TimeoutException:
        # 디버깅: 현재 페이지 상태 출력
        logger.error(f"[TIMEOUT] {step_name} → 요소를 찾지 못함: by={by}, value='{value}'")
        logger.error(f"[TIMEOUT] 현재 URL: {driver.current_url}")
        logger.error(f"[TIMEOUT] 페이지 타이틀: {driver.title}")
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text[:500]
            logger.error(f"[TIMEOUT] 페이지 body 텍스트 (처음 500자): {body_text}")
        except Exception:
            pass
        raise


def get_element_center(el):
    """요소의 중심 좌표를 반환한다."""
    cx = int(el.location["x"] + el.size.get("width", 0) // 2)
    cy = int(el.location["y"] + el.size.get("height", 0) // 2)
    return cx, cy


# ── 드라이버 생성 ─────────────────────────────────────────
options = webdriver.ChromeOptions()
options.add_argument("--window-size=1280,800")
driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

logger.info(f"━━━ Session started: {session_id} ━━━")

try:
    # ═══════════════════════════════════════════════════
    # STEP 1: 페이지 접속 (로그인 화면)
    # ═══════════════════════════════════════════════════
    logger.info("▶ STEP 1: 페이지 접속")
    driver.get(URL)
    record("page_load", extra={"url": URL})
    time.sleep(2)  # 초기 렌더링 대기

    # ═══════════════════════════════════════════════════
    # STEP 2: 로그인 - 이메일 입력
    # ═══════════════════════════════════════════════════
    logger.info("▶ STEP 2: 이메일 입력")
    email_input = wait_and_find(driver, By.ID, "login-email",
                                 step_name="이메일 입력 필드")
    ex, ey = get_element_center(email_input)

    # 마우스 이동 후 클릭
    ActionChains(driver).move_to_element(email_input).pause(0.3).perform()
    record("mouse_move", x=ex, y=ey, extra={"target": "login-email"})
    random_delay(200, 400)

    email_input.click()
    record("click", x=ex, y=ey, extra={"selector": "login-email"})
    random_delay(100, 300)

    # 이메일 한 글자씩 입력 (사람처럼)
    for ch in BOT_EMAIL:
        email_input.send_keys(ch)
        random_delay(30, 120)
    record("input_text", extra={"field": "email", "text": BOT_EMAIL})
    random_delay(300, 600)

    # ═══════════════════════════════════════════════════
    # STEP 3: 로그인 - 비밀번호 입력
    # ═══════════════════════════════════════════════════
    logger.info("▶ STEP 3: 비밀번호 입력")
    pw_input = wait_and_find(driver, By.ID, "login-password",
                              step_name="비밀번호 입력 필드")
    px, py_ = get_element_center(pw_input)

    ActionChains(driver).move_to_element(pw_input).pause(0.2).perform()
    record("mouse_move", x=px, y=py_, extra={"target": "login-password"})
    random_delay(200, 400)

    pw_input.click()
    record("click", x=px, y=py_, extra={"selector": "login-password"})
    random_delay(100, 300)

    for ch in BOT_PASSWORD:
        pw_input.send_keys(ch)
        random_delay(30, 120)
    record("input_text", extra={"field": "password", "text": "***"})
    random_delay(300, 500)

    # ═══════════════════════════════════════════════════
    # STEP 4: 로그인 버튼 클릭 ("방탈출 시작")
    # ═══════════════════════════════════════════════════
    logger.info("▶ STEP 4: 로그인 버튼 클릭")
    login_btn = wait_and_find(driver, By.ID, "login-submit",
                               condition="clickable",
                               step_name="로그인 버튼 (방탈출 시작)")
    lx, ly = get_element_center(login_btn)

    ActionChains(driver).move_to_element(login_btn).pause(0.3).perform()
    record("mouse_move", x=lx, y=ly, extra={"target": "login-submit"})
    random_delay(200, 400)

    login_btn.click()
    record("click", x=lx, y=ly, extra={"selector": "login-submit", "action": "login"})
    logger.info("  → 로그인 제출 완료, EscapeRoom 전환 대기")
    time.sleep(2)  # React 상태 전환 대기

    # ═══════════════════════════════════════════════════
    # STEP 5: EscapeRoom 핫스팟 클릭 → CaptchaModal 열기
    # ═══════════════════════════════════════════════════
    logger.info("▶ STEP 5: EscapeRoom 핫스팟 클릭")

    # 3개의 핫스팟 중 랜덤 선택
    hotspot_ids = ["hotspot-bookshelf", "hotspot-desk", "hotspot-safe"]
    chosen_hotspot = random.choice(hotspot_ids)
    logger.info(f"  → 선택된 핫스팟: #{chosen_hotspot}")

    hotspot = wait_and_find(driver, By.ID, chosen_hotspot,
                             condition="clickable",
                             step_name=f"핫스팟 ({chosen_hotspot})")
    hx, hy = get_element_center(hotspot)

    # 자연스러운 마우스 이동
    ActionChains(driver).move_to_element(hotspot).pause(0.4).perform()
    record("mouse_move", x=hx, y=hy, extra={"target": chosen_hotspot})
    random_delay(300, 600)

    hotspot.click()
    record("click", x=hx, y=hy, extra={"selector": chosen_hotspot, "action": "open_captcha"})
    logger.info("  → 핫스팟 클릭 완료, CaptchaModal 대기")
    time.sleep(1.5)  # 모달 애니메이션 대기

    # ═══════════════════════════════════════════════════
    # STEP 6: CaptchaModal - 모달 표시 확인
    # ═══════════════════════════════════════════════════
    logger.info("▶ STEP 6: CaptchaModal 모달 확인")

    # CSS Module이 클래스명을 해시하므로, 모달을 ID가 있는 자식 요소로 확인
    # captcha-answer 입력 필드가 존재하면 모달이 열린 것
    captcha_input = wait_and_find(driver, By.ID, "captcha-answer",
                                   step_name="캡챠 입력 필드 (모달 내부)")
    record("modal_appeared", extra={"selector": "captcha-answer (modal detected)"})
    time.sleep(0.5)

    # ═══════════════════════════════════════════════════
    # STEP 7: 캡챠 입력 필드에 랜덤 답 입력
    # ═══════════════════════════════════════════════════
    logger.info("▶ STEP 7: 캡챠 답 입력")
    ix, iy = get_element_center(captcha_input)

    ActionChains(driver).move_to_element(captcha_input).pause(0.2).perform()
    record("mouse_move_to_input", x=ix, y=iy, extra={"field": "captcha-answer"})
    random_delay(200, 400)

    captcha_input.click()
    record("click", x=ix, y=iy, extra={"selector": "captcha-answer"})
    random_delay(150, 300)

    # 랜덤 정답 입력 (봇이므로 틀려도 OK — 행동 패턴 수집이 목적)
    random_answer = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    for ch in random_answer:
        captcha_input.send_keys(ch)
        random_delay(20, 80)
    record("input_text", extra={"text": random_answer, "length": len(random_answer)})
    random_delay(300, 500)

    # ═══════════════════════════════════════════════════
    # STEP 8: 마우스 랜덤 움직임 (봇 패턴 수집)
    # ═══════════════════════════════════════════════════
    logger.info("▶ STEP 8: 랜덤 마우스 움직임")
    for i in range(5):
        offset_x = random.randint(-40, 40)
        offset_y = random.randint(-40, 40)
        ActionChains(driver).move_by_offset(offset_x, offset_y).pause(
            random.uniform(0.05, 0.15)
        ).perform()
        record("mouse_move", x=ix + offset_x, y=iy + offset_y,
               extra={"step": i, "offset": [offset_x, offset_y]})
    random_delay(200, 400)

    # ═══════════════════════════════════════════════════
    # STEP 9: 제출 버튼 클릭
    # ═══════════════════════════════════════════════════
    logger.info("▶ STEP 9: 캡챠 제출 버튼 클릭")
    submit_btn = wait_and_find(driver, By.ID, "captcha-submit",
                                condition="clickable",
                                step_name="캡챠 제출 버튼")
    sx, sy = get_element_center(submit_btn)

    ActionChains(driver).move_to_element(submit_btn).pause(0.3).perform()
    record("mouse_move", x=sx, y=sy, extra={"target": "captcha-submit"})
    random_delay(200, 400)

    submit_btn.click()
    record("click", x=sx, y=sy, extra={"selector": "captcha-submit", "action": "submit_captcha"})
    logger.info("  → 캡챠 제출 완료")

    # ═══════════════════════════════════════════════════
    # STEP 10: 응답 대기
    # ═══════════════════════════════════════════════════
    logger.info("▶ STEP 10: 응답 대기")
    time.sleep(3)  # 서버 응답 + 결과 모달 대기
    record("response_wait", extra={"wait_seconds": 3})

    logger.info("━━━ 봇 시나리오 완료 ━━━")

except TimeoutException as e:
    record("error", extra={"type": "TimeoutException", "reason": str(e)})
    logger.error(f"❌ TimeoutException: {e}")
except NoSuchElementException as e:
    record("error", extra={"type": "NoSuchElementException", "reason": str(e)})
    logger.error(f"❌ NoSuchElementException: {e}")
except StaleElementReferenceException as e:
    record("error", extra={"type": "StaleElementReferenceException", "reason": str(e)})
    logger.error(f"❌ StaleElementReferenceException: {e}")
except Exception as e:
    record("error", extra={"type": type(e).__name__, "reason": str(e)})
    logger.exception(f"❌ Unexpected error: {e}")

finally:
    # ═══════════════════════════════════════════════════
    # STEP 11: JSON 저장 및 드라이버 종료
    # ═══════════════════════════════════════════════════
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
        logger.info(f"✅ Session saved: {out} (events: {len(events)})")
    except PermissionError:
        logger.error(f"Permission denied when saving to {out}")
    except IOError as e:
        logger.error(f"I/O error while saving to {out}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while saving: {e}")
    finally:
        driver.quit()
        logger.info("🔒 WebDriver closed")