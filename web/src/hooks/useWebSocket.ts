'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import type { SensorData, IOStates } from '@/lib/api';

export interface WebSocketMessage {
  type: 'sensor_data' | 'status' | 'stage_change' | 'progress' | 'io_change' | 'test_complete' | 'error' | 'connected' | 'heartbeat' | 'pong';
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

interface UseWebSocketOptions {
  onSensorData?: (data: SensorData) => void;
  onStatusMessage?: (message: string) => void;
  onStageChange?: (data: StageChangeData) => void;
  onProgress?: (data: ProgressData) => void;
  onIOChange?: (data: IOChangeData) => void;
  onTestComplete?: () => void;
  onError?: (error: string) => void;
  onConnected?: (data: unknown) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    // Determine WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NEXT_PUBLIC_WS_HOST || window.location.host;
    const wsUrl = `${protocol}//${host}/api/ws`;

    console.log('[WebSocket] Connecting to:', wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WebSocket] Connected');
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
      setIsConnected(false);

      // Clear ping interval
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }

      // Reconnect after delay
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('[WebSocket] Attempting reconnect...');
        connect();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        setLastMessage(message);

        // Route message to appropriate handler
        switch (message.type) {
          case 'sensor_data':
            options.onSensorData?.(message.data as SensorData);
            break;

          case 'status':
            options.onStatusMessage?.(message.message || '');
            break;

          case 'stage_change':
            options.onStageChange?.(message.data as StageChangeData);
            break;

          case 'progress':
            options.onProgress?.(message.data as ProgressData);
            break;

          case 'io_change':
            options.onIOChange?.(message.data as IOChangeData);
            break;

          case 'test_complete':
            options.onTestComplete?.();
            break;

          case 'error':
            options.onError?.(message.message || 'Unknown error');
            break;

          case 'connected':
            options.onConnected?.(message.data);
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
  }, [options]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const send = useCallback((message: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

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
    clearHistory,
  };
}


