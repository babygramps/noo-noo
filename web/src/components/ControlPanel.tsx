'use client';

import { useState, useCallback } from 'react';
import { clsx } from 'clsx';
import { Play, Square, Power, Wind } from 'lucide-react';
import * as api from '@/lib/api';
import type { IOStates, SequenceSummary } from '@/lib/api';

interface ControlPanelProps {
  testRunning: boolean;
  ioStates: IOStates;
  sequences: SequenceSummary[];
  selectedSequence: string | null;
  onSequenceSelect: (name: string) => void;
  onTestStarted?: () => void;
  onTestStopped?: () => void;
}

export function ControlPanel({
  testRunning,
  ioStates,
  sequences,
  selectedSequence,
  onSequenceSelect,
  onTestStarted,
  onTestStopped,
}: ControlPanelProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleStartTest = useCallback(async () => {
    if (!selectedSequence) {
      setError('Please select a sequence first');
      return;
    }

    setLoading('start');
    setError(null);

    try {
      const result = await api.startTest(selectedSequence);
      if (result.success) {
        onTestStarted?.();
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start test');
    } finally {
      setLoading(null);
    }
  }, [selectedSequence, onTestStarted]);

  const handleStopTest = useCallback(async () => {
    setLoading('stop');
    setError(null);

    try {
      const result = await api.stopTest();
      if (result.success) {
        onTestStopped?.();
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop test');
    } finally {
      setLoading(null);
    }
  }, [onTestStopped]);

  const handlePumpToggle = useCallback(async () => {
    const isPumpOn = ioStates.vacuum_pump;
    setLoading('pump');
    setError(null);

    try {
      const result = isPumpOn ? await api.pumpOff() : await api.pumpOn();
      if (!result.success) {
        setError(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to control pump');
    } finally {
      setLoading(null);
    }
  }, [ioStates.vacuum_pump]);

  const handleValveToggle = useCallback(async (valveName: string) => {
    const isOpen = ioStates[valveName];
    setLoading(valveName);
    setError(null);

    try {
      const action = isOpen ? 'close' : 'open';
      const result = await api.controlValve(valveName, action);
      if (!result.success) {
        setError(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to control ${valveName}`);
    } finally {
      setLoading(null);
    }
  }, [ioStates]);

  const handleTare = useCallback(async () => {
    setLoading('tare');
    setError(null);

    try {
      const result = await api.tareLoadCells();
      if (!result.success) {
        setError(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to tare');
    } finally {
      setLoading(null);
    }
  }, []);

  return (
    <div className="panel-card space-y-4">
      <h3 className="panel-header">Control Panel</h3>

      {/* Error display */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Sequence selector */}
      <div className="space-y-2">
        <label className="text-sm text-gray-400">Test Sequence</label>
        <select
          value={selectedSequence || ''}
          onChange={(e) => onSequenceSelect(e.target.value)}
          disabled={testRunning}
          className={clsx(
            'w-full bg-panel-bg border border-panel-border rounded-lg px-3 py-2',
            'text-gray-100 focus:outline-none focus:border-blue-500',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <option value="">Select a sequence...</option>
          {sequences.map((seq) => (
            <option key={seq.name} value={seq.name}>
              {seq.name} ({seq.stages} stages, {seq.cycles}x)
            </option>
          ))}
        </select>
      </div>

      {/* Start/Stop buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleStartTest}
          disabled={testRunning || !selectedSequence || loading !== null}
          className={clsx(
            'flex-1 btn-success flex items-center justify-center gap-2',
            'disabled:bg-gray-700 disabled:border-gray-600'
          )}
        >
          <Play size={18} />
          {loading === 'start' ? 'Starting...' : 'Start Test'}
        </button>
        <button
          onClick={handleStopTest}
          disabled={!testRunning || loading !== null}
          className={clsx(
            'flex-1 btn-danger flex items-center justify-center gap-2',
            'disabled:bg-gray-700 disabled:border-gray-600'
          )}
        >
          <Square size={18} />
          {loading === 'stop' ? 'Stopping...' : 'Stop Test'}
        </button>
      </div>

      {/* Manual controls */}
      <div className="border-t border-panel-border pt-4 space-y-3">
        <h4 className="text-sm text-gray-400 font-medium">Manual Controls</h4>

        {/* Pump toggle */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Power size={16} className="text-gray-400" />
            <span className="text-sm">Vacuum Pump</span>
          </div>
          <ToggleButton
            isOn={ioStates.vacuum_pump ?? false}
            onToggle={handlePumpToggle}
            disabled={loading !== null}
            loading={loading === 'pump'}
          />
        </div>

        {/* Vacuum valve toggle */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wind size={16} className="text-gray-400" />
            <span className="text-sm">Vacuum Valve</span>
          </div>
          <ToggleButton
            isOn={ioStates.vacuum_valve ?? false}
            onToggle={() => handleValveToggle('vacuum_valve')}
            disabled={loading !== null}
            loading={loading === 'vacuum_valve'}
            labels={['CLOSED', 'OPEN']}
          />
        </div>

        {/* Vent valve toggle */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wind size={16} className="text-gray-400" />
            <span className="text-sm">Vent Valve</span>
          </div>
          <ToggleButton
            isOn={ioStates.vent_valve ?? false}
            onToggle={() => handleValveToggle('vent_valve')}
            disabled={loading !== null}
            loading={loading === 'vent_valve'}
            labels={['CLOSED', 'OPEN']}
          />
        </div>

        {/* Tare button */}
        <button
          onClick={handleTare}
          disabled={loading !== null}
          className="w-full btn-control text-sm"
        >
          {loading === 'tare' ? 'Taring...' : 'Tare Load Cells'}
        </button>
      </div>
    </div>
  );
}

interface ToggleButtonProps {
  isOn: boolean;
  onToggle: () => void;
  disabled?: boolean;
  loading?: boolean;
  labels?: [string, string];
}

function ToggleButton({ isOn, onToggle, disabled, loading, labels = ['OFF', 'ON'] }: ToggleButtonProps) {
  return (
    <button
      onClick={onToggle}
      disabled={disabled}
      className={clsx(
        'toggle-switch',
        isOn ? 'toggle-switch-on' : 'toggle-switch-off',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
    >
      <span
        className={clsx('toggle-knob', isOn ? 'toggle-knob-on' : 'toggle-knob-off')}
      />
      <span className="sr-only">{isOn ? labels[1] : labels[0]}</span>
    </button>
  );
}

interface IOStatusDisplayProps {
  ioStates: IOStates;
}

export function IOStatusDisplay({ ioStates }: IOStatusDisplayProps) {
  return (
    <div className="panel-card">
      <h3 className="panel-header">IO Status</h3>
      <div className="grid grid-cols-3 gap-3">
        <IOIndicator name="Pump" isOn={ioStates.vacuum_pump ?? false} />
        <IOIndicator name="Vacuum" isOn={ioStates.vacuum_valve ?? false} label={['CLOSED', 'OPEN']} />
        <IOIndicator name="Vent" isOn={ioStates.vent_valve ?? false} label={['CLOSED', 'OPEN']} />
      </div>
    </div>
  );
}

interface IOIndicatorProps {
  name: string;
  isOn: boolean;
  label?: [string, string];
}

function IOIndicator({ name, isOn, label = ['OFF', 'ON'] }: IOIndicatorProps) {
  return (
    <div className="lcd-display p-2 text-center">
      <div className="text-xs text-gray-500 uppercase mb-1">{name}</div>
      <div
        className={clsx(
          'text-sm font-mono font-bold',
          isOn ? 'text-green-400' : 'text-gray-500'
        )}
      >
        {isOn ? label[1] : label[0]}
      </div>
      <div
        className={clsx(
          'w-2 h-2 rounded-full mx-auto mt-1',
          isOn ? 'bg-green-500' : 'bg-gray-600'
        )}
      />
    </div>
  );
}


