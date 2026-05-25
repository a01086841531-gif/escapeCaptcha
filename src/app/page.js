'use client';

import { useState, useCallback } from 'react';
import { KeyRound, Mail, Lock, Shield } from 'lucide-react';
import styles from './page.module.css';
import EscapeRoom from '@/components/EscapeRoom';
import ResultModal from '@/components/ResultModal';
import { getSupabase } from '@/utils/supabase/client';

export default function Home() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [showEscapeRoom, setShowEscapeRoom] = useState(false);
  const [result, setResult] = useState(null); // { type: 'success'|'fail', message: string }

  /* ─── 모드 전환 ─── */
  const handleToggleMode = useCallback(() => {
    setIsSignUp((prev) => !prev);
    setPasswordConfirm('');
    setResult(null);
  }, []);

  /* ─── 로그인/회원가입 폼 제출 → 방탈출 뷰 전환 ─── */
  const handleLoginSubmit = useCallback(
    (e) => {
      e.preventDefault();
      if (!email.trim() || !password.trim()) {
        alert('이메일과 비밀번호를 모두 입력해주세요.');
        return;
      }
      if (isSignUp) {
        if (!passwordConfirm.trim()) {
          alert('비밀번호 확인을 입력해주세요.');
          return;
        }
        if (password !== passwordConfirm) {
          alert('비밀번호가 일치하지 않습니다.');
          return;
        }
      }
      setShowEscapeRoom(true);
    },
    [email, password, isSignUp, passwordConfirm]
  );

  /* ─── 캡챠 성공 → Supabase 로그인/회원가입 시도 ─── */
  const handleCaptchaSuccess = useCallback(async () => {
    try {
      const sb = getSupabase();
      if (isSignUp) {
        const { data, error } = await sb.auth.signUp({
          email,
          password,
        });

        if (error) {
          setResult({ type: 'fail', message: '회원가입 실패: ' + error.message });
        } else {
          const autoConfirmed = data?.user && data?.session;
          const message = autoConfirmed
            ? '회원가입 및 로그인이 완료되었습니다!'
            : '회원가입 성공! 이메일 인증 메일이 발송되었을 수 있으니 메일함을 확인해주세요.';
          setResult({ type: 'success', message });
        }
      } else {
        const { data, error } = await sb.auth.signInWithPassword({
          email,
          password,
        });

        if (error) {
          // 자동 테스트 계정 생성/로그인 흐름: 개발용으로만 사용
          if (email === 'test123@test.com' && password === 'test123') {
            // 개발용: 서버에서 서비스 키로 사용자 생성(확인 완료) 후 재로그인
            try {
              const resp = await fetch('/api/dev/create-test-user', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
              });
              const json = await resp.json();
              if (!resp.ok) {
                setResult({ type: 'fail', message: '테스트 계정 생성 실패: ' + (json.error || resp.statusText) });
              } else {
                // 생성되었으니 로그인 재시도
                const retry = await sb.auth.signInWithPassword({ email, password });
                if (retry.error) {
                  setResult({ type: 'fail', message: '테스트 계정 생성은 성공했지만 로그인에 실패했습니다: ' + retry.error.message });
                } else {
                  setResult({ type: 'success', message: '테스트 계정 생성 및 로그인에 성공했습니다.' });
                }
              }
            } catch (e) {
              setResult({ type: 'fail', message: '테스트 계정 생성 중 오류가 발생했습니다: ' + e.message });
            }
          } else {
            setResult({ type: 'fail', message: '로그인 실패: ' + error.message });
          }
        } else {
          setResult({ type: 'success', message: '방탈출에 성공하셨습니다! 로그인이 완료되었습니다.' });
        }
      }
    } catch (err) {
      setResult({ type: 'fail', message: '서버 연결에 실패했습니다. 다시 시도해주세요.' });
    }
  }, [email, password, isSignUp]);

  /* ─── 캡챠 실패 ─── */
  const handleCaptchaFail = useCallback(() => {
    setResult({ type: 'fail', message: '캡챠 인증에 실패했습니다. 다시 시도해주세요.' });
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
          <h1 className={styles.title}>{isSignUp ? 'ESCAPE REGISTER' : 'ESCAPE LOGIN'}</h1>
          <p className={styles.subtitle}>
            {isSignUp ? (
              <>
                방탈출에 성공해야 회원가입할 수 있습니다.<br />
                당신의 지혜를 시험합니다.
              </>
            ) : (
              <>
                방탈출에 성공해야 로그인할 수 있습니다.<br />
                당신의 지혜를 시험합니다.
              </>
            )}
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
                  autoComplete={isSignUp ? 'new-password' : 'current-password'}
                  required
                />
                <Lock className={styles.inputIcon} />
              </div>
            </div>

            {isSignUp && (
              <div className={styles.inputGroup}>
                <label className={styles.label} htmlFor="login-password-confirm">
                  비밀번호 확인
                </label>
                <div className={styles.inputWrapper}>
                  <input
                    id="login-password-confirm"
                    className={styles.input}
                    type="password"
                    placeholder="••••••••"
                    value={passwordConfirm}
                    onChange={(e) => setPasswordConfirm(e.target.value)}
                    autoComplete="new-password"
                    required
                  />
                  <Lock className={styles.inputIcon} />
                </div>
              </div>
            )}

            <button id="login-submit" type="submit" className={styles.submitBtn}>
              {isSignUp ? '회원가입' : '방탈출 시작'}
            </button>
          </form>

          {/* Toggle Mode */}
          <div className={styles.toggleMode}>
            {isSignUp ? (
              <>
                이미 계정이 있으신가요?
                <button type="button" className={styles.toggleLink} onClick={handleToggleMode}>
                  로그인하기
                </button>
              </>
            ) : (
              <>
                아직 계정이 없으신가요?
                <button type="button" className={styles.toggleLink} onClick={handleToggleMode}>
                  회원가입하기
                </button>
              </>
            )}
          </div>

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
