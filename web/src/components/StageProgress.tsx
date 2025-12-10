'use client';

import { clsx } from 'clsx';
import { Timer, Repeat, CheckCircle2, Circle, PlayCircle, Pause } from 'lucide-react';
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
        <div className="flex flex-col items-center justify-center py-8 text-slate-500">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-slate-800/50 border border-slate-700/50 mb-3">
            <Pause className="w-6 h-6 text-slate-600" />
          </div>
          <div className="text-sm font-medium text-slate-400">No test running</div>
          <div className="text-xs text-slate-600 mt-1 text-center max-w-[200px]">
            {statusMessage || 'Select a sequence and click Start to begin'}
          </div>
        </div>
      </div>
    );
  }

  const currentStage = sequence?.stages?.[stageInfo?.stage_index ?? 0];
  const progressPercent = progress?.progress ? Math.round(progress.progress * 100) : 0;

  return (
    <div className="panel-card space-y-4">
      <div className="flex items-center gap-2">
        <div className="status-indicator status-indicator-running" />
        <h3 className="panel-header mb-0">Test Status</h3>
      </div>

      {/* Cycle indicator */}
      {stageInfo && stageInfo.total_cycles > 1 && (
        <div className="flex items-center justify-between py-2 px-3 rounded-lg bg-panel-bg/50 border border-panel-border/30">
          <div className="flex items-center gap-2">
            <Repeat size={14} className="text-slate-500" />
            <span className="text-sm text-slate-400">Cycle</span>
          </div>
          <span className="lcd-value text-lg">
            {stageInfo.current_cycle + 1} / {stageInfo.total_cycles}
          </span>
        </div>
      )}

      {/* Stage indicator */}
      <div className="space-y-3">
        <div className="flex items-center justify-between py-2 px-3 rounded-lg bg-panel-bg/50 border border-panel-border/30">
          <div className="flex items-center gap-2">
            <Timer size={14} className="text-slate-500" />
            <span className="text-sm text-slate-400">Stage</span>
          </div>
          <span className="lcd-value text-lg">
            {stageInfo ? `${stageInfo.stage_index + 1} / ${stageInfo.stages_per_cycle}` : '-'}
          </span>
        </div>
        
        <div className="lcd-display p-4">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Current Stage</div>
          <div className="lcd-value text-xl truncate">
            {stageInfo?.stage_name || 'Initializing...'}
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-500 uppercase tracking-wider">Progress</span>
          <span className="text-sm font-mono text-slate-300">{progressPercent}%</span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-bar-fill"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        {progress?.status && (
          <div className="text-xs text-slate-500 truncate">{progress.status}</div>
        )}
      </div>

      {/* Current stage details */}
      {currentStage && (
        <div className="pt-3 border-t border-panel-border space-y-2">
          <h4 className="text-[10px] text-slate-500 uppercase tracking-wider">Stage Settings</h4>
          <div className="grid grid-cols-2 gap-2">
            {currentStage.target_vacuum_bar !== null && (
              <div className="py-1.5 px-2.5 rounded-lg bg-panel-bg/30 border border-panel-border/30">
                <span className="text-[10px] text-slate-600 block">Target</span>
                <span className="text-sm text-slate-300 font-mono">
                  {Math.abs(currentStage.target_vacuum_bar)} bar
                </span>
              </div>
            )}
            {currentStage.max_time_seconds !== null && (
              <div className="py-1.5 px-2.5 rounded-lg bg-panel-bg/30 border border-panel-border/30">
                <span className="text-[10px] text-slate-600 block">Max Time</span>
                <span className="text-sm text-slate-300 font-mono">
                  {currentStage.max_time_seconds}s
                </span>
              </div>
            )}
            <div className="py-1.5 px-2.5 rounded-lg bg-panel-bg/30 border border-panel-border/30 col-span-2">
              <span className="text-[10px] text-slate-600 block">Pump Mode</span>
              <span className={clsx(
                'text-sm font-medium',
                currentStage.pump_mode === 'continuous' && 'text-emerald-400',
                currentStage.pump_mode === 'off' && 'text-slate-500',
                currentStage.pump_mode === 'maintain' && 'text-amber-400',
              )}>
                {currentStage.pump_mode.charAt(0).toUpperCase() + currentStage.pump_mode.slice(1)}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Status message */}
      {statusMessage && (
        <div className="pt-3 border-t border-panel-border">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Status</div>
          <div className="text-sm text-slate-400">{statusMessage}</div>
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
      <div className="flex items-center justify-between mb-4">
        <h3 className="panel-header mb-0">Sequence: {sequence.name}</h3>
        {sequence.cycles > 1 && (
          <span className="badge badge-info">
            {sequence.cycles}× cycles
          </span>
        )}
      </div>
      <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
        {sequence.stages.map((stage, index) => {
          const isActive = index === currentStageIndex;
          const isComplete = index < currentStageIndex;
          
          return (
            <div
              key={index}
              className={clsx(
                'flex items-center gap-3 p-3 rounded-xl border transition-all duration-200',
                isActive
                  ? 'bg-teal-500/10 border-teal-500/40 shadow-[0_0_15px_rgba(20,184,166,0.1)]'
                  : isComplete
                  ? 'bg-emerald-500/5 border-emerald-500/20'
                  : 'bg-panel-bg/30 border-panel-border/30'
              )}
            >
              {/* Stage indicator */}
              <div
                className={clsx(
                  'flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0',
                  isActive
                    ? 'bg-teal-500/20 text-teal-400'
                    : isComplete
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-slate-700/50 text-slate-500'
                )}
              >
                {isComplete ? (
                  <CheckCircle2 size={16} />
                ) : isActive ? (
                  <PlayCircle size={16} className="animate-pulse" />
                ) : (
                  <Circle size={16} />
                )}
              </div>
              
              {/* Stage info */}
              <div className="flex-1 min-w-0">
                <div className={clsx(
                  'text-sm font-medium truncate',
                  isActive ? 'text-teal-300' : isComplete ? 'text-emerald-300' : 'text-slate-300'
                )}>
                  {stage.name}
                </div>
                <div className="text-xs text-slate-500 flex items-center gap-2">
                  {stage.target_vacuum_bar !== null && (
                    <span>{Math.abs(stage.target_vacuum_bar)} bar</span>
                  )}
                  {stage.target_vacuum_bar !== null && stage.max_time_seconds !== null && (
                    <span className="text-slate-700">•</span>
                  )}
                  {stage.max_time_seconds !== null && (
                    <span>{stage.max_time_seconds}s</span>
                  )}
                  {stage.target_vacuum_bar === null && stage.max_time_seconds === null && (
                    <span className="text-slate-600">Manual</span>
                  )}
                </div>
              </div>
              
              {/* Stage number */}
              <div className={clsx(
                'text-xs font-mono px-2 py-1 rounded',
                isActive ? 'text-teal-400 bg-teal-500/10' : 'text-slate-600'
              )}>
                {index + 1}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
