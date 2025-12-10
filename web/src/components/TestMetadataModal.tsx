'use client';

import { useState, useCallback, useEffect, useMemo } from 'react';
import { clsx } from 'clsx';
import { X, Play, Calendar, User, FlaskConical, FileText, Target, Clock, ChevronDown, ChevronUp, Info, Scale, RefreshCw } from 'lucide-react';
import type { GasketWeighingResult } from './GasketWeighingModal';

export interface TestMetadata {
  test_name: string;
  operator: string;
  date: string;
  test_id: string;
  material?: string;
  sample_id?: string;
  batch_lot?: string;
  target_vacuum_bar?: number;
  target_force_kg?: number;
  target_time_seconds?: number;
  notes?: string;
  include_test_description?: boolean;
  user_test_description?: string;
  [key: string]: string | number | boolean | undefined;
}

interface TestMetadataModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (metadata: TestMetadata) => void;
  sequenceName: string | null;
  isLoading?: boolean;
  gasketWeight?: GasketWeighingResult | null;
  onReweigh?: () => void;
}

function generateTestId(testName: string, date: Date): string {
  const sanitized = testName.trim().replace(/[^\w\-]/g, '_') || 'UNNAMED_TEST';
  const dateStr = date.toISOString().slice(0, 10).replace(/-/g, '');
  const timeStr = date.toTimeString().slice(0, 8).replace(/:/g, '');
  return `${sanitized}_${dateStr}_${timeStr}`;
}

function formatDateForInput(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function formatTimeForInput(date: Date): string {
  return date.toTimeString().slice(0, 5);
}

export function TestMetadataModal({
  isOpen,
  onClose,
  onSubmit,
  sequenceName,
  isLoading = false,
  gasketWeight,
  onReweigh,
}: TestMetadataModalProps) {
  // Form state
  const [testName, setTestName] = useState('');
  const [operator, setOperator] = useState('');
  const [date, setDate] = useState(formatDateForInput(new Date()));
  const [time, setTime] = useState(formatTimeForInput(new Date()));
  
  // Material info
  const [material, setMaterial] = useState('');
  const [sampleId, setSampleId] = useState('');
  const [batchLot, setBatchLot] = useState('');
  
  // Test targets
  const [targetVacuum, setTargetVacuum] = useState('');
  const [targetForce, setTargetForce] = useState('');
  const [targetTime, setTargetTime] = useState('');
  
  // Notes
  const [notes, setNotes] = useState('');
  
  // Test description
  const [includeDescription, setIncludeDescription] = useState(true);
  const [testDescription, setTestDescription] = useState(getDefaultDescription());
  
  // UI state
  const [expandedSections, setExpandedSections] = useState({
    basic: true,
    material: false,
    targets: false,
    notes: false,
    description: false,
  });
  
  // Validation
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  
  // Generate test ID
  const testId = useMemo(() => {
    const dateTime = new Date(`${date}T${time}`);
    return generateTestId(testName, dateTime);
  }, [testName, date, time]);
  
  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      const now = new Date();
      setDate(formatDateForInput(now));
      setTime(formatTimeForInput(now));
      setTouched({});
    }
  }, [isOpen]);
  
  const toggleSection = useCallback((section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  }, []);
  
  const handleBlur = useCallback((field: string) => {
    setTouched(prev => ({ ...prev, [field]: true }));
  }, []);
  
  const isValid = testName.trim().length > 0 && operator.trim().length > 0;
  
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    
    if (!isValid) {
      setTouched({ test_name: true, operator: true });
      return;
    }
    
    const metadata: TestMetadata = {
      test_name: testName.trim(),
      operator: operator.trim(),
      date: `${date} ${time}:00`,
      test_id: testId,
    };
    
    // Add optional fields
    if (material.trim()) metadata.material = material.trim();
    if (sampleId.trim()) metadata.sample_id = sampleId.trim();
    if (batchLot.trim()) metadata.batch_lot = batchLot.trim();
    
    const vacuum = parseFloat(targetVacuum);
    if (!isNaN(vacuum) && vacuum > 0) metadata.target_vacuum_bar = vacuum;
    
    const force = parseFloat(targetForce);
    if (!isNaN(force) && force > 0) metadata.target_force_kg = force;
    
    const timeVal = parseInt(targetTime);
    if (!isNaN(timeVal) && timeVal > 0) metadata.target_time_seconds = timeVal;
    
    if (notes.trim()) metadata.notes = notes.trim();
    
    metadata.include_test_description = includeDescription;
    if (includeDescription && testDescription.trim()) {
      metadata.user_test_description = testDescription.trim();
    }
    
    onSubmit(metadata);
  }, [isValid, testName, operator, date, time, testId, material, sampleId, batchLot, targetVacuum, targetForce, targetTime, notes, includeDescription, testDescription, onSubmit]);
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-hidden rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 border border-slate-700/50 shadow-2xl shadow-black/50">
        {/* Header */}
        <div className="relative px-6 py-5 border-b border-slate-700/50 bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <FlaskConical className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-100">Test Configuration</h2>
              <p className="text-sm text-slate-400">
                {sequenceName ? `Sequence: ${sequenceName}` : 'Configure test metadata before starting'}
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
        <form onSubmit={handleSubmit} className="overflow-y-auto max-h-[calc(90vh-180px)]">
          <div className="px-6 py-4 space-y-3">
            {/* Gasket Weight Section (shown if weight captured) */}
            {gasketWeight && (
              <div className="rounded-xl border-2 border-emerald-500/40 bg-gradient-to-br from-emerald-900/20 to-emerald-950/20 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30">
                      <Scale className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-emerald-300">Gasket Assembly Weight</h4>
                      <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold font-mono text-emerald-400">
                          {gasketWeight.weight_kg.toFixed(3)}
                        </span>
                        <span className="text-sm text-emerald-400/70">kg</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {gasketWeight.assembly_id && (
                      <span className="text-xs text-slate-400 bg-slate-800/50 px-2 py-1 rounded">
                        ID: {gasketWeight.assembly_id}
                      </span>
                    )}
                    {onReweigh && (
                      <button
                        type="button"
                        onClick={onReweigh}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-lg transition-colors"
                      >
                        <RefreshCw size={14} />
                        Re-weigh
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}
            
            {/* No weight captured hint */}
            {!gasketWeight && (
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4">
                <div className="flex items-start gap-3">
                  <Scale className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm text-amber-200/80">
                      <strong>Tip:</strong> Weigh the gasket assembly before starting the test using the 
                      &quot;Weigh Assembly&quot; button in the Control Panel. The weight will be recorded in the test data.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Basic Info Section */}
            <CollapsibleSection
              title="Test Information"
              icon={<FileText size={18} />}
              isExpanded={expandedSections.basic}
              onToggle={() => toggleSection('basic')}
              required
            >
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <FormField
                    label="Test Name"
                    required
                    error={touched.test_name && !testName.trim() ? 'Test name is required' : undefined}
                  >
                    <input
                      type="text"
                      value={testName}
                      onChange={(e) => setTestName(e.target.value)}
                      onBlur={() => handleBlur('test_name')}
                      placeholder="e.g., EPDM_Seal_Test_001"
                      className="form-input"
                    />
                  </FormField>
                </div>
                
                <div className="col-span-2 sm:col-span-1">
                  <FormField
                    label="Operator"
                    required
                    error={touched.operator && !operator.trim() ? 'Operator is required' : undefined}
                  >
                    <div className="relative">
                      <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                      <input
                        type="text"
                        value={operator}
                        onChange={(e) => setOperator(e.target.value)}
                        onBlur={() => handleBlur('operator')}
                        placeholder="e.g., John Smith"
                        className="form-input pl-10"
                      />
                    </div>
                  </FormField>
                </div>
                
                <div className="col-span-2 sm:col-span-1 grid grid-cols-2 gap-3">
                  <FormField label="Date" required>
                    <div className="relative">
                      <Calendar size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                      <input
                        type="date"
                        value={date}
                        onChange={(e) => setDate(e.target.value)}
                        className="form-input pl-10"
                      />
                    </div>
                  </FormField>
                  <FormField label="Time" required>
                    <input
                      type="time"
                      value={time}
                      onChange={(e) => setTime(e.target.value)}
                      className="form-input"
                    />
                  </FormField>
                </div>
                
                <div className="col-span-2">
                  <FormField label="Test ID" hint="Auto-generated from test name and timestamp">
                    <input
                      type="text"
                      value={testId}
                      readOnly
                      className="form-input bg-slate-800/50 text-slate-400 cursor-not-allowed"
                    />
                  </FormField>
                </div>
              </div>
            </CollapsibleSection>
            
            {/* Material Info Section */}
            <CollapsibleSection
              title="Material Information"
              icon={<FlaskConical size={18} />}
              isExpanded={expandedSections.material}
              onToggle={() => toggleSection('material')}
            >
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2 sm:col-span-1">
                  <FormField label="Material">
                    <input
                      type="text"
                      value={material}
                      onChange={(e) => setMaterial(e.target.value)}
                      placeholder="e.g., EPDM 70 Shore A"
                      className="form-input"
                    />
                  </FormField>
                </div>
                <div className="col-span-2 sm:col-span-1">
                  <FormField label="Sample ID">
                    <input
                      type="text"
                      value={sampleId}
                      onChange={(e) => setSampleId(e.target.value)}
                      placeholder="e.g., SAMPLE-2025-001"
                      className="form-input"
                    />
                  </FormField>
                </div>
                <div className="col-span-2 sm:col-span-1">
                  <FormField label="Batch / Lot">
                    <input
                      type="text"
                      value={batchLot}
                      onChange={(e) => setBatchLot(e.target.value)}
                      placeholder="e.g., LOT-ABC123"
                      className="form-input"
                    />
                  </FormField>
                </div>
              </div>
            </CollapsibleSection>
            
            {/* Test Targets Section */}
            <CollapsibleSection
              title="Test Targets"
              icon={<Target size={18} />}
              isExpanded={expandedSections.targets}
              onToggle={() => toggleSection('targets')}
              hint="Optional pass/fail criteria"
            >
              <div className="grid grid-cols-3 gap-4">
                <FormField label="Target Vacuum">
                  <div className="relative">
                    <input
                      type="number"
                      step="0.001"
                      min="0"
                      max="1"
                      value={targetVacuum}
                      onChange={(e) => setTargetVacuum(e.target.value)}
                      placeholder="0.300"
                      className="form-input pr-12"
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">bar</span>
                  </div>
                </FormField>
                <FormField label="Target Force">
                  <div className="relative">
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="1000"
                      value={targetForce}
                      onChange={(e) => setTargetForce(e.target.value)}
                      placeholder="0.0"
                      className="form-input pr-10"
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">kg</span>
                  </div>
                </FormField>
                <FormField label="Target Time">
                  <div className="relative">
                    <Clock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input
                      type="number"
                      step="1"
                      min="0"
                      max="86400"
                      value={targetTime}
                      onChange={(e) => setTargetTime(e.target.value)}
                      placeholder="0"
                      className="form-input pl-10 pr-8"
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">s</span>
                  </div>
                </FormField>
              </div>
            </CollapsibleSection>
            
            {/* Notes Section */}
            <CollapsibleSection
              title="Notes"
              icon={<FileText size={18} />}
              isExpanded={expandedSections.notes}
              onToggle={() => toggleSection('notes')}
            >
              <FormField>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Additional notes or observations about this test..."
                  rows={3}
                  className="form-input resize-none"
                />
              </FormField>
            </CollapsibleSection>
            
            {/* Test Description Section */}
            <CollapsibleSection
              title="Test Description for Data Analysis"
              icon={<Info size={18} />}
              isExpanded={expandedSections.description}
              onToggle={() => toggleSection('description')}
              hint="Helps AI/LLM analyze results"
            >
              <div className="space-y-3">
                <label className="flex items-center gap-3 cursor-pointer group">
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={includeDescription}
                      onChange={(e) => setIncludeDescription(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-10 h-6 rounded-full bg-slate-700 peer-checked:bg-emerald-500/80 transition-colors" />
                    <div className="absolute top-1 left-1 w-4 h-4 rounded-full bg-slate-300 peer-checked:bg-white peer-checked:translate-x-4 transition-all" />
                  </div>
                  <span className="text-sm text-slate-300 group-hover:text-slate-100 transition-colors">
                    Include test description in metadata
                  </span>
                </label>
                
                {includeDescription && (
                  <>
                    <textarea
                      value={testDescription}
                      onChange={(e) => setTestDescription(e.target.value)}
                      rows={8}
                      className="form-input resize-none font-mono text-xs leading-relaxed"
                    />
                    <button
                      type="button"
                      onClick={() => setTestDescription(getDefaultDescription())}
                      className="text-xs text-slate-400 hover:text-emerald-400 transition-colors"
                    >
                      Reset to default
                    </button>
                  </>
                )}
              </div>
            </CollapsibleSection>
          </div>
        </form>
        
        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-700/50 bg-slate-900/50">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500">
              Data will be saved to <code className="text-slate-400">data/{testId}.csv</code>
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
                onClick={handleSubmit}
                disabled={!isValid || isLoading}
                className={clsx(
                  'flex items-center gap-2 px-5 py-2 text-sm font-medium rounded-lg transition-all',
                  isValid && !isLoading
                    ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-500/25'
                    : 'bg-slate-700 text-slate-400 cursor-not-allowed'
                )}
              >
                <Play size={16} />
                {isLoading ? 'Starting...' : 'Start Test'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Collapsible Section Component
interface CollapsibleSectionProps {
  title: string;
  icon: React.ReactNode;
  isExpanded: boolean;
  onToggle: () => void;
  required?: boolean;
  hint?: string;
  children: React.ReactNode;
}

function CollapsibleSection({ title, icon, isExpanded, onToggle, required, hint, children }: CollapsibleSectionProps) {
  return (
    <div className={clsx(
      'rounded-xl border transition-colors',
      isExpanded 
        ? 'border-slate-600/50 bg-slate-800/30' 
        : 'border-slate-700/30 bg-slate-800/10 hover:border-slate-600/40'
    )}>
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-slate-400">{icon}</span>
          <span className="font-medium text-slate-200">{title}</span>
          {required && (
            <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-amber-400 bg-amber-400/10 rounded">
              Required
            </span>
          )}
          {hint && !required && (
            <span className="text-xs text-slate-500">{hint}</span>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp size={18} className="text-slate-400" />
        ) : (
          <ChevronDown size={18} className="text-slate-400" />
        )}
      </button>
      
      {isExpanded && (
        <div className="px-4 pb-4">
          {children}
        </div>
      )}
    </div>
  );
}

// Form Field Component
interface FormFieldProps {
  label?: string;
  required?: boolean;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}

function FormField({ label, required, error, hint, children }: FormFieldProps) {
  return (
    <div className="space-y-1.5">
      {label && (
        <label className="block text-sm font-medium text-slate-300">
          {label}
          {required && <span className="text-amber-400 ml-0.5">*</span>}
        </label>
      )}
      {children}
      {error && (
        <p className="text-xs text-red-400">{error}</p>
      )}
      {hint && !error && (
        <p className="text-xs text-slate-500">{hint}</p>
      )}
    </div>
  );
}

function getDefaultDescription(): string {
  return `## EPDM Gasket Vacuum Seal Test - Operation Description

### Purpose
This test evaluates the vacuum sealing performance of EPDM gaskets by:
1. Drawing vacuum in a sealed test chamber containing the gasket
2. Monitoring vacuum level and force over time
3. Detecting any vacuum loss (leak) through the gasket seal

### Test Hardware Operation

**Vacuum System:**
- A vacuum pump creates negative pressure (vacuum) in the test chamber
- A vacuum isolation valve connects/disconnects the pump from the chamber
- A vent valve allows the chamber to return to atmospheric pressure

**Measurement System:**
- Pressure sensor measures chamber pressure (negative PSIG = vacuum)
- Load cells measure compression force on the gasket (in kg)

### Typical Test Sequence Flow

**Stage 1 - Evacuation:**
- Vent valve CLOSES (seals chamber from atmosphere)
- Vacuum valve OPENS (connects pump to chamber)
- Pump runs in CONTINUOUS mode
- Stage completes when target vacuum is reached OR time limit expires

**Stage 2 - Hold/Leak Check:**
- Vacuum valve CLOSES (isolates chamber from pump)
- Pump turns OFF
- Any vacuum loss indicates a leak through the gasket
- Leak rate = change in vacuum over time

**Stage 3 - Vent:**
- Vent valve OPENS (allows air into chamber)
- Chamber returns to atmospheric pressure

### How to Analyze the Data

**For Seal Quality Assessment:**
1. Find the "Hold" stage data
2. Calculate leak rate: vacuum_change / hold_time (mbar/min)
3. Lower leak rate = better seal

**Key Indicators:**
- vacuum_bar increasing during evacuation = system working correctly
- vacuum_bar stable during hold = good seal
- vacuum_bar decreasing during hold = leak detected`;
}

