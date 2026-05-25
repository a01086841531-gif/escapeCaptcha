"""
mouse_tracker.py — MVP 마우스 이벤트 기록 모듈
collect_bot_data.py 에서 import 해서 사용한다.
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

# 로깅 설정
logger = logging.getLogger(__name__)


class MouseTracker:
    """마우스 이벤트 추적 및 기록 클래스"""
    
    def __init__(self) -> None:
        """MouseTracker 초기화"""
        self.start_time: float = time.time()
        self.events: List[Dict[str, Any]] = []

    def _validate_coordinates(self, x: int | float, y: int | float) -> bool:
        """좌표 유효성 검사"""
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            logger.warning(f"Invalid coordinate types: x={type(x).__name__}, y={type(y).__name__}")
            return False
        if x < 0 or y < 0:
            logger.warning(f"Negative coordinates detected: x={x}, y={y}")
            return False
        return True

    def _record(self, event_type: str, x: int | float, y: int | float, extra: Optional[Dict[str, Any]] = None) -> bool:
        """
        이벤트 하나를 타임스탬프와 함께 기록한다.
        
        Args:
            event_type: 이벤트 타입 ("move" | "click" | "drag")
            x: X 좌표 (int 또는 float)
            y: Y 좌표 (int 또는 float)
            extra: 추가 정보 딕셔너리
            
        Returns:
            성공 여부
        """
        if not self._validate_coordinates(x, y):
            return False
            
        try:
            entry: Dict[str, Any] = {
                "seq":        len(self.events),
                "type":       event_type,
                "x":          int(x),
                "y":          int(y),
                "timestamp":  round(time.time(), 3),
                "elapsed_ms": round((time.time() - self.start_time) * 1000),
            }
            if extra and isinstance(extra, dict):
                entry["extra"] = extra
            self.events.append(entry)
            return True
        except Exception as e:
            logger.error(f"Failed to record event: {e}")
            return False

    def move(self, x: int | float, y: int | float) -> bool:
        """마우스 이동 기록"""
        return self._record("move", x, y)

    def click(self, x: int | float, y: int | float, selector: str = "") -> bool:
        """마우스 클릭 기록"""
        return self._record("click", x, y, extra={"selector": selector} if selector else None)

    def drag(self, start_x: int | float, start_y: int | float, end_x: int | float, end_y: int | float, duration_ms: int | float = 0) -> bool:
        """
        마우스 드래그 기록
        
        Args:
            start_x: 시작 X 좌표
            start_y: 시작 Y 좌표
            end_x: 종료 X 좌표
            end_y: 종료 Y 좌표
            duration_ms: 드래그 소요 시간 (밀리초)
            
        Returns:
            성공 여부
        """
        # 시작점과 종료점 모두 검증
        if not self._validate_coordinates(start_x, start_y):
            logger.warning(f"Invalid start coordinates: ({start_x}, {start_y})")
            return False
        if not self._validate_coordinates(end_x, end_y):
            logger.warning(f"Invalid end coordinates: ({end_x}, {end_y})")
            return False
        if not isinstance(duration_ms, (int, float)) or duration_ms < 0:
            logger.warning(f"Invalid duration: {duration_ms}")
            return False
            
        return self._record("drag", start_x, start_y,
                           extra={
                               "end_x": int(end_x),
                               "end_y": int(end_y),
                               "duration_ms": int(duration_ms)
                           })

    def save(self, path: Path) -> bool:
        """
        이벤트를 JSON 파일로 저장
        
        Args:
            path: 저장 경로 (Path 객체 또는 문자열)
            
        Returns:
            성공 여부
        """
        try:
            # 경로 검증
            if not isinstance(path, Path):
                path = Path(path)
            
            # 디렉토리 생성
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # JSON 저장
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "total":  len(self.events),
                    "events": self.events,
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Successfully saved {len(self.events)} events to {path}")
            return True
            
        except PermissionError:
            logger.error(f"Permission denied when saving to {path}")
            return False
        except IOError as e:
            logger.error(f"I/O error while saving to {path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while saving to {path}: {e}")
            return False