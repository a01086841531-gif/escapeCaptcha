'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { ArrowRight, Info } from 'lucide-react';
import styles from './EscapeRoom.module.css';
import useEventLogger from '../utils/useEventLogger';

/* ────────────────────────────────────────────
   한영 변환 매핑 테이블
   영어 키보드 → 한글 자모
──────────────────────────────────────────── */
const EN_TO_KR = {
  'q': 'ㅂ', 'w': 'ㅈ', 'e': 'ㄷ', 'r': 'ㄱ', 't': 'ㅅ',
  'y': 'ㅛ', 'u': 'ㅕ', 'i': 'ㅑ', 'o': 'ㅐ', 'p': 'ㅔ',
  'a': 'ㅁ', 's': 'ㄴ', 'd': 'ㅇ', 'f': 'ㄹ', 'g': 'ㅎ',
  'h': 'ㅗ', 'j': 'ㅓ', 'k': 'ㅏ', 'l': 'ㅣ',
  'z': 'ㅋ', 'x': 'ㅌ', 'c': 'ㅊ', 'v': 'ㅍ', 'b': 'ㅠ',
  'n': 'ㅜ', 'm': 'ㅡ',
  'Q': 'ㅃ', 'W': 'ㅉ', 'E': 'ㄸ', 'R': 'ㄲ', 'T': 'ㅆ',
  'O': 'ㅒ', 'P': 'ㅖ',
};

const KR_TO_EN = {};
Object.entries(EN_TO_KR).forEach(([en, kr]) => {
  KR_TO_EN[kr] = en;
});

/* 한영 변환 문제 세트
   영어 단어를 한글 키보드로 치면 나오는 글자 */
const KEYBOARD_PROBLEMS = [
  { korean: 'ㅡㅐㅜㅏㄷㅛ', answer: 'monkey' },
  { korean: 'ㅗㄷㅣㅣㅐ', answer: 'hello' },
  { korean: 'ㅈㅐㄱㅣㅇ', answer: 'world' },
  { korean: 'ㅁㅔㅔㅣㄷ', answer: 'apple' },
  { korean: 'ㄷㄴㅊㅁㅔㄷ', answer: 'escape' },
];

/* ────────────────────────────────────────────
   책장 문제 생성
──────────────────────────────────────────── */
function generateBookshelfProblem() {
  const heights = [];
  const numbers = [];
  const usedH = new Set();
  const usedN = new Set();

  while (heights.length < 5) {
    const h = Math.floor(Math.random() * 100) + 80; // 80 ~ 179
    if (!usedH.has(h)) {
      usedH.add(h);
      heights.push(h);
    }
  }

  while (numbers.length < 5) {
    const n = Math.floor(Math.random() * 90) + 10; // 10 ~ 99
    if (!usedN.has(n)) {
      usedN.add(n);
      numbers.push(n);
    }
  }

  const books = heights.map((h, i) => ({ height: h, number: numbers[i] }));
  // answer: numbers sorted by ascending height
  const sorted = [...books].sort((a, b) => a.height - b.height);
  const answer = sorted.map((b) => b.number).join(' ');

  return { books, answer };
}

/* ────────────────────────────────────────────
   기호 세기 문제 생성
──────────────────────────────────────────── */
const ALL_SYMBOLS = ['🔑', '🗝️', '🔒', '🔓', '🚪', '💎', '🕯️', '📜', '⚙️', '🧩'];

function generateSymbolProblem() {
  const targetIdx = Math.floor(Math.random() * 3); // 첫 3개 중 하나
  const target = ALL_SYMBOLS[targetIdx];
  const gridSize = 36; // 6x6
  const grid = [];
  let targetCount = Math.floor(Math.random() * 5) + 3; // 3~7

  // Place target symbols
  const targetPositions = new Set();
  while (targetPositions.size < targetCount) {
    targetPositions.add(Math.floor(Math.random() * gridSize));
  }

  for (let i = 0; i < gridSize; i++) {
    if (targetPositions.has(i)) {
      grid.push(target);
    } else {
      // Random non-target symbol
      const others = ALL_SYMBOLS.filter((s) => s !== target);
      grid.push(others[Math.floor(Math.random() * others.length)]);
    }
  }

  return { grid, target, answer: String(targetCount) };
}

/* ────────────────────────────────────────────
   Book colors for visual variety
──────────────────────────────────────────── */
const BOOK_COLORS = [
  'linear-gradient(135deg, #8b2500, #a0522d)',
  'linear-gradient(135deg, #1a3a5c, #2d5f8a)',
  'linear-gradient(135deg, #2d5a27, #4a8c3f)',
  'linear-gradient(135deg, #5c3a6e, #8a5ca0)',
  'linear-gradient(135deg, #8b6914, #c49b2a)',
];

/* ────────────────────────────────────────────
   CaptchaModal Component
──────────────────────────────────────────── */
export default function CaptchaModal({ onSuccess, onFail, onClose }) {
  // Pick random captcha type
  const [captchaType] = useState(() => Math.floor(Math.random() * 3));
  const [userInput, setUserInput] = useState('');
  const [shaking, setShaking] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const [verificationError, setVerificationError] = useState('');
  const [lastScore, setLastScore] = useState(null);
  const [lastThreshold, setLastThreshold] = useState(null);

  // Attach global event logger while the modal is mounted
  const eventLogger = useEventLogger();

  const verifyCaptchaEvents = useCallback(async (events) => {
    const response = await fetch('/api/captcha-score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ events }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload?.error || '인증 모델 검증에 실패했습니다.');
    }

    const result = await response.json();
    return result;
  }, []);

  // Generate problem data once
  const problem = useMemo(() => {
    switch (captchaType) {
      case 0:
        return { type: 'bookshelf', ...generateBookshelfProblem() };
      case 1: {
        const p = KEYBOARD_PROBLEMS[Math.floor(Math.random() * KEYBOARD_PROBLEMS.length)];
        return { type: 'keyboard', ...p };
      }
      case 2:
        return { type: 'symbol', ...generateSymbolProblem() };
      default:
        return { type: 'bookshelf', ...generateBookshelfProblem() };
    }
  }, [captchaType]);

  const handleSubmit = useCallback(async () => {
    const trimmed = userInput.trim().toLowerCase();
    const correctAnswer = problem.answer.toLowerCase();

    if (trimmed === correctAnswer) {
      setVerificationError('');
      const events = eventLogger?.getAllEvents?.() || [];

      try {
        const result = await verifyCaptchaEvents(events);
        setLastScore(result?.score ?? null);
        setLastThreshold(result?.threshold ?? null);
        if (!result?.is_human) {
          setAttempts((p) => p + 1);
          setShaking(true);
          setTimeout(() => setShaking(false), 500);
          setVerificationError('행동 패턴이 로봇으로 감지되었습니다. 인증이 실패했습니다.');

          if (attempts + 1 >= 3) {
            setTimeout(() => onFail(), 600);
          }

          return;
        }

        onSuccess();
      } catch (error) {
        setVerificationError(error.message || '인증 모델 검증에 실패했습니다. 다시 시도해주세요.');
      }
    } else {
      setAttempts((p) => p + 1);
      setShaking(true);
      setTimeout(() => setShaking(false), 500);

      if (attempts + 1 >= 3) {
        setTimeout(() => onFail(), 600);
      }
    }
  }, [userInput, problem.answer, attempts, onSuccess, onFail, eventLogger, verifyCaptchaEvents]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter') handleSubmit();
    },
    [handleSubmit]
  );

  /* ── Render: 책장 ── */
  const renderBookshelf = () => (
    <>
      <div className={styles.bookshelf}>
        {problem.books.map((book, i) => (
          <div
            key={i}
            className={styles.book}
            style={{
              height: `${book.height}px`,
              width: `${48 + (i * 3)}px`,
              background: BOOK_COLORS[i % BOOK_COLORS.length],
            }}
          >
            <span className={styles.bookNumber}>{book.number}</span>
          </div>
        ))}
      </div>
      <div className={styles.bookshelfHint}>
        <Info size={14} />
        책 높이가 작은 것부터 큰 순서대로 숫자를 입력하세요 (공백으로 구분)
      </div>
    </>
  );

  /* ── Render: 한영타 변환 ── */
  const renderKeyboard = () => (
    <>
      <div className={styles.keyboardChallenge}>
        <div className={styles.koreanText}>{problem.korean}</div>
        <div className={styles.keyboardHint}>
          위 한글을 영어 키보드로 입력하면 어떤 단어가 될까요?
        </div>
      </div>
    </>
  );

  /* ── Render: 기호 세기 ── */
  const renderSymbol = () => (
    <>
      <div className={styles.symbolGrid}>
        {problem.grid.map((sym, i) => (
          <div key={i} className={styles.symbolCell}>
            {sym}
          </div>
        ))}
      </div>
      <div className={styles.symbolQuestion}>
        위 격자에서{' '}
        <span className={styles.targetSymbol}>{problem.target}</span> 의 개수는?
      </div>
    </>
  );

  const titles = {
    bookshelf: '📚 책장의 비밀',
    keyboard: '⌨️ 암호 해독',
    symbol: '🔍 기호 탐색',
  };

  const descs = {
    bookshelf: '책장에 꽂혀있는 책들을 잘 관찰하세요. 높이의 비밀을 풀어야 문이 열립니다.',
    keyboard: '벽에 적힌 이상한 문자... 이것은 한글 키보드로 친 것 같습니다. 영어로 해독하세요!',
    symbol: '바닥에 흩어진 기호들 속에서 특정 기호의 개수를 세어주세요.',
  };

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div
        className={`${styles.modalContent} ${shaking ? styles.shakeError : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        <button className={styles.modalClose} onClick={onClose} aria-label="닫기">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>

        <h2 className={styles.modalTitle}>{titles[problem.type]}</h2>
        <p className={styles.modalDesc}>{descs[problem.type]}</p>

        <div className={styles.captchaArea}>
          {problem.type === 'bookshelf' && renderBookshelf()}
          {problem.type === 'keyboard' && renderKeyboard()}
          {problem.type === 'symbol' && renderSymbol()}

          <input
            id="captcha-answer"
            className={styles.captchaInput}
            type="text"
            placeholder="정답을 입력하세요..."
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyDown={handleKeyDown}
            autoFocus
            autoComplete="off"
          />
        </div>

        <button
          id="captcha-submit"
          className={styles.captchaSubmitBtn}
          onClick={handleSubmit}
        >
          확인 <ArrowRight size={16} style={{ verticalAlign: 'middle', marginLeft: 6 }} />
        </button>

        {verificationError && (
          <p className={styles.captchaErrorMessage}>
            {verificationError}
          </p>
        )}

        {lastScore !== null && (
          <p style={{ textAlign: 'center', marginTop: 8, fontSize: '0.85rem', color: '#666' }}>
            모델 점수: {typeof lastScore === 'number' ? lastScore.toFixed(4) : String(lastScore)}
            {lastThreshold !== null && (
              <span> (임계값: {typeof lastThreshold === 'number' ? lastThreshold : String(lastThreshold)})</span>
            )}
          </p>
        )}

        {attempts > 0 && (
          <p
            style={{
              textAlign: 'center',
              marginTop: 14,
              fontSize: '0.8rem',
              color: '#c41e3a',
            }}
          >
            틀렸습니다! ({attempts}/3 시도)
          </p>
        )}
      </div>
    </div>
  );
}
