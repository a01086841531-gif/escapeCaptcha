'use client';

import { useEffect, useRef } from 'react';

function safeGet(fn, fallback = null) {
  try {
    return fn();
  } catch (e) {
    return fallback;
  }
}

export default function useEventLogger(options = {}) {
  const { enabled = true, flushInterval = 3000, batchSize = 20 } = options;
  const bufferRef = useRef([]);
  const timerRef = useRef(null);
  const sessionIdRef = useRef(null);

  useEffect(() => {
    if (!enabled) return;

    sessionIdRef.current = sessionIdRef.current || safeGet(() => (crypto && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)));

    function captureCommon(e) {
      const t = e.target || null;
      const target = t && t.tagName ? {
        tag: t.tagName,
        id: t.id || null,
        classes: t.className || null,
      } : null;

      return {
        type: e.type,
        time: new Date().toISOString(),
        target,
        // position if available
        clientX: e.clientX ?? null,
        clientY: e.clientY ?? null,
        pageX: e.pageX ?? null,
        pageY: e.pageY ?? null,
        key: e.key ?? null,
      };
    }

    let lastScroll = 0;

    const handlers = {
      click(e) { bufferRef.current.push(captureCommon(e)); maybeFlush(); },
      mousedown(e) { bufferRef.current.push(captureCommon(e)); maybeFlush(); },
      mouseup(e) { bufferRef.current.push(captureCommon(e)); maybeFlush(); },
      keydown(e) { bufferRef.current.push(captureCommon(e)); maybeFlush(); },
      touchmove(e) {
        bufferRef.current.push(captureCommon(e)); maybeFlush();
      },
      scroll(e) {
        const now = Date.now();
        if (now - lastScroll < 200) return; // throttle scroll
        lastScroll = now;
        bufferRef.current.push({
          type: 'scroll',
          time: new Date().toISOString(),
          scrollX: safeGet(() => window.scrollX, null),
          scrollY: safeGet(() => window.scrollY, null),
        });
        maybeFlush();
      },
    };

    function maybeFlush() {
      if (bufferRef.current.length >= batchSize) flush();
      if (!timerRef.current) {
        timerRef.current = setTimeout(() => { flush(); }, flushInterval);
      }
    }

    async function flush() {
      if (!bufferRef.current.length) {
        if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
        return;
      }

      const events = bufferRef.current.splice(0, bufferRef.current.length);
      if (!events.length) return;

      const payload = {
        session_id: sessionIdRef.current,
        page: safeGet(() => window.location.pathname, null),
        user_agent: safeGet(() => navigator.userAgent, null),
        events,
      };

      try {
        // Try fetch; do not await to avoid blocking UI
        await fetch('/api/events', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } catch (err) {
        // ignore network errors; events are lost in this simple implementation
        console.error('Event flush failed', err);
      } finally {
        if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
      }
    }

    function handleBeforeUnload() {
      if (!bufferRef.current.length) return;
      try {
        const payload = JSON.stringify({
          session_id: sessionIdRef.current,
          page: safeGet(() => window.location.pathname, null),
          user_agent: safeGet(() => navigator.userAgent, null),
          events: bufferRef.current,
        });
        navigator.sendBeacon('/api/events', new Blob([payload], { type: 'application/json' }));
      } catch (e) {
        // fallback: nothing
      }
    }

    // attach listeners
    window.addEventListener('click', handlers.click, true);
    window.addEventListener('mousedown', handlers.mousedown, true);
    window.addEventListener('mouseup', handlers.mouseup, true);
    window.addEventListener('keydown', handlers.keydown, true);
    window.addEventListener('touchmove', handlers.touchmove, { passive: true });
    window.addEventListener('scroll', handlers.scroll, { passive: true });
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('click', handlers.click, true);
      window.removeEventListener('mousedown', handlers.mousedown, true);
      window.removeEventListener('mouseup', handlers.mouseup, true);
      window.removeEventListener('keydown', handlers.keydown, true);
      window.removeEventListener('touchmove', handlers.touchmove);
      window.removeEventListener('scroll', handlers.scroll);
      window.removeEventListener('beforeunload', handleBeforeUnload);
      if (timerRef.current) clearTimeout(timerRef.current);
      // try a final flush
      if (bufferRef.current.length) {
        try { navigator.sendBeacon('/api/events', new Blob([JSON.stringify({ session_id: sessionIdRef.current, page: safeGet(() => window.location.pathname, null), user_agent: safeGet(() => navigator.userAgent, null), events: bufferRef.current })], { type: 'application/json' })); } catch (e) {}
      }
    };
  }, [enabled, flushInterval, batchSize]);
}
