'use client';

import { useState } from 'react';
import Image from 'next/image';
import { Search, KeyRound, Eye } from 'lucide-react';
import styles from './EscapeRoom.module.css';
import CaptchaModal from './CaptchaModal';

/* ────────────────────────────────────────────
   EscapeRoom Component
   - 방탈출 배경 이미지 위에 돋보기 핫스팟
   - 핫스팟 클릭 시 CaptchaModal 오픈
──────────────────────────────────────────── */
export default function EscapeRoom({ onCaptchaSuccess, onCaptchaFail }) {
  const [showCaptcha, setShowCaptcha] = useState(false);

  const handleHotspotClick = () => {
    setShowCaptcha(true);
  };

  const handleCaptchaSuccess = () => {
    setShowCaptcha(false);
    onCaptchaSuccess();
  };

  const handleCaptchaFail = () => {
    setShowCaptcha(false);
    onCaptchaFail();
  };

  return (
    <div className={styles.escapeRoom}>
      {/* Room Background */}
      <div className={styles.roomImageWrapper}>
        <Image
          src="/escape_room_bg.png"
          alt="방탈출 배경"
          fill
          className={styles.roomImage}
          priority
          quality={90}
        />
        <div className={styles.vignette} />
      </div>

      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerTitle}>
          <KeyRound size={20} />
          ESCAPE ROOM
        </div>
        <div className={styles.hint}>
          <Eye size={16} />
          돋보기를 찾아 클릭하세요
        </div>
      </div>

      {/* Hotspot 1 – 책장 근처 (왼쪽 상단 영역) */}
      <div
        className={styles.hotspot}
        style={{ top: '35%', left: '22%' }}
        onClick={handleHotspotClick}
        id="hotspot-bookshelf"
      >
        <div className={styles.hotspotRipple} />
        <div className={styles.hotspotInner}>
          <Search size={24} />
        </div>
        <span className={styles.hotspotLabel}>수상한 단서</span>
      </div>

      {/* Hotspot 2 – 책상 근처 (중앙 하단) */}
      <div
        className={styles.hotspot}
        style={{ top: '60%', left: '55%' }}
        onClick={handleHotspotClick}
        id="hotspot-desk"
      >
        <div className={styles.hotspotRipple} />
        <div className={styles.hotspotInner}>
          <Search size={24} />
        </div>
        <span className={styles.hotspotLabel}>숨겨진 메모</span>
      </div>

      {/* Hotspot 3 – 금고 근처 (오른쪽) */}
      <div
        className={styles.hotspot}
        style={{ top: '40%', left: '78%' }}
        onClick={handleHotspotClick}
        id="hotspot-safe"
      >
        <div className={styles.hotspotRipple} />
        <div className={styles.hotspotInner}>
          <Search size={24} />
        </div>
        <span className={styles.hotspotLabel}>잠긴 금고</span>
      </div>

      {/* Captcha Modal */}
      {showCaptcha && (
        <CaptchaModal
          onSuccess={handleCaptchaSuccess}
          onFail={handleCaptchaFail}
          onClose={() => setShowCaptcha(false)}
        />
      )}
    </div>
  );
}
