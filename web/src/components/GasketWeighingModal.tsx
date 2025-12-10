'use client';

import { useState, useCallback, useEffect, useMemo } from 'react';
import { clsx } from 'clsx';
import { X, Scale, RotateCcw, Check, SkipForward } from 'lucide-react';
import * as api from '@/lib/api';

export interface GasketWeighingResult {
  weight_kg: number;
  assembly_id: string;
  assembly_description: string;
  timestamp: number;
  is_tared: boolean;
  individual_cells: {
    cell_1: number;
    cell_2: number;
    cell_3: number;
    cell_4: number;
  };
}

interface LoadCellData {
  load_cell_1_kg?: number;
  load_cell_2_kg?: number;
  load_cell_3_kg?: number;
  load_cell_4_kg?: number;
  total_force_kg?: number;
  gross_weight_kg?: number;
}

interface GasketWeighingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCapture: (result: GasketWeighingResult) => void;
  onSkip: () => void;
  currentData: LoadCellData | null;
}

// Stability parameters
const STABILITY_WINDOW_SIZE = 20; // samples
const STABILITY_THRESHOLD_KG = 0.010; // 10g
const MIN_STABLE_DURATION_MS = 1000; // 1 second

export function GasketWeighingModal({
  isOpen,
  onClose,
  onCapture,
  onSkip,
  currentData,
}: GasketWeighingModalProps) {
  // Form state
  const [assemblyId, setAssemblyId] = useState('');
  const [description, setDescription] = useState('');
  const [isTared, setIsTared] = useState(false);
  const [isTaring, setIsTaring] = useState(false);
  
  // Stability tracking
  const [weightHistory, setWeightHistory] = useState<number[]>([]);
  const [stableSince, setStableSince] = useState<number | null>(null);
  const [isStable, setIsStable] = useState(false);
  
  // Calculate current total weight
  const currentWeight = useMemo(() => {
    if (!currentData) return 0;
    
    const cell1 = currentData.load_cell_1_kg ?? 0;
    const cell2 = currentData.load_cell_2_kg ?? 0;
    const cell3 = currentData.load_cell_3_kg ?? 0;
    const cell4 = currentData.load_cell_4_kg ?? 0;
    
    const sum = cell1 + cell2 + cell3 + cell4;
    
    // If individual cells sum to 0, try total_force_kg or gross_weight_kg
    if (sum === 0) {
      return currentData.total_force_kg ?? currentData.gross_weight_kg ?? 0;
    }
    
    return sum;
  }, [currentData]);
  
  // Track weight history for stability detection
  useEffect(() => {
    if (!isOpen || currentWeight === undefined) return;
    
    setWeightHistory(prev => {
      const newHistory = [...prev, currentWeight].slice(-STABILITY_WINDOW_SIZE);
      return newHistory;
    });
  }, [isOpen, currentWeight]);
  
  // Check stability
  useEffect(() => {
    if (weightHistory.length < STABILITY_WINDOW_SIZE / 2) {
      setIsStable(false);
      setStableSince(null);
      return;
    }
    
    const min = Math.min(...weightHistory);
    const max = Math.max(...weightHistory);
    const range = max - min;
    
    const isCurrentlyStable = range <= STABILITY_THRESHOLD_KG;
    
    if (isCurrentlyStable) {
      if (stableSince === null) {
        setStableSince(Date.now());
      } else {
        const stableDuration = Date.now() - stableSince;
        if (stableDuration >= MIN_STABLE_DURATION_MS) {
          setIsStable(true);
        }
      }
    } else {
      setStableSince(null);
      setIsStable(false);
    }
  }, [weightHistory, stableSince]);
  
  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setWeightHistory([]);
      setStableSince(null);
      setIsStable(false);
      setAssemblyId('');
      setDescription('');
      setIsTared(false);
    }
  }, [isOpen]);
  
  const handleTare = useCallback(async () => {
    setIsTaring(true);
    try {
      const result = await api.tareLoadCells();
      if (result.success) {
        setIsTared(true);
        setWeightHistory([]);
        setStableSince(null);
        setIsStable(false);
      }
    } catch (error) {
      console.error('Failed to tare:', error);
    } finally {
      setIsTaring(false);
    }
  }, []);
  
  const handleCapture = useCallback(() => {
    if (!isStable) return;
    
    const result: GasketWeighingResult = {
      weight_kg: currentWeight,
      assembly_id: assemblyId.trim(),
      assembly_description: description.trim(),
      timestamp: Date.now() / 1000,
      is_tared: isTared,
      individual_cells: {
        cell_1: currentData?.load_cell_1_kg ?? 0,
        cell_2: currentData?.load_cell_2_kg ?? 0,
        cell_3: currentData?.load_cell_3_kg ?? 0,
        cell_4: currentData?.load_cell_4_kg ?? 0,
      },
    };
    
    onCapture(result);
  }, [isStable, currentWeight, assemblyId, description, isTared, currentData, onCapture]);
  
  // Stability indicator percentage
  const stabilityPercent = useMemo(() => {
    if (weightHistory.length < 3) return 0;
    const min = Math.min(...weightHistory);
    const max = Math.max(...weightHistory);
    const range = max - min;
    return Math.max(0, Math.min(100, (1 - range / STABILITY_THRESHOLD_KG) * 100));
  }, [weightHistory]);
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-xl overflow-hidden rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 border border-slate-700/50 shadow-2xl shadow-black/50">
        {/* Header */}
        <div className="relative px-6 py-5 border-b border-slate-700/50 bg-gradient-to-r from-emerald-900/20 to-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-emerald-500/20 border border-emerald-500/30">
              <Scale className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-slate-100">Weigh Gasket Assembly</h2>
              <p className="text-sm text-slate-400">
                Place assembly on fixture, wait for stable reading
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
        <div className="px-6 py-6 space-y-6">
          {/* Weight Display */}
          <div className={clsx(
            'relative rounded-2xl p-6 transition-all duration-300',
            isStable 
              ? 'bg-gradient-to-br from-emerald-900/40 to-emerald-950/40 border-2 border-emerald-500/50'
              : 'bg-gradient-to-br from-slate-800/50 to-slate-900/50 border-2 border-slate-700/50'
          )}>
            {/* Main Weight Value */}
            <div className="text-center">
              <div className={clsx(
                'font-mono text-6xl font-bold tracking-tight transition-colors',
                isStable ? 'text-emerald-400' : 'text-slate-200'
              )}>
                {currentWeight.toFixed(3)}
              </div>
              <div className="text-lg text-slate-400 mt-1">kg</div>
            </div>
            
            {/* Stability Indicator */}
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-slate-500 uppercase tracking-wider">
                  Reading Stability
                </span>
                <span className={clsx(
                  'text-xs font-semibold px-2 py-0.5 rounded-full',
                  isStable 
                    ? 'bg-emerald-500/20 text-emerald-400' 
                    : stabilityPercent > 50
                      ? 'bg-amber-500/20 text-amber-400'
                      : 'bg-slate-700/50 text-slate-400'
                )}>
                  {isStable ? '✓ STABLE' : stabilityPercent > 50 ? 'Stabilizing...' : 'Waiting...'}
                </span>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className={clsx(
                    'h-full transition-all duration-300 rounded-full',
                    isStable 
                      ? 'bg-emerald-500' 
                      : stabilityPercent > 50 
                        ? 'bg-amber-500' 
                        : 'bg-slate-600'
                  )}
                  style={{ width: `${isStable ? 100 : stabilityPercent}%` }}
                />
              </div>
            </div>
            
            {/* Individual Load Cells */}
            <div className="mt-4 grid grid-cols-4 gap-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="text-center p-2 rounded-lg bg-slate-800/50">
                  <div className="text-[10px] text-slate-500 uppercase">LC{i}</div>
                  <div className="text-sm font-mono text-slate-300">
                    {(currentData?.[`load_cell_${i}_kg` as keyof LoadCellData] as number ?? 0).toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* Tare Section */}
          <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-500/5 border border-amber-500/20">
            <div className="text-2xl">💡</div>
            <div className="flex-1">
              <p className="text-sm text-amber-200/80">
                <strong>Tip:</strong> Use Tare to zero the scale before placing the gasket assembly,
                or to exclude fixture weight.
              </p>
            </div>
            <button
              onClick={handleTare}
              disabled={isTaring}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all',
                'bg-amber-500/20 border border-amber-500/40 text-amber-300',
                'hover:bg-amber-500/30 hover:border-amber-400/50',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              <RotateCcw size={16} className={isTaring ? 'animate-spin' : ''} />
              {isTaring ? 'Taring...' : 'Tare'}
            </button>
          </div>
          
          {/* Assembly Identification */}
          <div className="space-y-4">
            <h4 className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Assembly Identification (Optional)
            </h4>
            <div className="grid gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  Assembly ID
                </label>
                <input
                  type="text"
                  value={assemblyId}
                  onChange={(e) => setAssemblyId(e.target.value)}
                  placeholder="e.g., GASKET-001, FRAME-A-2025"
                  className="form-input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional notes: gasket material, frame type, batch number..."
                  rows={2}
                  className="form-input resize-none"
                />
              </div>
            </div>
          </div>
        </div>
        
        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-700/50 bg-slate-900/50">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500">
              {isStable 
                ? 'Reading stable - ready to capture' 
                : 'Wait for reading to stabilize (±10g for 1 second)'}
            </p>
            <div className="flex gap-3">
              <button
                onClick={onSkip}
                className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-xl border border-slate-700 transition-colors"
              >
                <SkipForward size={16} />
                Skip Weighing
              </button>
              <button
                onClick={handleCapture}
                disabled={!isStable}
                className={clsx(
                  'flex items-center gap-2 px-6 py-2.5 text-sm font-semibold rounded-xl transition-all duration-200',
                  isStable
                    ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-500/25'
                    : 'bg-slate-700 text-slate-400 cursor-not-allowed'
                )}
              >
                <Check size={18} />
                Capture Weight
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

