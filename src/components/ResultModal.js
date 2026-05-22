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

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={`${styles.modal} ${isSuccess ? styles.success : styles.fail}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Animated icon */}
        <div className={styles.iconWrap}>
          {isSuccess ? (
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

        <h2 className={styles.title}>
          {isSuccess ? '인증 성공!' : '인증 실패'}
        </h2>
        <p className={styles.message}>{message}</p>

        <button className={styles.closeBtn} onClick={onClose}>
          확인
        </button>
      </div>
    </div>
  );
}
