'use client';

import { clsx } from 'clsx';
import type { StageChangeData, ProgressData } from '@/hooks/useWebSocket';
import type { Sequence } from '@/lib/api';

interface StageProgressProps {
  testRunning: boolean;
  stageInfo: StageChangeData | null;
  progress: ProgressData | null;
  statusMessage: string;
  sequence: Sequence | null;
}

export function StageProgress({
  testRunning,
  stageInfo,
  progress,
  statusMessage,
  sequence,
}: StageProgressProps) {
  if (!testRunning) {
    return (
      <div className="panel-card">
        <h3 className="panel-header">Test Status</h3>
        <div className="flex items-center justify-center h-32 text-gray-500">
          <div className="text-center">
            <div className="text-4xl mb-2">⏸️</div>
            <div>No test running</div>
            <div className="text-sm mt-1">{statusMessage || 'Select a sequence and click Start'}</div>
          </div>
        </div>
      </div>
    );
  }

  const currentStage = sequence?.stages?.[stageInfo?.stage_index ?? 0];
  const progressPercent = progress?.progress ? Math.round(progress.progress * 100) : 0;

  return (
    <div className="panel-card space-y-4">
      <h3 className="panel-header flex items-center gap-2">
        <div className="status-indicator status-indicator-running" />
        Test Status
      </h3>

      {/* Cycle indicator */}
      {stageInfo && stageInfo.total_cycles > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Cycle</span>
          <span className="lcd-value text-lg">
            {stageInfo.current_cycle + 1} / {stageInfo.total_cycles}
          </span>
        </div>
      )}

      {/* Stage indicator */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Stage</span>
          <span className="lcd-value text-lg">
            {stageInfo ? `${stageInfo.stage_index + 1} / ${stageInfo.stages_per_cycle}` : '-'}
          </span>
        </div>
        
        <div className="lcd-display p-3">
          <div className="text-xs text-gray-500 mb-1">Current Stage</div>
          <div className="lcd-value text-xl truncate">
            {stageInfo?.stage_name || 'Initializing...'}
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Progress</span>
          <span className="text-gray-300">{progressPercent}%</span>
        </div>
        <div className="h-3 bg-panel-bg rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        {progress?.status && (
          <div className="text-xs text-gray-500">{progress.status}</div>
        )}
      </div>

      {/* Current stage details */}
      {currentStage && (
        <div className="border-t border-panel-border pt-3 space-y-2">
          <h4 className="text-xs text-gray-500 uppercase">Stage Settings</h4>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {currentStage.target_vacuum_bar !== null && (
              <div>
                <span className="text-gray-500">Target: </span>
                <span className="text-gray-300">{Math.abs(currentStage.target_vacuum_bar)} bar</span>
              </div>
            )}
            {currentStage.max_time_seconds !== null && (
              <div>
                <span className="text-gray-500">Max Time: </span>
                <span className="text-gray-300">{currentStage.max_time_seconds}s</span>
              </div>
            )}
            <div>
              <span className="text-gray-500">Pump: </span>
              <span className={clsx(
                currentStage.pump_mode === 'continuous' && 'text-green-400',
                currentStage.pump_mode === 'off' && 'text-gray-400',
                currentStage.pump_mode === 'maintain' && 'text-yellow-400',
              )}>
                {currentStage.pump_mode}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Status message */}
      {statusMessage && (
        <div className="border-t border-panel-border pt-3">
          <div className="text-xs text-gray-500 mb-1">Status</div>
          <div className="text-sm text-gray-300">{statusMessage}</div>
        </div>
      )}
    </div>
  );
}

interface StageListProps {
  sequence: Sequence | null;
  currentStageIndex: number;
}

export function StageList({ sequence, currentStageIndex }: StageListProps) {
  if (!sequence) return null;

  return (
    <div className="panel-card">
      <h3 className="panel-header">Sequence: {sequence.name}</h3>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {sequence.stages.map((stage, index) => (
          <div
            key={index}
            className={clsx(
              'p-2 rounded-lg border transition-colors',
              index === currentStageIndex
                ? 'bg-blue-900/30 border-blue-600'
                : index < currentStageIndex
                ? 'bg-green-900/20 border-green-800/50'
                : 'bg-panel-bg border-panel-border'
            )}
          >
            <div className="flex items-center gap-2">
              <div
                className={clsx(
                  'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold',
                  index === currentStageIndex
                    ? 'bg-blue-600 text-white'
                    : index < currentStageIndex
                    ? 'bg-green-600 text-white'
                    : 'bg-panel-border text-gray-400'
                )}
              >
                {index < currentStageIndex ? '✓' : index + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{stage.name}</div>
                <div className="text-xs text-gray-500">
                  {stage.target_vacuum_bar !== null && `${Math.abs(stage.target_vacuum_bar)} bar`}
                  {stage.target_vacuum_bar !== null && stage.max_time_seconds !== null && ' / '}
                  {stage.max_time_seconds !== null && `${stage.max_time_seconds}s`}
                  {stage.target_vacuum_bar === null && stage.max_time_seconds === null && 'Manual'}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      {sequence.cycles > 1 && (
        <div className="mt-3 pt-3 border-t border-panel-border text-sm text-gray-400">
          Repeats {sequence.cycles} times
        </div>
      )}
    </div>
  );
}


