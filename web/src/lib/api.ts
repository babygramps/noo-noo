/**
 * API client for the EPDM Vacuum Fixture backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export interface APIResponse<T = unknown> {
  success: boolean;
  message: string;
  data?: T;
}

export interface SensorData {
  timestamp: number;
  datetime: string;
  vacuum_bar: number;
  pressure_psi: number;
  pressure_mA?: number;
  pressure_voltage?: number;
  gross_weight_kg: number;
  total_force_kg?: number;
  load_cell_1_kg: number;
  load_cell_2_kg: number;
  load_cell_3_kg: number;
  load_cell_4_kg: number;
  test_running: boolean;
  sequence_name?: string;
}

export interface SystemStatus {
  connected: boolean;
  widgetlords_connected: boolean;
  modbus_connected: boolean;
  test_running: boolean;
  current_sequence: string | null;
  websocket_connections?: number;
}

export interface TestStatus {
  running: boolean;
  sequence: string | null;
  state?: string;
  stage_index?: number;
  total_stages?: number;
}

export interface SequenceSummary {
  name: string;  // Filename used for API lookups
  display_name?: string;  // Human-readable name from YAML
  description: string;
  stages: number;
  cycles: number;
}

export interface Sequence {
  name: string;
  description: string;
  cycles: number;
  stages: Stage[];
  created_date?: string;
  modified_date?: string;
  author?: string;
}

export interface Stage {
  name: string;
  target_vacuum_bar: number | null;
  max_time_seconds: number | null;
  min_time_seconds: number;
  pump_mode: 'continuous' | 'maintain' | 'off';
  vacuum_tolerance_bar: number;
  collect_data: boolean;
  io_actions: IOAction[];
}

export interface IOAction {
  device_name: string;
  action_type: 'digital_output' | 'analog_output' | 'pulse';
  value: boolean | number;
  timing: 'before_stage' | 'start_of_stage' | 'during_stage' | 'end_of_stage' | 'after_stage';
  delay_seconds: number;
  duration_seconds: number | null;
  description: string;
}

export interface IOStates {
  vacuum_pump?: boolean;
  vacuum_valve?: boolean;
  vent_valve?: boolean;
  [key: string]: boolean | undefined;
}

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<APIResponse<T>> {
  const url = `${API_BASE}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  
  return response.json();
}

// System Status
export async function getStatus(): Promise<SystemStatus> {
  const response = await fetchAPI<SystemStatus>('/api/status');
  return response.data!;
}

// Sensor Data
export async function getSensors(): Promise<SensorData> {
  const response = await fetchAPI<SensorData>('/api/sensors');
  return response.data!;
}

// IO States
export async function getIOStates(): Promise<IOStates> {
  const response = await fetchAPI<IOStates>('/api/io/states');
  return response.data!;
}

// Pump Control
export async function pumpOn(): Promise<APIResponse> {
  return fetchAPI('/api/pump/on', { method: 'POST' });
}

export async function pumpOff(): Promise<APIResponse> {
  return fetchAPI('/api/pump/off', { method: 'POST' });
}

// Valve Control
export async function controlValve(
  valveName: string,
  action: 'open' | 'close'
): Promise<APIResponse> {
  return fetchAPI(`/api/valve/${valveName}/${action}`, { method: 'POST' });
}

// Tare
export async function tareLoadCells(): Promise<APIResponse> {
  return fetchAPI('/api/tare', { method: 'POST' });
}

// Test Control
export async function startTest(
  sequenceName: string,
  metadata?: Record<string, unknown>
): Promise<APIResponse> {
  return fetchAPI('/api/test/start', {
    method: 'POST',
    body: JSON.stringify({
      sequence_name: sequenceName,
      metadata,
    }),
  });
}

export async function stopTest(): Promise<APIResponse> {
  return fetchAPI('/api/test/stop', { method: 'POST' });
}

export async function getTestStatus(): Promise<TestStatus> {
  const response = await fetchAPI<TestStatus>('/api/test/status');
  return response.data!;
}

// Sequences
export async function listSequences(): Promise<SequenceSummary[]> {
  const response = await fetchAPI<{ sequences: SequenceSummary[] }>('/api/sequences');
  return response.data?.sequences || [];
}

export async function getSequence(name: string): Promise<Sequence> {
  const response = await fetchAPI<Sequence>(`/api/sequences/${encodeURIComponent(name)}`);
  return response.data!;
}

export async function saveSequence(sequence: Sequence): Promise<APIResponse> {
  return fetchAPI('/api/sequences', {
    method: 'POST',
    body: JSON.stringify(sequence),
  });
}

export async function deleteSequence(name: string): Promise<APIResponse> {
  return fetchAPI(`/api/sequences/${encodeURIComponent(name)}`, {
    method: 'DELETE',
  });
}

// Test Data Files
export interface TestDataFile {
  filename: string;
  file_type: 'csv' | 'json';
  size_bytes: number;
  size_formatted: string;
  modified_time: string;
  modified_timestamp: number;
  test_name: string | null;
  test_id: string | null;
  operator: string | null;
  sequence_name: string | null;
  has_metadata: boolean;
}

export async function listTestData(): Promise<TestDataFile[]> {
  const response = await fetchAPI<{ files: TestDataFile[] }>('/api/data');
  return response.data?.files || [];
}

export async function getTestMetadata(filename: string): Promise<Record<string, unknown>> {
  const response = await fetchAPI<Record<string, unknown>>(`/api/data/${encodeURIComponent(filename)}/metadata`);
  return response.data || {};
}

export async function deleteTestData(filename: string): Promise<APIResponse> {
  return fetchAPI(`/api/data/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
  });
}

export function getTestDataDownloadUrl(filename: string): string {
  return `${API_BASE}/api/data/${encodeURIComponent(filename)}`;
}

