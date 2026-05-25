"""
collect_human_data.py — 사람 행동 데이터 수집기
위치: bot/collect_human_data.py

실행:  python collect_human_data.py
동작:  브라우저를 열고 사람이 직접 CAPTCHA를 풀면
       마우스 이동·클릭을 JavaScript로 감지해 JSON 저장
저장:  dataset/human/session_YYYYMMDD_HHMMSS.json
"""

import json
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

from selenium import webdriver

# ── 설정 ──────────────────────────────────────────────────
URL        = "http://localhost:3000"
OUTPUT_DIR = Path("dataset/human")
WAIT_SEC   = 60       # 사람이 풀 수 있는 최대 대기 시간(초)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── JavaScript: 마우스 이벤트 리스너 주입 ─────────────────
# 브라우저 window.__events 배열에 이벤트를 쌓는다
INJECT_JS = """
window.__events = [];
const _push = (type, e) => window.__events.push({
    type,
    x:          Math.round(e.clientX),
    y:          Math.round(e.clientY),
    timestamp:  parseFloat((performance.now() / 1000 + window.__t0).toFixed(3)),
});
document.addEventListener('mousemove', e => _push('move',  e));
document.addEventListener('click',     e => _push('click', e));
document.addEventListener('mousedown', e => _push('mousedown', e));
document.addEventListener('mouseup',   e => _push('mouseup',   e));
"""

# ── 드라이버 생성 ─────────────────────────────────────────
options = webdriver.ChromeOptions()
options.add_argument("--window-size=1280,800")
driver = webdriver.Chrome(options=options)

try:
    # 1) 페이지 접속
    driver.get(URL)
    time.sleep(1)  # 렌더링 대기

    # 2) JS 리스너 주입 (페이지 로드 기준 시각 동기화)
    t0 = time.time()
    driver.execute_script(f"window.__t0 = {t0};")
    driver.execute_script(INJECT_JS)
    print("=" * 48)
    print("  브라우저에서 CAPTCHA를 직접 풀어주세요.")
    print(f"  완료되면 엔터를 누르거나 {WAIT_SEC}초 후 자동 저장됩니다.")
    print("=" * 48)

    # 3) 완료 대기 — 엔터 입력 또는 타임아웃
    done = threading.Event()
    input_thread = threading.Thread(
        target=lambda: (input(), done.set()),
        daemon=True
    )
    input_thread.start()
    done.wait(timeout=WAIT_SEC)

    # 4) JS에서 이벤트 수집
    raw_events = driver.execute_script("return window.__events || [];")

    # 5) elapsed_ms 계산 및 seq 부여
    events = []
    for i, e in enumerate(raw_events):
        e["seq"]        = i
        e["elapsed_ms"] = round((e["timestamp"] - t0) * 1000)
        events.append(e)

    # 6) JSON 저장
    session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path   = OUTPUT_DIR / f"session_{session_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "session_id": session_id,
            "start_time": round(t0, 3),
            "total":      len(events),
            "events":     events,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료: {out_path}  (이벤트 {len(events)}개)")

except Exception as e:
    print(f"\n오류: {e}")

finally:
    driver.quit()