'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

interface UseIdleDetectionOptions {
  /** Time in milliseconds before user is considered idle (default: 60000 = 60 seconds) */
  idleTimeout?: number;
  /** Events to track for activity (default: mouse, keyboard, touch, scroll) */
  events?: string[];
  /** Enable console logging for debugging */
  debug?: boolean;
}

// Static events array to prevent re-renders
const DEFAULT_EVENTS = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'wheel'];

/**
 * Hook to detect user idle state based on mouse, keyboard, and touch activity.
 * Returns true when user has been idle for longer than the specified timeout.
 */
export function useIdleDetection(options: UseIdleDetectionOptions = {}) {
  const {
    idleTimeout = 60000, // 60 seconds default
    events = DEFAULT_EVENTS,
    debug = true, // Enable by default for now
  } = options;

  const [isIdle, setIsIdle] = useState(false);
  const [idleTime, setIdleTime] = useState(0);
  
  // Use refs to avoid dependency issues in callbacks
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastActivityRef = useRef<number>(Date.now());
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const activityCountRef = useRef<number>(0);
  const isIdleRef = useRef<boolean>(false);
  const debugRef = useRef<boolean>(debug);
  const idleTimeoutRef = useRef<number>(idleTimeout);
  
  // Keep refs in sync
  debugRef.current = debug;
  idleTimeoutRef.current = idleTimeout;

  // Set up event listeners - only run once on mount
  useEffect(() => {
    const logDebug = debugRef.current;
    const timeout = idleTimeoutRef.current;
    
    if (logDebug) {
      console.log(`[IdleDetection] Initializing with ${timeout / 1000}s timeout`);
    }
    
    // Handler function that uses refs to avoid stale closures
    const handleActivity = (event?: Event) => {
      lastActivityRef.current = Date.now();
      activityCountRef.current += 1;
      
      // Log every 10th activity to avoid spam (or first few)
      if (debugRef.current && (activityCountRef.current <= 3 || activityCountRef.current % 50 === 0)) {
        console.log(`[IdleDetection] Activity: ${event?.type || 'manual'} (count: ${activityCountRef.current})`);
      }
      
      // If currently idle, immediately set to not idle
      if (isIdleRef.current) {
        if (debugRef.current) {
          console.log('[IdleDetection] User became ACTIVE (was idle)');
        }
        isIdleRef.current = false;
        setIsIdle(false);
        setIdleTime(0);
      }

      // Clear existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      // Set new timeout
      timeoutRef.current = setTimeout(() => {
        if (debugRef.current) {
          console.log(`[IdleDetection] User became IDLE after ${idleTimeoutRef.current / 1000}s of inactivity`);
        }
        isIdleRef.current = true;
        setIsIdle(true);
      }, idleTimeoutRef.current);
    };
    
    // Initial timeout setup
    timeoutRef.current = setTimeout(() => {
      if (debugRef.current) {
        console.log(`[IdleDetection] Initial idle timeout reached (${timeout / 1000}s)`);
      }
      isIdleRef.current = true;
      setIsIdle(true);
    }, timeout);

    // Add event listeners
    events.forEach(eventName => {
      window.addEventListener(eventName, handleActivity, { passive: true });
    });
    
    if (logDebug) {
      console.log('[IdleDetection] Event listeners attached');
    }

    // Track idle time for display purposes (update every 5 seconds to reduce logs)
    intervalRef.current = setInterval(() => {
      const elapsed = Date.now() - lastActivityRef.current;
      setIdleTime(elapsed);
      
      // Log every 10 seconds
      if (debugRef.current && elapsed > 0 && Math.floor(elapsed / 1000) % 10 === 0) {
        console.log(`[IdleDetection] Idle time: ${Math.floor(elapsed / 1000)}s / ${idleTimeoutRef.current / 1000}s threshold, isIdle: ${isIdleRef.current}`);
      }
    }, 1000);

    // Cleanup
    return () => {
      if (debugRef.current) {
        console.log('[IdleDetection] Cleaning up (component unmount)');
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      events.forEach(eventName => {
        window.removeEventListener(eventName, handleActivity);
      });
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty deps - only run once on mount

  // Manual reset function
  const resetIdleTimer = useCallback(() => {
    lastActivityRef.current = Date.now();
    if (isIdleRef.current) {
      isIdleRef.current = false;
      setIsIdle(false);
      setIdleTime(0);
    }
    
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    timeoutRef.current = setTimeout(() => {
      isIdleRef.current = true;
      setIsIdle(true);
    }, idleTimeoutRef.current);
  }, []);

  return {
    /** Whether the user is currently idle (no activity for idleTimeout ms) */
    isIdle,
    /** Time in milliseconds since last activity */
    idleTime,
    /** Manually reset the idle timer (e.g., after programmatic action) */
    resetIdleTimer,
  };
}

