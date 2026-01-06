'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

interface UseIdleDetectionOptions {
  /** Time in milliseconds before user is considered idle (default: 60000 = 60 seconds) */
  idleTimeout?: number;
  /** Events to track for activity (default: mouse, keyboard, touch, scroll) */
  events?: string[];
}

/**
 * Hook to detect user idle state based on mouse, keyboard, and touch activity.
 * Returns true when user has been idle for longer than the specified timeout.
 */
export function useIdleDetection(options: UseIdleDetectionOptions = {}) {
  const {
    idleTimeout = 60000, // 60 seconds default
    events = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'wheel'],
  } = options;

  const [isIdle, setIsIdle] = useState(false);
  const [idleTime, setIdleTime] = useState(0);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastActivityRef = useRef<number>(Date.now());
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Reset idle timer on activity
  const handleActivity = useCallback(() => {
    lastActivityRef.current = Date.now();
    
    // If currently idle, immediately set to not idle
    if (isIdle) {
      setIsIdle(false);
      setIdleTime(0);
    }

    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Set new timeout
    timeoutRef.current = setTimeout(() => {
      setIsIdle(true);
    }, idleTimeout);
  }, [idleTimeout, isIdle]);

  // Set up event listeners
  useEffect(() => {
    // Initial timeout setup
    timeoutRef.current = setTimeout(() => {
      setIsIdle(true);
    }, idleTimeout);

    // Add event listeners
    events.forEach(event => {
      window.addEventListener(event, handleActivity, { passive: true });
    });

    // Track idle time for display purposes
    intervalRef.current = setInterval(() => {
      const elapsed = Date.now() - lastActivityRef.current;
      setIdleTime(elapsed);
    }, 1000);

    // Cleanup
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      events.forEach(event => {
        window.removeEventListener(event, handleActivity);
      });
    };
  }, [events, handleActivity, idleTimeout]);

  return {
    /** Whether the user is currently idle (no activity for idleTimeout ms) */
    isIdle,
    /** Time in milliseconds since last activity */
    idleTime,
    /** Manually reset the idle timer (e.g., after programmatic action) */
    resetIdleTimer: handleActivity,
  };
}

