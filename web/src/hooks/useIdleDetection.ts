'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

interface UseIdleDetectionOptions {
  /** Time in milliseconds before user is considered idle (default: 60000 = 60 seconds) */
  idleTimeout?: number;
  /** Events to track for activity (default: mouse, keyboard, touch, scroll) */
  events?: string[];
  /** Enable console logging for debugging */
  debug?: boolean;
}

/**
 * Hook to detect user idle state based on mouse, keyboard, and touch activity.
 * Returns true when user has been idle for longer than the specified timeout.
 */
export function useIdleDetection(options: UseIdleDetectionOptions = {}) {
  const {
    idleTimeout = 60000, // 60 seconds default
    events = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'wheel'],
    debug = true, // Enable by default for now
  } = options;

  const [isIdle, setIsIdle] = useState(false);
  const [idleTime, setIdleTime] = useState(0);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastActivityRef = useRef<number>(Date.now());
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const activityCountRef = useRef<number>(0);

  // Reset idle timer on activity
  const handleActivity = useCallback((event?: Event) => {
    lastActivityRef.current = Date.now();
    activityCountRef.current += 1;
    
    // Log every 10th activity to avoid spam (or first few)
    if (debug && (activityCountRef.current <= 3 || activityCountRef.current % 10 === 0)) {
      console.log(`[IdleDetection] Activity detected: ${event?.type || 'manual'} (count: ${activityCountRef.current})`);
    }
    
    // If currently idle, immediately set to not idle
    if (isIdle) {
      if (debug) {
        console.log('[IdleDetection] User became ACTIVE (was idle)');
      }
      setIsIdle(false);
      setIdleTime(0);
    }

    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Set new timeout
    timeoutRef.current = setTimeout(() => {
      if (debug) {
        console.log(`[IdleDetection] User became IDLE after ${idleTimeout / 1000}s of inactivity`);
      }
      setIsIdle(true);
    }, idleTimeout);
  }, [idleTimeout, isIdle, debug]);

  // Set up event listeners
  useEffect(() => {
    if (debug) {
      console.log(`[IdleDetection] Initializing with ${idleTimeout / 1000}s timeout, tracking events:`, events);
    }
    
    // Initial timeout setup
    timeoutRef.current = setTimeout(() => {
      if (debug) {
        console.log(`[IdleDetection] Initial idle timeout reached (${idleTimeout / 1000}s)`);
      }
      setIsIdle(true);
    }, idleTimeout);

    // Add event listeners
    const wrappedHandler = (event: Event) => handleActivity(event);
    events.forEach(event => {
      window.addEventListener(event, wrappedHandler, { passive: true });
    });
    
    if (debug) {
      console.log('[IdleDetection] Event listeners attached');
    }

    // Track idle time for display purposes
    intervalRef.current = setInterval(() => {
      const elapsed = Date.now() - lastActivityRef.current;
      setIdleTime(elapsed);
      
      // Log every 10 seconds when approaching idle threshold
      if (debug && elapsed > 0 && elapsed % 10000 < 1000) {
        console.log(`[IdleDetection] Idle time: ${Math.floor(elapsed / 1000)}s / ${idleTimeout / 1000}s threshold`);
      }
    }, 1000);

    // Cleanup
    return () => {
      if (debug) {
        console.log('[IdleDetection] Cleaning up event listeners');
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      events.forEach(event => {
        window.removeEventListener(event, wrappedHandler);
      });
    };
  }, [events, handleActivity, idleTimeout, debug]);

  // Log state changes
  useEffect(() => {
    if (debug) {
      console.log(`[IdleDetection] State: isIdle=${isIdle}, idleTime=${Math.floor(idleTime / 1000)}s`);
    }
  }, [isIdle, idleTime, debug]);

  return {
    /** Whether the user is currently idle (no activity for idleTimeout ms) */
    isIdle,
    /** Time in milliseconds since last activity */
    idleTime,
    /** Manually reset the idle timer (e.g., after programmatic action) */
    resetIdleTimer: handleActivity,
  };
}

