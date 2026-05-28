'use client';

import { useState, useCallback } from 'react';
import { KeyRound, Mail, Lock, Shield } from 'lucide-react';
import styles from './page.module.css';
import EscapeRoom from '@/components/EscapeRoom';
import ResultModal from '@/components/ResultModal';

/* ─── 허용된 테스트 계정 ─── */
const ALLOWED_ACCOUNTS = {
  'bot123@bot.com': 'bot123',
  'person123@person.com': 'person123',
  'test123@test.com': 'test123',
};

export default function Home() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showEscapeRoom, setShowEscapeRoom] = useState(false);
  const [result, setResult] = useState(null); // { type: 'success'|'fail', message: string }
  const [loginError, setLoginError] = useState('');

  /* ─── 로그인 폼 제출: 테스트 계정 검증 후 캡챠로 이동 ─── */
  const handleLoginSubmit = useCallback(
    (e) => {
      e.preventDefault();
      setLoginError('');

      if (!email.trim() || !password.trim()) {
        setLoginError('이메일과 비밀번호를 모두 입력해주세요.');
        return;
      }

      // 테스트 계정 검증
      const expected = ALLOWED_ACCOUNTS[email.trim()];
      if (!expected || expected !== password) {
        setLoginError('아이디와 비밀번호가 옳지 않습니다.');
        return;
      }

      // 계정 검증 성공 → 캡챠 화면으로 전환
      setShowEscapeRoom(true);
    },
    [email, password]
  );

  /* ─── 캡챠 성공 (봇 아님으로 판별) → 인증 성공 ─── */
  const handleCaptchaSuccess = useCallback(() => {
    setResult({ type: 'success', message: '캡챠 인증에 성공하였습니다! 인증이 완료되었습니다.' });
  }, []);

  /* ─── 캡챠 실패 (봇으로 판별) → 인증 실패 ─── */
  const handleCaptchaFail = useCallback(() => {
    setResult({ type: 'fail', message: '봇으로 감지되었습니다. 인증에 실패했습니다.' });
  }, []);

  /* ─── 결과 모달 닫기 → 로그인 화면으로 복귀 ─── */
  const handleResultClose = useCallback(() => {
    setResult(null);
    setShowEscapeRoom(false);
  }, []);

  /* ─── 방탈출 뷰 ─── */
  if (showEscapeRoom) {
    return (
      <div className={styles.escapeOverlay}>
        <EscapeRoom
          onCaptchaSuccess={handleCaptchaSuccess}
          onCaptchaFail={handleCaptchaFail}
        />
        {result && (
          <ResultModal
            type={result.type}
            message={result.message}
            onClose={handleResultClose}
          />
        )}
      </div>
    );
  }

  /* ─── 로그인 뷰 ─── */
  return (
    <div className={styles.page}>
      {/* Floating particles */}
      <div className={styles.particles}>
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={i}
            className={styles.particle}
            style={{
              left: `${(i * 17 + 3) % 100}%`,
              animationDelay: `${(i * 1.3) % 8}s`,
              animationDuration: `${6 + (i * 0.7) % 6}s`,
            }}
          />
        ))}
      </div>

      <div className={styles.loginContainer}>
        <div className={styles.loginCard}>
          {/* Icon */}
          <div className={styles.iconWrapper}>
            <div className={styles.iconCircle}>
              <KeyRound />
            </div>
          </div>

          {/* Title */}
          <h1 className={styles.title}>ESCAPE LOGIN</h1>
          <p className={styles.subtitle}>
            방탈출을 통과해야 로그인됩니다. 당신의 지혜를 시험합니다.
          </p>

          {/* Form */}
          <form className={styles.form} onSubmit={handleLoginSubmit}>
            <div className={styles.inputGroup}>
              <label className={styles.label} htmlFor="login-email">
                이메일
              </label>
              <div className={styles.inputWrapper}>
                <input
                  id="login-email"
                  className={styles.input}
                  type="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  required
                />
                <Mail className={styles.inputIcon} />
              </div>
            </div>

            <div className={styles.inputGroup}>
              <label className={styles.label} htmlFor="login-password">
                비밀번호
              </label>
              <div className={styles.inputWrapper}>
                <input
                  id="login-password"
                  className={styles.input}
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
                <Lock className={styles.inputIcon} />
              </div>
            </div>

            {/* 로그인 에러 메시지 */}
            {loginError && (
              <div className={styles.errorMessage}>
                {loginError}
              </div>
            )}

            <button id="login-submit" type="submit" className={styles.submitBtn}>
              방탈출 시작
            </button>
          </form>

          {/* Footer */}
          <div className={styles.footer}>
            <Shield size={14} />
            캡챠 인증이 필요합니다
          </div>
        </div>
      </div>

      {/* Result Modal */}
      {result && (
        <ResultModal
          type={result.type}
          message={result.message}
          onClose={handleResultClose}
        />
      )}
    </div>
  );
}
