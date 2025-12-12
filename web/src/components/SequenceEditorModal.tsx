'use client';

import { useState, useCallback, useEffect } from 'react';
import { clsx } from 'clsx';
import {
  X,
  Save,
  Plus,
  Trash2,
  GripVertical,
  ChevronDown,
  ChevronUp,
  Copy,
  Layers,
  Play,
  Clock,
  Gauge,
  Power,
  Wind,
  AlertCircle,
  Check,
  Edit3,
} from 'lucide-react';
import type { Sequence, Stage, IOAction } from '@/lib/api';

// Default empty stage template
const createEmptyStage = (): Stage => ({
  name: 'New Stage',
  target_vacuum_bar: null,
  max_time_seconds: 60,
  min_time_seconds: 0,
  pump_mode: 'off',
  vacuum_tolerance_bar: 0.05,
  collect_data: true,
  io_actions: [],
});

// Default empty IO action
const createEmptyIOAction = (): IOAction => ({
  device_name: 'vacuum_valve',
  action_type: 'digital_output',
  value: false,
  timing: 'start_of_stage',
  delay_seconds: 0,
  duration_seconds: null,
  description: '',
});

// Device options for IO actions
const DEVICE_OPTIONS = [
  { value: 'vacuum_pump', label: 'Vacuum Pump', icon: Power },
  { value: 'vacuum_valve', label: 'Vacuum Valve', icon: Wind },
  { value: 'vent_valve', label: 'Vent Valve', icon: Wind },
];

// Timing options for IO actions
const TIMING_OPTIONS = [
  { value: 'before_stage', label: 'Before Stage' },
  { value: 'start_of_stage', label: 'Start of Stage' },
  { value: 'during_stage', label: 'During Stage' },
  { value: 'end_of_stage', label: 'End of Stage' },
  { value: 'after_stage', label: 'After Stage' },
];

// Pump mode options
const PUMP_MODE_OPTIONS = [
  { value: 'continuous', label: 'Continuous', description: 'Pump runs entire stage' },
  { value: 'maintain', label: 'Maintain', description: 'Cycle to maintain setpoint' },
  { value: 'off', label: 'Off', description: 'Pump stays off' },
];

interface SequenceEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (sequence: Sequence) => Promise<boolean>;
  initialSequence?: Sequence | null;
  existingSequenceNames?: string[];
}

export function SequenceEditorModal({
  isOpen,
  onClose,
  onSave,
  initialSequence,
  existingSequenceNames = [],
}: SequenceEditorModalProps) {
  // Sequence metadata
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [cycles, setCycles] = useState(1);
  const [stages, setStages] = useState<Stage[]>([]);

  // UI state
  const [expandedStages, setExpandedStages] = useState<Set<number>>(new Set([0]));
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isEditMode, setIsEditMode] = useState(false);

  // Initialize form when modal opens or sequence changes
  useEffect(() => {
    if (isOpen) {
      if (initialSequence) {
        setName(initialSequence.name);
        setDescription(initialSequence.description || '');
        setCycles(initialSequence.cycles || 1);
        setStages(JSON.parse(JSON.stringify(initialSequence.stages || [])));
        setIsEditMode(true);
      } else {
        // New sequence
        setName('');
        setDescription('');
        setCycles(1);
        setStages([createEmptyStage()]);
        setIsEditMode(false);
      }
      setError(null);
      setSuccessMessage(null);
      setExpandedStages(new Set([0]));
    }
  }, [isOpen, initialSequence]);

  // Validation
  const nameError = !name.trim()
    ? 'Sequence name is required'
    : !isEditMode && existingSequenceNames.includes(name.trim())
    ? 'A sequence with this name already exists'
    : null;

  const stagesError = stages.length === 0 ? 'At least one stage is required' : null;

  const isValid = !nameError && !stagesError && stages.every((s) => s.name.trim());

  // Stage management
  const addStage = useCallback(() => {
    setStages((prev) => [...prev, createEmptyStage()]);
    setExpandedStages((prev) => {
      const arr = Array.from(prev);
      arr.push(stages.length);
      return new Set(arr);
    });
  }, [stages.length]);

  const removeStage = useCallback((index: number) => {
    setStages((prev) => prev.filter((_, i) => i !== index));
    setExpandedStages((prev) => {
      const next = new Set(prev);
      next.delete(index);
      // Shift indices
      const shifted = Array.from(next).map((i) => (i > index ? i - 1 : i));
      return new Set(shifted);
    });
  }, []);

  const duplicateStage = useCallback((index: number) => {
    const stageCopy = JSON.parse(JSON.stringify(stages[index]));
    stageCopy.name = `${stageCopy.name} (copy)`;
    setStages((prev) => [...prev.slice(0, index + 1), stageCopy, ...prev.slice(index + 1)]);
    setExpandedStages((prev) => {
      const arr = Array.from(prev);
      arr.push(index + 1);
      return new Set(arr);
    });
  }, [stages]);

  const moveStage = useCallback((index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= stages.length) return;

    setStages((prev) => {
      const newStages = [...prev];
      [newStages[index], newStages[newIndex]] = [newStages[newIndex], newStages[index]];
      return newStages;
    });

    setExpandedStages((prev) => {
      const mapped = Array.from(prev).map((i) => {
        if (i === index) return newIndex;
        if (i === newIndex) return index;
        return i;
      });
      return new Set(mapped);
    });
  }, [stages.length]);

  const updateStage = useCallback((index: number, updates: Partial<Stage>) => {
    setStages((prev) =>
      prev.map((stage, i) => (i === index ? { ...stage, ...updates } : stage))
    );
  }, []);

  const toggleStageExpanded = useCallback((index: number) => {
    setExpandedStages((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  // IO Action management
  const addIOAction = useCallback((stageIndex: number) => {
    setStages((prev) =>
      prev.map((stage, i) =>
        i === stageIndex
          ? { ...stage, io_actions: [...stage.io_actions, createEmptyIOAction()] }
          : stage
      )
    );
  }, []);

  const removeIOAction = useCallback((stageIndex: number, actionIndex: number) => {
    setStages((prev) =>
      prev.map((stage, i) =>
        i === stageIndex
          ? { ...stage, io_actions: stage.io_actions.filter((_, j) => j !== actionIndex) }
          : stage
      )
    );
  }, []);

  const updateIOAction = useCallback(
    (stageIndex: number, actionIndex: number, updates: Partial<IOAction>) => {
      setStages((prev) =>
        prev.map((stage, i) =>
          i === stageIndex
            ? {
                ...stage,
                io_actions: stage.io_actions.map((action, j) =>
                  j === actionIndex ? { ...action, ...updates } : action
                ),
              }
            : stage
        )
      );
    },
    []
  );

  // Save handler
  const handleSave = useCallback(async () => {
    if (!isValid) {
      setError('Please fix validation errors before saving');
      return;
    }

    setIsSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const sequence: Sequence = {
        name: name.trim(),
        description: description.trim(),
        cycles,
        stages: stages.map((stage) => ({
          ...stage,
          name: stage.name.trim(),
          io_actions: stage.io_actions.map((action) => ({
            ...action,
            description: action.description.trim(),
          })),
        })),
      };

      console.log('[SequenceEditor] Saving sequence:', sequence);
      const success = await onSave(sequence);

      if (success) {
        setSuccessMessage('Sequence saved successfully!');
        setTimeout(() => {
          onClose();
        }, 1000);
      } else {
        setError('Failed to save sequence');
      }
    } catch (err) {
      console.error('[SequenceEditor] Save error:', err);
      setError(err instanceof Error ? err.message : 'Failed to save sequence');
    } finally {
      setIsSaving(false);
    }
  }, [isValid, name, description, cycles, stages, onSave, onClose]);

  // Quick add common patterns
  const addEvacuateStage = useCallback(() => {
    const stage: Stage = {
      name: 'Evacuate to Setpoint',
      target_vacuum_bar: 0.3,
      max_time_seconds: 120,
      min_time_seconds: 5,
      pump_mode: 'continuous',
      vacuum_tolerance_bar: 0.02,
      collect_data: true,
      io_actions: [
        {
          device_name: 'vacuum_valve',
          action_type: 'digital_output',
          value: true,
          timing: 'start_of_stage',
          delay_seconds: 0,
          duration_seconds: null,
          description: 'Open vacuum valve',
        },
        {
          device_name: 'vent_valve',
          action_type: 'digital_output',
          value: false,
          timing: 'start_of_stage',
          delay_seconds: 0,
          duration_seconds: null,
          description: 'Close vent valve',
        },
        {
          device_name: 'vacuum_valve',
          action_type: 'digital_output',
          value: false,
          timing: 'end_of_stage',
          delay_seconds: 0,
          duration_seconds: null,
          description: 'Close vacuum valve at setpoint',
        },
      ],
    };
    setStages((prev) => [...prev, stage]);
    setExpandedStages((prev) => {
      const arr = Array.from(prev);
      arr.push(stages.length);
      return new Set(arr);
    });
  }, [stages.length]);

  const addHoldStage = useCallback(() => {
    const stage: Stage = {
      name: 'Hold (Leak Check)',
      target_vacuum_bar: null,
      max_time_seconds: 180,
      min_time_seconds: 180,
      pump_mode: 'off',
      vacuum_tolerance_bar: 0.05,
      collect_data: true,
      io_actions: [
        {
          device_name: 'vacuum_valve',
          action_type: 'digital_output',
          value: false,
          timing: 'start_of_stage',
          delay_seconds: 0,
          duration_seconds: null,
          description: 'Keep vacuum valve closed',
        },
        {
          device_name: 'vent_valve',
          action_type: 'digital_output',
          value: false,
          timing: 'start_of_stage',
          delay_seconds: 0,
          duration_seconds: null,
          description: 'Keep vent valve closed',
        },
      ],
    };
    setStages((prev) => [...prev, stage]);
    setExpandedStages((prev) => {
      const arr = Array.from(prev);
      arr.push(stages.length);
      return new Set(arr);
    });
  }, [stages.length]);

  const addVentStage = useCallback(() => {
    const stage: Stage = {
      name: 'Vent Chamber',
      target_vacuum_bar: null,
      max_time_seconds: 30,
      min_time_seconds: 5,
      pump_mode: 'off',
      vacuum_tolerance_bar: 0.05,
      collect_data: true,
      io_actions: [
        {
          device_name: 'vacuum_valve',
          action_type: 'digital_output',
          value: false,
          timing: 'start_of_stage',
          delay_seconds: 0,
          duration_seconds: null,
          description: 'Keep vacuum valve closed',
        },
        {
          device_name: 'vent_valve',
          action_type: 'digital_output',
          value: true,
          timing: 'start_of_stage',
          delay_seconds: 0,
          duration_seconds: null,
          description: 'Open vent valve',
        },
        {
          device_name: 'vent_valve',
          action_type: 'digital_output',
          value: false,
          timing: 'end_of_stage',
          delay_seconds: 0,
          duration_seconds: null,
          description: 'Close vent valve',
        },
      ],
    };
    setStages((prev) => [...prev, stage]);
    setExpandedStages((prev) => {
      const arr = Array.from(prev);
      arr.push(stages.length);
      return new Set(arr);
    });
  }, [stages.length]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-4xl max-h-[95vh] overflow-hidden rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 border border-slate-700/50 shadow-2xl shadow-black/50 flex flex-col">
        {/* Header */}
        <div className="relative px-6 py-5 border-b border-slate-700/50 bg-slate-900/50 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/20">
              <Layers className="w-5 h-5 text-violet-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-100">
                {isEditMode ? 'Edit Sequence' : 'Create New Sequence'}
              </h2>
              <p className="text-sm text-slate-400">
                {isEditMode
                  ? `Editing: ${initialSequence?.name}`
                  : 'Define test stages and IO actions'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="absolute top-5 right-5 p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
          {/* Error/Success Messages */}
          {error && (
            <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/30">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          {successMessage && (
            <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
              <Check className="w-5 h-5 text-emerald-400 flex-shrink-0" />
              <p className="text-sm text-emerald-300">{successMessage}</p>
            </div>
          )}

          {/* Sequence Metadata */}
          <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 p-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
              <Edit3 size={16} className="text-slate-400" />
              Sequence Details
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-400 mb-1.5">
                  Sequence Name <span className="text-amber-400">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., 300mbar_leak_test"
                  disabled={isEditMode}
                  className={clsx(
                    'form-input',
                    nameError && 'border-red-500/50 focus:border-red-500',
                    isEditMode && 'opacity-60 cursor-not-allowed'
                  )}
                />
                {nameError && <p className="text-xs text-red-400 mt-1">{nameError}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1.5">
                  Cycles
                </label>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={cycles}
                  onChange={(e) => setCycles(Math.max(1, parseInt(e.target.value) || 1))}
                  className="form-input"
                />
                <p className="text-xs text-slate-500 mt-1">Repeat sequence N times</p>
              </div>
              <div className="md:col-span-3">
                <label className="block text-sm font-medium text-slate-400 mb-1.5">
                  Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe what this test sequence does..."
                  rows={2}
                  className="form-input resize-none"
                />
              </div>
            </div>
          </div>

          {/* Quick Add Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-slate-400 mr-2">Quick add:</span>
            <button
              type="button"
              onClick={addEvacuateStage}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-teal-300 bg-teal-500/10 hover:bg-teal-500/20 border border-teal-500/30 rounded-lg transition-colors"
            >
              <Gauge size={14} />
              Evacuate Stage
            </button>
            <button
              type="button"
              onClick={addHoldStage}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 rounded-lg transition-colors"
            >
              <Clock size={14} />
              Hold Stage
            </button>
            <button
              type="button"
              onClick={addVentStage}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 rounded-lg transition-colors"
            >
              <Wind size={14} />
              Vent Stage
            </button>
            <button
              type="button"
              onClick={addStage}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-700/50 hover:bg-slate-700 border border-slate-600 rounded-lg transition-colors"
            >
              <Plus size={14} />
              Empty Stage
            </button>
          </div>

          {/* Stages */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <Layers size={16} className="text-slate-400" />
                Stages ({stages.length})
              </h3>
              {stagesError && <p className="text-xs text-red-400">{stagesError}</p>}
            </div>

            {stages.length === 0 ? (
              <div className="text-center py-8 text-slate-500 border border-dashed border-slate-700 rounded-xl">
                <Layers size={32} className="mx-auto mb-2 opacity-50" />
                <p>No stages yet. Add a stage to get started.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {stages.map((stage, stageIndex) => (
                  <StageEditor
                    key={stageIndex}
                    stage={stage}
                    stageIndex={stageIndex}
                    totalStages={stages.length}
                    isExpanded={expandedStages.has(stageIndex)}
                    onToggleExpanded={() => toggleStageExpanded(stageIndex)}
                    onUpdate={(updates) => updateStage(stageIndex, updates)}
                    onRemove={() => removeStage(stageIndex)}
                    onDuplicate={() => duplicateStage(stageIndex)}
                    onMoveUp={() => moveStage(stageIndex, 'up')}
                    onMoveDown={() => moveStage(stageIndex, 'down')}
                    onAddIOAction={() => addIOAction(stageIndex)}
                    onRemoveIOAction={(actionIndex) => removeIOAction(stageIndex, actionIndex)}
                    onUpdateIOAction={(actionIndex, updates) =>
                      updateIOAction(stageIndex, actionIndex, updates)
                    }
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-700/50 bg-slate-900/50 flex-shrink-0">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500">
              {stages.length} stage{stages.length !== 1 ? 's' : ''} · {cycles} cycle
              {cycles !== 1 ? 's' : ''}
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={!isValid || isSaving}
                className={clsx(
                  'flex items-center gap-2 px-5 py-2 text-sm font-medium rounded-lg transition-all',
                  isValid && !isSaving
                    ? 'bg-violet-600 hover:bg-violet-500 text-white shadow-lg shadow-violet-500/25'
                    : 'bg-slate-700 text-slate-400 cursor-not-allowed'
                )}
              >
                <Save size={16} />
                {isSaving ? 'Saving...' : 'Save Sequence'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Stage Editor Component
interface StageEditorProps {
  stage: Stage;
  stageIndex: number;
  totalStages: number;
  isExpanded: boolean;
  onToggleExpanded: () => void;
  onUpdate: (updates: Partial<Stage>) => void;
  onRemove: () => void;
  onDuplicate: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onAddIOAction: () => void;
  onRemoveIOAction: (actionIndex: number) => void;
  onUpdateIOAction: (actionIndex: number, updates: Partial<IOAction>) => void;
}

function StageEditor({
  stage,
  stageIndex,
  totalStages,
  isExpanded,
  onToggleExpanded,
  onUpdate,
  onRemove,
  onDuplicate,
  onMoveUp,
  onMoveDown,
  onAddIOAction,
  onRemoveIOAction,
  onUpdateIOAction,
}: StageEditorProps) {
  const getPumpModeColor = (mode: string) => {
    switch (mode) {
      case 'continuous':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
      case 'maintain':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
      default:
        return 'text-slate-400 bg-slate-500/10 border-slate-500/30';
    }
  };

  return (
    <div
      className={clsx(
        'rounded-xl border transition-all',
        isExpanded
          ? 'border-slate-600/50 bg-slate-800/50'
          : 'border-slate-700/30 bg-slate-800/20 hover:border-slate-600/40'
      )}
    >
      {/* Stage Header */}
      <div className="flex items-center gap-2 p-3">
        <div className="flex items-center gap-1 text-slate-500">
          <button
            type="button"
            onClick={onMoveUp}
            disabled={stageIndex === 0}
            className="p-1 hover:text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Move up"
          >
            <ChevronUp size={16} />
          </button>
          <button
            type="button"
            onClick={onMoveDown}
            disabled={stageIndex === totalStages - 1}
            className="p-1 hover:text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Move down"
          >
            <ChevronDown size={16} />
          </button>
        </div>

        <button
          type="button"
          onClick={onToggleExpanded}
          className="flex-1 flex items-center gap-3 text-left"
        >
          <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-slate-700/50 text-xs font-bold text-slate-400">
            {stageIndex + 1}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-slate-200 truncate">{stage.name || 'Untitled'}</div>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              {stage.target_vacuum_bar !== null && (
                <span className="flex items-center gap-1">
                  <Gauge size={12} />
                  {Math.abs(stage.target_vacuum_bar)} bar
                </span>
              )}
              {stage.max_time_seconds !== null && (
                <span className="flex items-center gap-1">
                  <Clock size={12} />
                  {stage.max_time_seconds}s
                </span>
              )}
              <span className={clsx('px-1.5 py-0.5 rounded text-[10px] font-medium border', getPumpModeColor(stage.pump_mode))}>
                {stage.pump_mode.toUpperCase()}
              </span>
              {stage.io_actions.length > 0 && (
                <span className="text-slate-600">{stage.io_actions.length} IO actions</span>
              )}
            </div>
          </div>
          {isExpanded ? (
            <ChevronUp size={18} className="text-slate-400" />
          ) : (
            <ChevronDown size={18} className="text-slate-400" />
          )}
        </button>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onDuplicate}
            className="p-1.5 text-slate-500 hover:text-slate-300 hover:bg-slate-700 rounded transition-colors"
            title="Duplicate stage"
          >
            <Copy size={14} />
          </button>
          <button
            type="button"
            onClick={onRemove}
            className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
            title="Remove stage"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Stage Content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-slate-700/30">
          {/* Stage Settings */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-4">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Stage Name <span className="text-amber-400">*</span>
              </label>
              <input
                type="text"
                value={stage.name}
                onChange={(e) => onUpdate({ name: e.target.value })}
                placeholder="e.g., Evacuate"
                className="form-input text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Target Vacuum (bar)
              </label>
              <input
                type="number"
                step="0.01"
                min="-1"
                max="1"
                value={stage.target_vacuum_bar ?? ''}
                onChange={(e) =>
                  onUpdate({
                    target_vacuum_bar: e.target.value ? parseFloat(e.target.value) : null,
                  })
                }
                placeholder="null"
                className="form-input text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Max Time (s)
              </label>
              <input
                type="number"
                step="1"
                min="0"
                value={stage.max_time_seconds ?? ''}
                onChange={(e) =>
                  onUpdate({
                    max_time_seconds: e.target.value ? parseFloat(e.target.value) : null,
                  })
                }
                placeholder="null"
                className="form-input text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Min Time (s)
              </label>
              <input
                type="number"
                step="1"
                min="0"
                value={stage.min_time_seconds}
                onChange={(e) =>
                  onUpdate({ min_time_seconds: parseFloat(e.target.value) || 0 })
                }
                className="form-input text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Pump Mode</label>
              <select
                value={stage.pump_mode}
                onChange={(e) =>
                  onUpdate({ pump_mode: e.target.value as Stage['pump_mode'] })
                }
                className="form-select text-sm"
              >
                {PUMP_MODE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Vacuum Tolerance
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="0.5"
                value={stage.vacuum_tolerance_bar}
                onChange={(e) =>
                  onUpdate({ vacuum_tolerance_bar: parseFloat(e.target.value) || 0.05 })
                }
                className="form-input text-sm"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id={`collect-data-${stageIndex}`}
                checked={stage.collect_data}
                onChange={(e) => onUpdate({ collect_data: e.target.checked })}
                className="rounded border-slate-600 bg-slate-800 text-teal-500 focus:ring-teal-500/30"
              />
              <label
                htmlFor={`collect-data-${stageIndex}`}
                className="text-xs text-slate-300 cursor-pointer"
              >
                Collect Data
              </label>
            </div>
          </div>

          {/* IO Actions */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-slate-400">
                IO Actions ({stage.io_actions.length})
              </label>
              <button
                type="button"
                onClick={onAddIOAction}
                className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-teal-300 hover:text-teal-200 bg-teal-500/10 hover:bg-teal-500/20 border border-teal-500/30 rounded transition-colors"
              >
                <Plus size={12} />
                Add Action
              </button>
            </div>

            {stage.io_actions.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No IO actions defined</p>
            ) : (
              <div className="space-y-2">
                {stage.io_actions.map((action, actionIndex) => (
                  <IOActionEditor
                    key={actionIndex}
                    action={action}
                    onUpdate={(updates) => onUpdateIOAction(actionIndex, updates)}
                    onRemove={() => onRemoveIOAction(actionIndex)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// IO Action Editor Component
interface IOActionEditorProps {
  action: IOAction;
  onUpdate: (updates: Partial<IOAction>) => void;
  onRemove: () => void;
}

function IOActionEditor({ action, onUpdate, onRemove }: IOActionEditorProps) {
  const DeviceIcon = DEVICE_OPTIONS.find((d) => d.value === action.device_name)?.icon || Power;

  return (
    <div className="flex items-start gap-2 p-2 rounded-lg bg-slate-900/50 border border-slate-700/30">
      <div className="flex-shrink-0 mt-1">
        <DeviceIcon size={14} className="text-slate-500" />
      </div>

      <div className="flex-1 grid grid-cols-2 md:grid-cols-5 gap-2">
        <div>
          <select
            value={action.device_name}
            onChange={(e) => onUpdate({ device_name: e.target.value })}
            className="form-select text-xs py-1.5"
          >
            {DEVICE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <select
            value={action.timing}
            onChange={(e) => onUpdate({ timing: e.target.value as IOAction['timing'] })}
            className="form-select text-xs py-1.5"
          >
            {TIMING_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <select
            value={action.value ? 'true' : 'false'}
            onChange={(e) => onUpdate({ value: e.target.value === 'true' })}
            className="form-select text-xs py-1.5"
          >
            <option value="true">
              {action.device_name.includes('valve') ? 'Open' : 'On'}
            </option>
            <option value="false">
              {action.device_name.includes('valve') ? 'Closed' : 'Off'}
            </option>
          </select>
        </div>
        <div>
          <input
            type="number"
            min="0"
            step="0.1"
            value={action.delay_seconds}
            onChange={(e) => onUpdate({ delay_seconds: parseFloat(e.target.value) || 0 })}
            placeholder="Delay (s)"
            className="form-input text-xs py-1.5"
          />
        </div>
        <div className="col-span-2 md:col-span-1">
          <input
            type="text"
            value={action.description}
            onChange={(e) => onUpdate({ description: e.target.value })}
            placeholder="Description..."
            className="form-input text-xs py-1.5"
          />
        </div>
      </div>

      <button
        type="button"
        onClick={onRemove}
        className="p-1 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors flex-shrink-0"
        title="Remove action"
      >
        <Trash2 size={12} />
      </button>
    </div>
  );
}

