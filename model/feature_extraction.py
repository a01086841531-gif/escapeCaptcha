"""
feature_extraction.py — 행동 로그 → ML feature 추출
위치: model/feature_extraction.py

실행:  python feature_extraction.py
입력:  dataset/bot/*.json, dataset/human/*.json
출력:  model/features.csv
"""

import json
import math
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# ── Pandas import 안정화 ──────────────────────────────────
try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas 패키지가 설치되지 않았습니다.")
    print("       설치 명령: pip install pandas")
    sys.exit(1)

# ── 로깅 설정 ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ── 경로 설정 ──────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent.parent   # 프로젝트 루트
DATASET_DIR = BASE_DIR / "dataset"
OUTPUT_CSV  = Path(__file__).parent / "features.csv"

# ── 경로 검증 ────────────────────────────────────────────
if not DATASET_DIR.exists():
    logger.error(f"Dataset 디렉토리가 없습니다: {DATASET_DIR}")
    sys.exit(1)


# ── 단일 세션 JSON → feature dict ─────────────────────────
def extract(json_path: Path, label: str) -> Optional[Dict[str, Any]]:
    """
    하나의 세션 JSON 파일에서 feature를 추출한다.

    Parameters
    ----------
    json_path : JSON 파일 경로
    label     : "bot" 또는 "human" (문자열, train_model.py에서 숫자로 변환)
    
    Returns
    -------
    Dict 또는 None (추출 실패 시)
        반환되는 dict의 키:
        - file: 파일 이름 (train_model.py에서 사용 안 함)
        - label: "bot" 또는 "human" (문자열)
        - avg_speed, total_dist, direction_changes, click_gap_mean, click_gap_std, duration_sec: feature 값들
    """
    try:
        data   = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(f"JSON 파일 읽기 실패 {json_path.name}: {e}")
        return None
    except Exception as e:
        logger.warning(f"파일 읽기 실패 {json_path.name}: {e}")
        return None
    
    # events 키 존재 확인
    if "events" not in data:
        logger.warning(f"'events' 키가 없습니다: {json_path.name}")
        return None
    
    events = data.get("events", [])
    if not isinstance(events, list) or len(events) == 0:
        logger.warning(f"events가 비어있거나 리스트가 아닙니다: {json_path.name}")
        return None

    # "move" 또는 "mouse_move" 타입 모두 지원
    # collect_bot_data.py는 "mouse_move"를 사용하고,
    # 다른 데이터는 "move"를 사용할 수 있음
    moves  = [e for e in events if e.get("type") in ("move", "mouse_move")]
    clicks = [e for e in events if e.get("type") == "click"]

    # ── 평균 마우스 속도 & 총 이동 거리 ──────────────────
    total_dist = 0.0
    total_time = 0.0
    try:
        for i in range(1, len(moves)):
            prev_move = moves[i-1]
            curr_move = moves[i]
            
            # 필수 키 검증
            if not all(k in curr_move for k in ["x", "y", "timestamp"]):
                continue
            if not all(k in prev_move for k in ["x", "y", "timestamp"]):
                continue
            
            dx = float(curr_move["x"]) - float(prev_move["x"])
            dy = float(curr_move["y"]) - float(prev_move["y"])
            dt = float(curr_move["timestamp"]) - float(prev_move["timestamp"])
            
            # 타임스탬프 이상 검사
            if dt < 0 or dt > 60:  # 60초 이상 차이는 비정상
                continue
            
            dist = math.hypot(dx, dy)
            total_dist += dist
            total_time += dt
    except (KeyError, TypeError, ValueError) as e:
        logger.warning(f"마우스 속도 계산 중 오류 {json_path.name}: {e}")

    avg_speed = (total_dist / total_time) if total_time > 0 else 0.0

    # ── 방향 전환 횟수 ────────────────────────────────────
    direction_changes = 0
    try:
        for i in range(1, len(moves) - 1):
            moves_i_minus_1 = moves[i-1]
            moves_i = moves[i]
            moves_i_plus_1 = moves[i+1]
            
            # 필수 키 검증
            required_keys = ["x", "y"]
            if not all(k in moves_i_minus_1 for k in required_keys):
                continue
            if not all(k in moves_i for k in required_keys):
                continue
            if not all(k in moves_i_plus_1 for k in required_keys):
                continue
            
            ax = float(moves_i["x"]) - float(moves_i_minus_1["x"])
            ay = float(moves_i["y"]) - float(moves_i_minus_1["y"])
            bx = float(moves_i_plus_1["x"]) - float(moves_i["x"])
            by = float(moves_i_plus_1["y"]) - float(moves_i["y"])
            
            # 내적 < 0 이면 방향이 90° 이상 전환
            if (ax * bx + ay * by) < 0:
                direction_changes += 1
    except (KeyError, TypeError, ValueError) as e:
        logger.warning(f"방향 전환 계산 중 오류 {json_path.name}: {e}")

    # ── 클릭 간격 평균 & 표준편차 ─────────────────────────
    click_gaps: List[float] = []
    try:
        for i in range(1, len(clicks)):
            prev_click = clicks[i-1]
            curr_click = clicks[i]
            
            if "timestamp" not in prev_click or "timestamp" not in curr_click:
                continue
            
            gap = float(curr_click["timestamp"]) - float(prev_click["timestamp"])
            
            # 클릭 간격이 비정상적이면 무시 (음수 또는 600초 이상)
            if 0 <= gap <= 600:
                click_gaps.append(gap)
    except (KeyError, TypeError, ValueError) as e:
        logger.warning(f"클릭 간격 계산 중 오류 {json_path.name}: {e}")

    if click_gaps:
        mean_gap = sum(click_gaps) / len(click_gaps)
        variance = sum((g - mean_gap) ** 2 for g in click_gaps) / len(click_gaps)
        std_gap  = math.sqrt(variance)
    else:
        mean_gap = std_gap = 0.0

    # ── 전체 수행 시간 ────────────────────────────────────
    duration = 0.0
    if events:
        try:
            first_ts = float(events[0].get("timestamp", 0))
            last_ts  = float(events[-1].get("timestamp", 0))
            duration = max(0, last_ts - first_ts)
        except (KeyError, TypeError, ValueError):
            pass

    return {
        "file":               json_path.name,
        "label":              label,          # "bot" 또는 "human"
        "avg_speed":          round(avg_speed, 4),
        "total_dist":         round(total_dist, 2),
        "direction_changes":  direction_changes,
        "click_gap_mean":     round(mean_gap, 4),
        "click_gap_std":      round(std_gap, 4),
        "duration_sec":       round(duration, 3),
    }


# ── 전체 데이터셋 처리 ────────────────────────────────────
def build_dataframe() -> pd.DataFrame:
    """
    dataset/bot, dataset/human 폴더에서 JSON 파일들을 읽고
    feature 데이터프레임을 생성한다.
    
    Returns
    -------
    pd.DataFrame
        추출된 feature들의 데이터프레임
        칼럼: file, label, avg_speed, total_dist, direction_changes, click_gap_mean, click_gap_std, duration_sec
        
    주의:
        - label은 "bot" 또는 "human" 문자열
        - train_model.py에서 label을 숫자로 변환: bot=0, human=1
        - file 칼럼은 train_model.py의 분류에 사용되지 않음 (참고용)
    """
    rows: List[Dict[str, Any]] = []
    
    for label in ("bot", "human"):
        label_dir = DATASET_DIR / label
        
        # 라벨별 폴더 존재 여부 확인
        if not label_dir.exists():
            logger.warning(f"'{label}' 폴더가 없습니다: {label_dir}")
            continue
        
        # 폴더가 디렉토리가 아니면 스킵
        if not label_dir.is_dir():
            logger.warning(f"'{label}'은 디렉토리가 아닙니다: {label_dir}")
            continue
        
        json_files = sorted(label_dir.glob("*.json"))
        
        if not json_files:
            logger.warning(f"'{label}' 폴더에 JSON 파일이 없습니다: {label_dir}")
            continue
        
        logger.info(f"'{label}' 폴더에서 {len(json_files)}개 파일 처리 중...")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for path in json_files:
            try:
                result = extract(path, label)
                if result is not None:
                    rows.append(result)
                    success_count += 1
                    logger.debug(f"  [OK] {label}/{path.name}")
                else:
                    skip_count += 1
                    logger.debug(f"  [SKIP] {label}/{path.name}: feature 추출 실패")
            except Exception as e:
                error_count += 1
                logger.debug(f"  [ERROR] {label}/{path.name}: {e}")
        
        logger.info(f"'{label}' 처리 완료: {success_count}개 성공, {skip_count}개 스킵, {error_count}개 오류")

    if not rows:
        logger.warning("추출된 feature가 없습니다. 데이터를 확인하세요.")
        return pd.DataFrame()

    return pd.DataFrame(rows)


def save_csv(df: pd.DataFrame, path: Path = OUTPUT_CSV) -> bool:
    """
    데이터프레임을 CSV 파일로 저장한다.
    
    Parameters
    ----------
    df : pd.DataFrame
        저장할 데이터프레임
    path : Path
        저장 경로
        
    Returns
    -------
    bool
        성공 여부
    """
    try:
        # 디렉토리 생성
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # CSV 저장
        df.to_csv(path, index=False, encoding="utf-8")
        logger.info(f"저장 완료: {path} ({len(df)}행)")
        return True
        
    except PermissionError:
        logger.error(f"권한 오류: {path}에 쓸 수 없습니다")
        return False
    except IOError as e:
        logger.error(f"I/O 오류: {path}에 저장 실패: {e}")
        return False
    except Exception as e:
        logger.error(f"예상치 못한 오류: {path}에 저장 실패: {e}")
        return False


# ── 진입점 ────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"Dataset 디렉토리: {DATASET_DIR}")
    logger.info(f"출력 파일: {OUTPUT_CSV}")
    
    df = build_dataframe()
    
    if df.empty:
        logger.error("데이터프레임이 비어있습니다. 데이터를 확인하세요.")
        sys.exit(1)
    
    # 데이터 출력
    logger.info("\n추출된 feature:")
    print(df.to_string(index=False))
    
    # CSV 저장
    if save_csv(df):
        logger.info("성공적으로 완료되었습니다.")
        sys.exit(0)
    else:
        logger.error("CSV 저장에 실패했습니다.")
        sys.exit(1)