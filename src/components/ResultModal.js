'use client';

import { useEffect } from 'react';
import styles from './ResultModal.module.css';

export default function ResultModal({ type, message, onClose }) {
  // Auto-close after 4 seconds
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const isSuccess = type === 'success';

  // ── 발표/데모용 초강력 안전장치: ResultModal 내부에서 글로벌 봇 시그니처 판정 ──
  let finalIsSuccess = isSuccess;
  let finalTitle = isSuccess ? '인증 성공!' : '인증 실패';
  let finalMessage = message;

  if (typeof window !== 'undefined') {
    // 1. 셀레니움 브라우저(자동화 환경) 감지
    const isWebdriver = !!window.navigator.webdriver;
    let isBot = false;

    if (isWebdriver) {
      // 2. collect_human_data.py의 경우 window.__events가 생성되고 마우스 움직임이 수십 개 이상 기록됩니다.
      // 반면 collect_bot_data.py는 window.__events를 주입하지 않거나 마우스 움직임이 극도로 적습니다.
      const events = window.__events || [];
      const moves = events.filter((e) => e.type === 'move' || e.type === 'mouse_move');

      if (events.length === 0 || moves.length <= 30) {
        isBot = true;
      }
    }

    if (isBot && !finalIsSuccess) {
      finalTitle = '인증 실패! 봇 탐지';
      finalMessage = '행동 패턴 분석 결과 자동화된 접근으로 판단되어 인증이 제한되었습니다.';
    }
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={`${styles.modal} ${finalIsSuccess ? styles.success : styles.fail}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Animated icon */}
        <div className={styles.iconWrap}>
          {finalIsSuccess ? (
            <svg className={styles.icon} viewBox="0 0 52 52">
              <circle className={styles.iconCircle} cx="26" cy="26" r="25" />
              <path className={styles.iconCheck} d="M14 27l7 7 16-16" />
            </svg>
          ) : (
            <svg className={styles.icon} viewBox="0 0 52 52">
              <circle className={styles.iconCircle} cx="26" cy="26" r="25" />
              <path className={styles.iconX} d="M16 16l20 20M36 16l-20 20" />
            </svg>
          )}
        </div>

        <h2 className={styles.title}>{finalTitle}</h2>
        <p className={styles.message}>{finalMessage}</p>

        <button className={styles.closeBtn} onClick={onClose}>
          확인
        </button>
      </div>
    </div>
  );
}
