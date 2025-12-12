'use client';

import { useState, useCallback } from 'react';
import { clsx } from 'clsx';
import { Play, Square, Power, Wind, RotateCcw, Settings2, Scale, Plus, Edit3 } from 'lucide-react';
import * as api from '@/lib/api';
import type { IOStates, SequenceSummary } from '@/lib/api';

interface ControlPanelProps {
  testRunning: boolean;
  ioStates: IOStates;
  sequences: SequenceSummary[];
  selectedSequence: string | null;
  onSequenceSelect: (name: string) => void;
  onStartTestRequest?: () => void;
  onTestStopped?: () => void;
  onTareComplete?: () => void;
  onWeighAssembly?: () => void;
  onNewSequence?: () => void;
  onEditSequence?: () => void;
}

export function ControlPanel({
  testRunning,
  ioStates,
  sequences,
  selectedSequence,
  onSequenceSelect,
  onStartTestRequest,
  onTestStopped,
  onTareComplete,
  onWeighAssembly,
  onNewSequence,
  onEditSequence,
}: ControlPanelProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleStartTest = useCallback(async () => {
    if (!selectedSequence) {
      setError('Please select a sequence first');
      return;
    }

    // Trigger the metadata modal instead of starting directly
    onStartTestRequest?.();
  }, [selectedSequence, onStartTestRequest]);

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
      if (result.success) {
        // Clear chart history since force values are now relative to new zero
        onTareComplete?.();
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to tare');
    } finally {
      setLoading(null);
    }
  }, [onTareComplete]);

  return (
    <div className="panel-card space-y-5">
      <div className="flex items-center gap-2">
        <Settings2 className="w-4 h-4 text-slate-400" />
        <h3 className="panel-header mb-0">Control Panel</h3>
      </div>

      {/* Error display */}
      {error && (
        <div className="flex items-start gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/30">
          <div className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1.5 flex-shrink-0" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Sequence selector */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            Test Sequence
          </label>
          <div className="flex items-center gap-1">
            <button
              onClick={onNewSequence}
              disabled={testRunning}
              className={clsx(
                'p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 transition-colors',
                testRunning && 'opacity-50 cursor-not-allowed'
              )}
              title="Create new sequence"
            >
              <Plus size={14} />
            </button>
            <button
              onClick={onEditSequence}
              disabled={testRunning || !selectedSequence}
              className={clsx(
                'p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 transition-colors',
                (testRunning || !selectedSequence) && 'opacity-50 cursor-not-allowed'
              )}
              title="Edit selected sequence"
            >
              <Edit3 size={14} />
            </button>
          </div>
        </div>
        <select
          value={selectedSequence || ''}
          onChange={(e) => onSequenceSelect(e.target.value)}
          disabled={testRunning}
          className={clsx(
            'form-select w-full',
            testRunning && 'opacity-60 cursor-not-allowed'
          )}
        >
          <option value="">Select a sequence...</option>
          {sequences.map((seq) => (
            <option key={seq.name} value={seq.name}>
              {seq.display_name || seq.name} ({seq.stages} stages, {seq.cycles}×)
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
            'flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all duration-200',
            !testRunning && selectedSequence && loading === null
              ? 'bg-emerald-500/20 border border-emerald-500/50 text-emerald-300 hover:bg-emerald-500/30 hover:border-emerald-400/60'
              : 'bg-slate-800/50 border border-slate-700 text-slate-500 cursor-not-allowed'
          )}
        >
          <Play size={18} className={loading === 'start' ? 'animate-pulse' : ''} />
          <span>Start Test</span>
        </button>
        <button
          onClick={handleStopTest}
          disabled={!testRunning || loading !== null}
          className={clsx(
            'flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all duration-200',
            testRunning && loading === null
              ? 'bg-red-500/20 border border-red-500/50 text-red-300 hover:bg-red-500/30 hover:border-red-400/60'
              : 'bg-slate-800/50 border border-slate-700 text-slate-500 cursor-not-allowed'
          )}
        >
          <Square size={18} className={loading === 'stop' ? 'animate-pulse' : ''} />
          <span>{loading === 'stop' ? 'Stopping...' : 'Stop Test'}</span>
        </button>
      </div>

      {/* Manual controls */}
      <div className="space-y-4 pt-4 border-t border-panel-border">
        <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider">
          Manual Controls
        </h4>

        {/* Pump toggle */}
        <div className="flex items-center justify-between p-3 rounded-xl bg-panel-bg/50 border border-panel-border/50">
          <div className="flex items-center gap-3">
            <div className={clsx(
              'flex items-center justify-center w-8 h-8 rounded-lg',
              ioStates.vacuum_pump 
                ? 'bg-emerald-500/20 text-emerald-400' 
                : 'bg-slate-700/50 text-slate-500'
            )}>
              <Power size={16} />
            </div>
            <div>
              <span className="text-sm font-medium text-slate-200">Vacuum Pump</span>
              <p className="text-xs text-slate-500">
                {ioStates.vacuum_pump ? 'Running' : 'Stopped'}
              </p>
            </div>
          </div>
          <ToggleButton
            isOn={ioStates.vacuum_pump ?? false}
            onToggle={handlePumpToggle}
            disabled={loading !== null}
            loading={loading === 'pump'}
          />
        </div>

        {/* Vacuum valve toggle */}
        <div className="flex items-center justify-between p-3 rounded-xl bg-panel-bg/50 border border-panel-border/50">
          <div className="flex items-center gap-3">
            <div className={clsx(
              'flex items-center justify-center w-8 h-8 rounded-lg',
              ioStates.vacuum_valve 
                ? 'bg-blue-500/20 text-blue-400' 
                : 'bg-slate-700/50 text-slate-500'
            )}>
              <Wind size={16} />
            </div>
            <div>
              <span className="text-sm font-medium text-slate-200">Vacuum Valve</span>
              <p className="text-xs text-slate-500">
                {ioStates.vacuum_valve ? 'Open' : 'Closed'}
              </p>
            </div>
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
        <div className="flex items-center justify-between p-3 rounded-xl bg-panel-bg/50 border border-panel-border/50">
          <div className="flex items-center gap-3">
            <div className={clsx(
              'flex items-center justify-center w-8 h-8 rounded-lg',
              ioStates.vent_valve 
                ? 'bg-amber-500/20 text-amber-400' 
                : 'bg-slate-700/50 text-slate-500'
            )}>
              <Wind size={16} />
            </div>
            <div>
              <span className="text-sm font-medium text-slate-200">Vent Valve</span>
              <p className="text-xs text-slate-500">
                {ioStates.vent_valve ? 'Open' : 'Closed'}
              </p>
            </div>
          </div>
          <ToggleButton
            isOn={ioStates.vent_valve ?? false}
            onToggle={() => handleValveToggle('vent_valve')}
            disabled={loading !== null}
            loading={loading === 'vent_valve'}
            labels={['CLOSED', 'OPEN']}
          />
        </div>

        {/* Weigh Assembly button */}
        <button
          onClick={onWeighAssembly}
          disabled={loading !== null || testRunning}
          className={clsx(
            'w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-semibold transition-all duration-200',
            'bg-emerald-500/20 border border-emerald-500/40 text-emerald-300',
            'hover:bg-emerald-500/30 hover:border-emerald-400/50',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <Scale size={18} />
          <span>Weigh Assembly</span>
        </button>

        {/* Tare button */}
        <button
          onClick={handleTare}
          disabled={loading !== null}
          className={clsx(
            'w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all duration-200',
            'bg-panel-bg border border-panel-border text-slate-300',
            'hover:bg-panel-highlight hover:border-slate-500',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <RotateCcw size={16} className={loading === 'tare' ? 'animate-spin' : ''} />
          <span>{loading === 'tare' ? 'Taring...' : 'Tare Load Cells'}</span>
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
        disabled && 'opacity-50 cursor-not-allowed',
        loading && 'animate-pulse'
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
      <div className="grid grid-cols-3 gap-2">
        <IOIndicator name="Pump" isOn={ioStates.vacuum_pump ?? false} />
        <IOIndicator name="Vacuum" isOn={ioStates.vacuum_valve ?? false} label={['SHUT', 'OPEN']} />
        <IOIndicator name="Vent" isOn={ioStates.vent_valve ?? false} label={['SHUT', 'OPEN']} />
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
    <div className="lcd-display p-3 text-center">
      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1.5">{name}</div>
      <div
        className={clsx(
          'text-sm font-mono font-semibold tracking-tight',
          isOn ? 'lcd-value' : 'text-slate-600'
        )}
      >
        {isOn ? label[1] : label[0]}
      </div>
      <div
        className={clsx(
          'w-2 h-2 rounded-full mx-auto mt-2',
          isOn ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-slate-700'
        )}
      />
    </div>
  );
}
