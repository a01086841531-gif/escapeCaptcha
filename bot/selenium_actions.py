"""
selenium_actions.py — MVP 사람처럼 보이는 Selenium 동작 모음
collect_bot_data.py 에서 import 해서 사용한다.
"""

import time
import random
import logging
from typing import Tuple, List, Optional, Union

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    InvalidArgumentException,
)

# 로깅 설정
logger = logging.getLogger(__name__)

# 타입 정의
Coordinate = Union[int, float]
CoordinateTuple = Tuple[int, int]
DragResult = Tuple[int, int, int, int, int]


def random_delay(min_ms: Coordinate = 200, max_ms: Coordinate = 600) -> None:
    """
    랜덤 딜레이 (사람처럼 보이기 위함)
    
    Args:
        min_ms: 최소 대기 시간 (밀리초, int 또는 float)
        max_ms: 최대 대기 시간 (밀리초, int 또는 float)
        
    Raises:
        ValueError: min_ms, max_ms가 음수이거나 min_ms > max_ms인 경우
    """
    if not isinstance(min_ms, (int, float)) or not isinstance(max_ms, (int, float)):
        raise ValueError("min_ms와 max_ms는 숫자(int 또는 float)여야 합니다")
    if min_ms < 0 or max_ms < 0:
        raise ValueError("min_ms와 max_ms는 음수일 수 없습니다")
    if min_ms > max_ms:
        raise ValueError(f"min_ms({min_ms})가 max_ms({max_ms})보다 클 수 없습니다")
    
    delay_sec = random.uniform(min_ms, max_ms) / 1000
    time.sleep(delay_sec)


def random_move(driver: WebDriver, cx: Coordinate, cy: Coordinate, steps: int = 5) -> Optional[List[CoordinateTuple]]:
    """
    현재 위치 근처를 랜덤하게 흔들다가 목표 좌표로 이동.
    
    Args:
        driver: Selenium WebDriver 인스턴스
        cx: 목표 X 좌표 (int 또는 float)
        cy: 목표 Y 좌표 (int 또는 float)
        steps: 이동 단계 수 (기본값 5)
        
    Returns:
        경로: 최종 (x, y) 좌표 목록 [(x,y), ...], 실패 시 None
    """
    if not driver:
        logger.error("WebDriver 인스턴스가 None입니다")
        return None
    
    if not isinstance(cx, (int, float)) or not isinstance(cy, (int, float)):
        logger.error(f"Invalid coordinates: cx={type(cx).__name__}, cy={type(cy).__name__}")
        return None
    
    if cx < 0 or cy < 0:
        logger.warning(f"Negative coordinates detected: cx={cx}, cy={cy}")
        return None
    
    if not isinstance(steps, int) or steps <= 0:
        logger.error(f"Invalid steps: {steps}. Must be positive integer")
        return None
    
    try:
        ac = ActionChains(driver)
        path: List[CoordinateTuple] = []
        
        for _ in range(steps):
            ox = random.randint(-60, 60)
            oy = random.randint(-30, 30)
            
            ac.move_by_offset(ox, oy).pause(random.uniform(0.03, 0.1))
            path.append((int(cx + ox), int(cy + oy)))
        
        ac.perform()
        logger.debug(f"Completed {steps} random moves")
        return path
        
    except StaleElementReferenceException:
        logger.error("Element reference became stale during mouse movement")
        return None
    except InvalidArgumentException as e:
        logger.error(f"Invalid argument for mouse movement: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during random_move: {e}")
        return None



def click_element(driver: WebDriver, selector: str) -> Optional[CoordinateTuple]:
    """
    CSS 셀렉터로 버튼을 찾아 사람처럼 이동 후 클릭.
    
    Args:
        driver: Selenium WebDriver 인스턴스
        selector: CSS 셀렉터 문자열
        
    Returns:
        클릭 좌표 (x, y), 실패 시 None
    """
    if not driver:
        logger.error("WebDriver 인스턴스가 None입니다")
        return None
    
    if not selector or not isinstance(selector, str):
        logger.error(f"Invalid selector: {repr(selector)}")
        return None
    
    try:
        el = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        
        # Element 크기 검증
        width = el.size.get("width", 0)
        height = el.size.get("height", 0)
        if width <= 0 or height <= 0:
            logger.warning(f"Element size invalid: {width}x{height}")
            return None
        
        cx = int(el.location["x"] + width // 2)
        cy = int(el.location["y"] + height // 2)
        
        # 좌표 검증
        if cx < 0 or cy < 0:
            logger.warning(f"Calculated negative coordinates: ({cx}, {cy})")
            return None

        ActionChains(driver).move_to_element(el).perform()
        random_delay(100, 300)
        
        # Element가 여전히 유효한지 확인 후 클릭
        el.click()
        logger.debug(f"Successfully clicked element at ({cx}, {cy})")
        return cx, cy
        
    except TimeoutException:
        logger.error(f"Timeout: Element with selector '{selector}' not found within 10 seconds")
        return None
    except NoSuchElementException:
        logger.error(f"NoSuchElementException: Element with selector '{selector}' not found")
        return None
    except StaleElementReferenceException:
        logger.error(f"StaleElementReferenceException: Element reference became stale")
        return None
    except InvalidArgumentException as e:
        logger.error(f"InvalidArgumentException: Invalid selector or argument: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in click_element: {e}")
        return None



def drag_element(driver: WebDriver, handle_sel: str, target_sel: str) -> Optional[DragResult]:
    """
    handle 요소를 target 위치로 드래그.
    
    Args:
        driver: Selenium WebDriver 인스턴스
        handle_sel: 드래그할 요소의 CSS 셀렉터
        target_sel: 드래그 대상 요소의 CSS 셀렉터
        
    Returns:
        드래그 정보 (start_x, start_y, end_x, end_y, duration_ms), 실패 시 None
    """
    if not driver:
        logger.error("WebDriver 인스턴스가 None입니다")
        return None
    
    if not handle_sel or not isinstance(handle_sel, str):
        logger.error(f"Invalid handle_sel: {repr(handle_sel)}")
        return None
    
    if not target_sel or not isinstance(target_sel, str):
        logger.error(f"Invalid target_sel: {repr(target_sel)}")
        return None
    
    try:
        handle = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, handle_sel))
        )
        target = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, target_sel))
        )
        
        # Element 크기 검증
        handle_width = handle.size.get("width", 0)
        handle_height = handle.size.get("height", 0)
        if handle_width <= 0 or handle_height <= 0:
            logger.warning(f"Handle element size invalid: {handle_width}x{handle_height}")
            return None
        
        target_width = target.size.get("width", 0)
        target_height = target.size.get("height", 0)
        if target_width <= 0 or target_height <= 0:
            logger.warning(f"Target element size invalid: {target_width}x{target_height}")
            return None

        sx = int(handle.location["x"] + handle_width // 2)
        sy = int(handle.location["y"] + handle_height // 2)
        ex = int(target.location["x"] + target_width // 2)
        ey = int(target.location["y"] + target_height // 2)
        
        # 좌표 검증
        if sx < 0 or sy < 0 or ex < 0 or ey < 0:
            logger.warning(f"Negative coordinates detected: start=({sx}, {sy}), end=({ex}, {ey})")
            return None

        t0 = time.time()
        ActionChains(driver)\
            .move_to_element(handle)\
            .pause(random.uniform(0.1, 0.3))\
            .click_and_hold(handle)\
            .pause(random.uniform(0.1, 0.2))\
            .move_by_offset((ex - sx) // 2, (ey - sy) // 2)\
            .pause(random.uniform(0.05, 0.1))\
            .move_to_element(target)\
            .pause(random.uniform(0.05, 0.1))\
            .release()\
            .perform()
        
        duration_ms = round((time.time() - t0) * 1000)
        logger.debug(f"Drag completed: ({sx}, {sy}) -> ({ex}, {ey}), duration: {duration_ms}ms")
        return sx, sy, ex, ey, duration_ms
        
    except TimeoutException:
        logger.error(f"Timeout: Handle '{handle_sel}' or target '{target_sel}' not found within 10 seconds")
        return None
    except NoSuchElementException:
        logger.error(f"NoSuchElementException: Handle '{handle_sel}' or target '{target_sel}' not found")
        return None
    except StaleElementReferenceException:
        logger.error("StaleElementReferenceException: Element reference became stale during drag")
        return None
    except InvalidArgumentException as e:
        logger.error(f"InvalidArgumentException: Invalid selector or argument during drag: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in drag_element: {e}")
        return None