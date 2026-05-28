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
  const allEventsRef = useRef([]);
  const timerRef = useRef(null);
  const sessionIdRef = useRef(null);
  const startTimeRef = useRef(Date.now());

  function captureCommon(e, overrideType = null) {
    const t = e.target || null;
    const target = t && t.tagName ? {
      tag: t.tagName,
      id: t.id || null,
      classes: t.className || null,
    } : null;

    const x = e.clientX ?? e.pageX ?? null;
    const y = e.clientY ?? e.pageY ?? null;

    return {
      type: overrideType || e.type,
      time: new Date().toISOString(),
      elapsed_ms: Date.now() - startTimeRef.current,
      target,
      clientX: e.clientX ?? null,
      clientY: e.clientY ?? null,
      pageX: e.pageX ?? null,
      pageY: e.pageY ?? null,
      x,
      y,
      key: e.key ?? null,
    };
  }

  useEffect(() => {
    if (!enabled) return;

    startTimeRef.current = startTimeRef.current || Date.now();
    sessionIdRef.current = sessionIdRef.current || safeGet(() => (crypto && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)));

    let lastScroll = 0;
    let lastMove = 0;

    const handlers = {
      click(e) {
        const event = captureCommon(e);
        bufferRef.current.push(event);
        allEventsRef.current.push(event);
        maybeFlush();
      },
      mousedown(e) {
        const event = captureCommon(e);
        bufferRef.current.push(event);
        allEventsRef.current.push(event);
        maybeFlush();
      },
      mouseup(e) {
        const event = captureCommon(e);
        bufferRef.current.push(event);
        allEventsRef.current.push(event);
        maybeFlush();
      },
      keydown(e) {
        const event = captureCommon(e);
        bufferRef.current.push(event);
        allEventsRef.current.push(event);
        maybeFlush();
      },
      mousemove(e) {
        const now = Date.now();
        if (now - lastMove < 100) return;
        lastMove = now;
        const event = captureCommon(e, 'move');
        bufferRef.current.push(event);
        allEventsRef.current.push(event);
        maybeFlush();
      },
      touchmove(e) {
        const now = Date.now();
        if (now - lastMove < 100) return;
        lastMove = now;
        const event = captureCommon(e, 'move');
        bufferRef.current.push(event);
        allEventsRef.current.push(event);
        maybeFlush();
      },
      scroll() {
        const now = Date.now();
        if (now - lastScroll < 200) return; // throttle scroll
        lastScroll = now;
        const event = {
          type: 'scroll',
          time: new Date().toISOString(),
          elapsed_ms: Date.now() - startTimeRef.current,
          scrollX: safeGet(() => window.scrollX, null),
          scrollY: safeGet(() => window.scrollY, null),
        };
        bufferRef.current.push(event);
        allEventsRef.current.push(event);
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
        if (timerRef.current) {
          clearTimeout(timerRef.current);
          timerRef.current = null;
        }
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
        await fetch('/api/events', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } catch (err) {
        console.error('Event flush failed', err);
      } finally {
        if (timerRef.current) {
          clearTimeout(timerRef.current);
          timerRef.current = null;
        }
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

    window.addEventListener('click', handlers.click, true);
    window.addEventListener('mousedown', handlers.mousedown, true);
    window.addEventListener('mouseup', handlers.mouseup, true);
    window.addEventListener('keydown', handlers.keydown, true);
    window.addEventListener('mousemove', handlers.mousemove, true);
    window.addEventListener('touchmove', handlers.touchmove, { passive: true });
    window.addEventListener('scroll', handlers.scroll, { passive: true });
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('click', handlers.click, true);
      window.removeEventListener('mousedown', handlers.mousedown, true);
      window.removeEventListener('mouseup', handlers.mouseup, true);
      window.removeEventListener('keydown', handlers.keydown, true);
      window.removeEventListener('mousemove', handlers.mousemove, true);
      window.removeEventListener('touchmove', handlers.touchmove);
      window.removeEventListener('scroll', handlers.scroll);
      window.removeEventListener('beforeunload', handleBeforeUnload);
      if (timerRef.current) clearTimeout(timerRef.current);
      if (bufferRef.current.length) {
        try {
          navigator.sendBeacon(
            '/api/events',
            new Blob([
              JSON.stringify({
                session_id: sessionIdRef.current,
                page: safeGet(() => window.location.pathname, null),
                user_agent: safeGet(() => navigator.userAgent, null),
                events: bufferRef.current,
              })], { type: 'application/json' }
            )
          );
        } catch (e) {
          // ignore
        }
      }
    };
  }, [enabled, flushInterval, batchSize]);

  return {
    getAllEvents: () => allEventsRef.current.slice(),
    getSessionId: () => sessionIdRef.current,
  };
}
