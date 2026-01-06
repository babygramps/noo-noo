'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import type { SensorData, IOStates } from '@/lib/api';

export interface WebSocketMessage {
  type: 'sensor_data' | 'status' | 'stage_change' | 'progress' | 'io_change' | 'test_complete' | 'error' | 'connected' | 'heartbeat' | 'pong' | 'joke';
  data?: unknown;
  message?: string;
  timestamp?: string;
}

export interface StageChangeData {
  stage_index: number;
  stage_name: string;
  stages_per_cycle: number;
  current_cycle: number;
  total_cycles: number;
}

export interface ProgressData {
  progress: number;
  status: string;
}

export interface IOChangeData {
  device: string;
  state: boolean;
}

export interface JokeData {
  line1: string;
  line2: string;
}

interface UseWebSocketOptions {
  onSensorData?: (data: SensorData) => void;
  onStatusMessage?: (message: string) => void;
  onStageChange?: (data: StageChangeData) => void;
  onProgress?: (data: ProgressData) => void;
  onIOChange?: (data: IOChangeData) => void;
  onTestComplete?: () => void;
  onError?: (error: string) => void;
  onConnected?: (data: unknown) => void;
  onJoke?: (data: JokeData) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isConnectingRef = useRef(false);
  const isMountedRef = useRef(true);
  
  // Use refs for callbacks to avoid dependency issues
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const cleanup = useCallback(() => {
    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Clear ping interval
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    // Prevent multiple simultaneous connection attempts
    if (isConnectingRef.current) {
      console.log('[WebSocket] Already connecting, skipping...');
      return;
    }
    
    // Don't connect if unmounted
    if (!isMountedRef.current) {
      console.log('[WebSocket] Component unmounted, skipping connect...');
      return;
    }

    // Clean up any existing connection first
    cleanup();
    
    if (wsRef.current) {
      console.log('[WebSocket] Closing existing connection before reconnect');
      const oldWs = wsRef.current;
      wsRef.current = null;
      // Remove event handlers to prevent triggering reconnect
      oldWs.onclose = null;
      oldWs.onerror = null;
      oldWs.onmessage = null;
      oldWs.onopen = null;
      oldWs.close();
    }

    isConnectingRef.current = true;

    // Determine WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NEXT_PUBLIC_WS_HOST || window.location.host;
    const wsUrl = `${protocol}//${host}/api/ws`;

    console.log('[WebSocket] Connecting to:', wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WebSocket] Connected');
      isConnectingRef.current = false;
      
      if (!isMountedRef.current) {
        ws.close();
        return;
      }
      
      setIsConnected(true);

      // Start ping interval
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 25000);
    };

    ws.onclose = (event) => {
      console.log('[WebSocket] Disconnected:', event.code, event.reason);
      isConnectingRef.current = false;
      
      if (!isMountedRef.current) {
        return;
      }
      
      setIsConnected(false);

      // Clear ping interval
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }

      // Only reconnect if component is still mounted and this is our current ws
      if (isMountedRef.current && wsRef.current === ws) {
        reconnectTimeoutRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            console.log('[WebSocket] Attempting reconnect...');
            connect();
          }
        }, 3000);
      }
    };

    ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
      isConnectingRef.current = false;
    };

    ws.onmessage = (event) => {
      if (!isMountedRef.current) return;
      
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        setLastMessage(message);

        // Route message to appropriate handler (using ref to get latest callbacks)
        const opts = optionsRef.current;
        switch (message.type) {
          case 'sensor_data':
            opts.onSensorData?.(message.data as SensorData);
            break;

          case 'status':
            opts.onStatusMessage?.(message.message || '');
            break;

          case 'stage_change':
            opts.onStageChange?.(message.data as StageChangeData);
            break;

          case 'progress':
            opts.onProgress?.(message.data as ProgressData);
            break;

          case 'io_change':
            opts.onIOChange?.(message.data as IOChangeData);
            break;

          case 'test_complete':
            opts.onTestComplete?.();
            break;

          case 'error':
            opts.onError?.(message.message || 'Unknown error');
            break;

          case 'connected':
            opts.onConnected?.(message.data);
            break;

          case 'joke':
            opts.onJoke?.(message.data as JokeData);
            break;

          case 'heartbeat':
          case 'pong':
            // Heartbeat/pong - connection is alive
            break;

          default:
            console.log('[WebSocket] Unknown message type:', message.type);
        }
      } catch (error) {
        console.error('[WebSocket] Failed to parse message:', error);
      }
    };
  }, [cleanup]);

  const disconnect = useCallback(() => {
    cleanup();

    if (wsRef.current) {
      const ws = wsRef.current;
      wsRef.current = null;
      // Remove event handlers to prevent triggering reconnect
      ws.onclose = null;
      ws.onerror = null;
      ws.onmessage = null;
      ws.onopen = null;
      ws.close();
    }
    
    setIsConnected(false);
    isConnectingRef.current = false;
  }, [cleanup]);

  const send = useCallback((message: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    isMountedRef.current = true;
    connect();

    return () => {
      isMountedRef.current = false;
      disconnect();
    };
  }, []); // Empty dependency array - only run on mount/unmount

  return {
    isConnected,
    lastMessage,
    send,
    reconnect: connect,
  };
}

// Hook specifically for sensor data with buffering for charts
export function useSensorData(maxDataPoints: number = 600) {
  const [currentData, setCurrentData] = useState<SensorData | null>(null);
  const [dataHistory, setDataHistory] = useState<SensorData[]>([]);
  const [ioStates, setIOStates] = useState<IOStates>({});
  const [stageInfo, setStageInfo] = useState<StageChangeData | null>(null);
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [testRunning, setTestRunning] = useState(false);
  const [currentJoke, setCurrentJoke] = useState<JokeData | null>(null);

  const { isConnected } = useWebSocket({
    onSensorData: (data) => {
      setCurrentData(data);
      setTestRunning(data.test_running);
      
      // Add to history for charts
      setDataHistory((prev) => {
        const newHistory = [...prev, data];
        // Keep only last N points
        if (newHistory.length > maxDataPoints) {
          return newHistory.slice(-maxDataPoints);
        }
        return newHistory;
      });
    },
    onIOChange: ({ device, state }) => {
      setIOStates((prev) => ({ ...prev, [device]: state }));
    },
    onStageChange: (data) => {
      setStageInfo(data);
      // Clear joke when test starts
      setCurrentJoke(null);
    },
    onProgress: (data) => {
      setProgress(data);
    },
    onStatusMessage: (message) => {
      setStatusMessage(message);
    },
    onTestComplete: () => {
      setTestRunning(false);
      setStageInfo(null);
      setProgress(null);
      setStatusMessage('Test complete');
    },
    onError: (error) => {
      console.error('[SensorData] Error:', error);
      setStatusMessage(`Error: ${error}`);
    },
    onConnected: (data) => {
      console.log('[SensorData] Connected with initial data:', data);
    },
    onJoke: (data) => {
      // Only show jokes when not testing
      if (!testRunning) {
        setCurrentJoke(data);
      }
    },
  });

  // Clear history
  const clearHistory = useCallback(() => {
    setDataHistory([]);
  }, []);

  return {
    isConnected,
    currentData,
    dataHistory,
    ioStates,
    stageInfo,
    progress,
    statusMessage,
    testRunning,
    currentJoke,
    clearHistory,
  };
}


