"""
collect_bot_data.py  — MVP 봇 데이터 수집기
사용법: python collect_bot_data.py
저장:   dataset/bot/session_20260522_15:43.json
"""

import json
import time
import random
import string
from datetime import datetime, timezone
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── 설정 ──────────────────────────────────────────────────
URL         = "http://localhost:3000"
OUTPUT_DIR  = Path("dataset/bot")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 기록 저장소 ───────────────────────────────────────────
session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
start_time = time.time()
events     = []

def record(event_type, x=None, y=None, extra=None):
    """이벤트 하나를 타임스탬프와 함께 기록한다."""
    entry = {
        "seq":        len(events),
        "type":       event_type,
        "timestamp":  round(time.time(), 3),
        "elapsed_ms": round((time.time() - start_time) * 1000),
    }
    if x is not None: entry["x"] = x
    if y is not None: entry["y"] = y
    if extra:         entry["extra"] = extra
    events.append(entry)
    print(f"  [{entry['seq']:03d}] {event_type:12s}  "
          f"{'(' + str(x) + ',' + str(y) + ')' if x is not None else ''}")

# ── 드라이버 생성 ─────────────────────────────────────────
options = webdriver.ChromeOptions()
options.add_argument("--window-size=1280,800")
driver = webdriver.Chrome(options=options)
wait   = WebDriverWait(driver, 10)

try:
    # 1) 페이지 접속
    driver.get(URL)
    record("page_load", extra={"url": URL})
    time.sleep(1)

    # 2) 캡챠 모달 표시 대기 (CaptchaModal이 나타날 때까지 대기)
    modal = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "modalContent")))
    record("modal_appeared", extra={"selector": "modalContent"})
    time.sleep(0.5)

    # 3) 캡챠 입력 필드 찾기 및 포커스
    input_field = wait.until(EC.visibility_of_element_located((By.ID, "captcha-answer")))
    ix = input_field.location["x"] + input_field.size["width"]  // 2
    iy = input_field.location["y"] + input_field.size["height"] // 2
    
    # 마우스 이동해서 입력 필드로 접근
    ac = ActionChains(driver)
    ac.move_to_element(input_field).pause(0.2).perform()
    record("mouse_move_to_input", x=ix, y=iy, extra={"field": "captcha-answer"})
    time.sleep(0.3)

    # 4) 입력 필드 클릭
    input_field.click()
    record("click", x=ix, y=iy, extra={"selector": "captcha-answer"})
    time.sleep(0.2)

    # 5) 랜덤 정답 입력 (지정된 길이의 랜덤 문자열 또는 숫자)
    random_answer = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    input_field.send_keys(random_answer)
    record("input_text", extra={"text": random_answer, "length": len(random_answer)})
    time.sleep(0.3)

    # 6) 마우스 움직임 (자연스러운 상호작용 시뮬레이션)
    for _ in range(3):
        offset_x = random.randint(-20, 20)
        offset_y = random.randint(-20, 20)
        ac = ActionChains(driver)
        ac.move_by_offset(offset_x, offset_y).pause(0.1).perform()
        record("mouse_move", x=ix + offset_x, y=iy + offset_y)
    time.sleep(0.2)

    # 7) 제출 버튼 찾기 및 클릭
    submit_btn = wait.until(EC.element_to_be_clickable((By.ID, "captcha-submit")))
    sx = submit_btn.location["x"] + submit_btn.size["width"]  // 2
    sy = submit_btn.location["y"] + submit_btn.size["height"] // 2
    
    # 마우스 이동 후 클릭 (자연스러운 상호작용)
    ac = ActionChains(driver)
    ac.move_to_element(submit_btn).pause(0.2).click().perform()
    record("click", x=sx, y=sy, extra={"selector": "captcha-submit"})
    
    # 응답 대기 (성공 또는 실패)
    time.sleep(1)

except Exception as e:
    record("error", extra={"reason": str(e)})
    print(f"\n오류 발생: {e}")

finally:
    # 8) JSON 저장
    out = OUTPUT_DIR / f"session_{session_id}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "session_id": session_id,
            "start_time": round(start_time, 3),
            "total":      len(events),
            "events":     events,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n저장 완료: {out}  (이벤트 {len(events)}개)")
    driver.quit()