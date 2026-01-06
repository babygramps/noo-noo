'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSensorData } from '@/hooks/useWebSocket';
import { SensorDisplay, LoadCellGrid, PressureDisplay, ConnectionStatus } from '@/components/SensorDisplay';
import { LiveChart } from '@/components/LiveChart';
import { ControlPanel, IOStatusDisplay } from '@/components/ControlPanel';
import { StageProgress, StageList } from '@/components/StageProgress';
import { TestMetadataModal, TestMetadata } from '@/components/TestMetadataModal';
import { TestDataBrowser } from '@/components/TestDataBrowser';
import { GasketWeighingModal, GasketWeighingResult } from '@/components/GasketWeighingModal';
import { SequenceEditorModal } from '@/components/SequenceEditorModal';
import { JokeTicker } from '@/components/JokeTicker';
import * as api from '@/lib/api';
import type { SequenceSummary, Sequence } from '@/lib/api';
import { Activity, Gauge, Scale, Settings, HardDrive } from 'lucide-react';
import Image from 'next/image';

export default function Dashboard() {
  // WebSocket sensor data
  const {
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
  } = useSensorData(600); // 1 minute of data at 10Hz

  // Local state
  const [sequences, setSequences] = useState<SequenceSummary[]>([]);
  const [selectedSequenceName, setSelectedSequenceName] = useState<string | null>(null);
  const [selectedSequence, setSelectedSequence] = useState<Sequence | null>(null);
  const [systemStatus, setSystemStatus] = useState<api.SystemStatus | null>(null);
  
  // Modal state
  const [isMetadataModalOpen, setIsMetadataModalOpen] = useState(false);
  const [isStartingTest, setIsStartingTest] = useState(false);
  const [currentMetadata, setCurrentMetadata] = useState<TestMetadata | null>(null);
  const [isDataBrowserOpen, setIsDataBrowserOpen] = useState(false);
  
  // Gasket weighing state
  const [isWeighingModalOpen, setIsWeighingModalOpen] = useState(false);
  const [gasketWeighingResult, setGasketWeighingResult] = useState<GasketWeighingResult | null>(null);
  
  // Sequence editor state
  const [isSequenceEditorOpen, setIsSequenceEditorOpen] = useState(false);
  const [sequenceToEdit, setSequenceToEdit] = useState<Sequence | null>(null);

  // Fetch sequences on mount
  useEffect(() => {
    async function loadSequences() {
      try {
        const seqs = await api.listSequences();
        setSequences(seqs);
        // Select first sequence by default
        if (seqs.length > 0 && !selectedSequenceName) {
          setSelectedSequenceName(seqs[0].name);
        }
      } catch (error) {
        console.error('Failed to load sequences:', error);
      }
    }

    loadSequences();
  }, [selectedSequenceName]);

  // Fetch full sequence details when selection changes
  useEffect(() => {
    async function loadSequenceDetails() {
      if (!selectedSequenceName) {
        setSelectedSequence(null);
        return;
      }

      try {
        const seq = await api.getSequence(selectedSequenceName);
        setSelectedSequence(seq);
      } catch (error) {
        console.error('Failed to load sequence details:', error);
      }
    }

    loadSequenceDetails();
  }, [selectedSequenceName]);

  // Fetch system status periodically
  useEffect(() => {
    async function loadStatus() {
      try {
        const status = await api.getStatus();
        setSystemStatus(status);
      } catch (error) {
        console.error('Failed to load status:', error);
      }
    }

    loadStatus();
    const interval = setInterval(loadStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Handlers
  const handleStartTestRequest = useCallback(() => {
    if (!selectedSequenceName) return;
    setIsMetadataModalOpen(true);
  }, [selectedSequenceName]);
  
  const handleWeighAssembly = useCallback(() => {
    setIsWeighingModalOpen(true);
  }, []);
  
  const handleWeighingCapture = useCallback((result: GasketWeighingResult) => {
    setGasketWeighingResult(result);
    setIsWeighingModalOpen(false);
    // Optionally open metadata modal to start test
    // setIsMetadataModalOpen(true);
  }, []);
  
  const handleWeighingSkip = useCallback(() => {
    setGasketWeighingResult(null);
    setIsWeighingModalOpen(false);
  }, []);
  
  const handleMetadataSubmit = useCallback(async (metadata: TestMetadata) => {
    if (!selectedSequenceName) return;
    
    setIsStartingTest(true);
    
    // Merge gasket weighing result into metadata
    const enhancedMetadata: Record<string, unknown> = { ...metadata };
    if (gasketWeighingResult) {
      enhancedMetadata.gasket_assembly_weight_kg = gasketWeighingResult.weight_kg;
      enhancedMetadata.gasket_assembly_id = gasketWeighingResult.assembly_id || null;
      enhancedMetadata.gasket_assembly_description = gasketWeighingResult.assembly_description || null;
      enhancedMetadata.gasket_weight_timestamp = gasketWeighingResult.timestamp;
      enhancedMetadata.gasket_weight_tared = gasketWeighingResult.is_tared;
      enhancedMetadata.gasket_weight_individual_cells_kg = gasketWeighingResult.individual_cells;
    }
    
    setCurrentMetadata(metadata);
    
    try {
      const result = await api.startTest(selectedSequenceName, enhancedMetadata);
      if (result.success) {
        clearHistory();
        setIsMetadataModalOpen(false);
        setGasketWeighingResult(null); // Clear after test starts
      } else {
        console.error('Failed to start test:', result.message);
      }
    } catch (error) {
      console.error('Failed to start test:', error);
    } finally {
      setIsStartingTest(false);
    }
  }, [selectedSequenceName, clearHistory, gasketWeighingResult]);

  const handleTestStopped = useCallback(() => {
    setCurrentMetadata(null);
  }, []);

  const handleSequenceSelect = useCallback((name: string) => {
    setSelectedSequenceName(name || null);
  }, []);
  
  // Sequence editor handlers
  const handleNewSequence = useCallback(() => {
    setSequenceToEdit(null);
    setIsSequenceEditorOpen(true);
  }, []);
  
  const handleEditSequence = useCallback(() => {
    if (selectedSequence) {
      setSequenceToEdit(selectedSequence);
      setIsSequenceEditorOpen(true);
    }
  }, [selectedSequence]);
  
  const handleSaveSequence = useCallback(async (sequence: Sequence): Promise<boolean> => {
    try {
      console.log('[Dashboard] Saving sequence:', sequence.name);
      const result = await api.saveSequence(sequence);
      if (result.success) {
        // Reload sequences list
        const seqs = await api.listSequences();
        setSequences(seqs);
        // Select the new/updated sequence
        setSelectedSequenceName(sequence.name);
        return true;
      }
      console.error('[Dashboard] Failed to save sequence:', result.message);
      return false;
    } catch (error) {
      console.error('[Dashboard] Error saving sequence:', error);
      return false;
    }
  }, []);

  // Get target vacuum from current stage
  const targetVacuum = selectedSequence?.stages?.[stageInfo?.stage_index ?? 0]?.target_vacuum_bar ?? null;

  return (
    <div className="min-h-screen bg-panel-bg bg-grid bg-radial-fade">
      {/* Joke Ticker - above header when system is idle */}
      {!testRunning && currentJoke && (
        <JokeTicker joke={currentJoke} isConnected={isConnected} />
      )}
      
      {/* Header */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-panel-bg/80 border-b border-panel-border/50">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500/20 to-yellow-500/20 border border-amber-500/30 overflow-hidden">
                  <Image
                    src="/noo-noo-logo.png"
                    alt="Noo-Noo"
                    width={40}
                    height={40}
                    className="object-contain"
                    priority
                  />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gradient">
                    Noo-Noo
                  </h1>
                  <p className="text-xs text-slate-500 tracking-wide">
                    Vacuum Seal Test System
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {/* Current Test Info Badge */}
              {testRunning && currentMetadata && (
                <div className="hidden md:flex items-center gap-3 px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
                  <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
                  <div className="text-sm">
                    <span className="text-emerald-400 font-medium">{currentMetadata.test_name}</span>
                    {currentMetadata.operator && (
                      <span className="text-slate-500 ml-2">by {currentMetadata.operator}</span>
                    )}
                  </div>
                </div>
              )}
              
              {/* Test Data Browser Button */}
              <button
                onClick={() => setIsDataBrowserOpen(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20 hover:border-cyan-500/50 transition-all"
                title="View Test Data"
              >
                <HardDrive className="w-4 h-4" />
                <span className="hidden sm:inline text-sm font-medium">Data</span>
              </button>
              
              {/* Connection Status */}
              <div className="flex items-center gap-3 px-4 py-2 rounded-xl bg-panel-surface border border-panel-border">
                <div
                  className={`status-indicator ${
                    isConnected ? 'status-indicator-running' : 'status-indicator-error'
                  }`}
                />
                <span className="text-sm text-slate-400">
                  {isConnected ? 'Live' : 'Offline'}
                </span>
              </div>
              
              {/* Test Running Badge */}
              {testRunning && (
                <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/15 border border-emerald-500/40 animate-glow-pulse">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span className="text-emerald-400 text-sm font-semibold tracking-wide">
                    RECORDING
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="px-6 py-6">
        <div className="grid grid-cols-12 gap-5">
          {/* Left sidebar - Sensor displays */}
          <div className="col-span-12 lg:col-span-3 space-y-5">
            {/* Pressure Card */}
            <div className="panel-card">
              <div className="flex items-center gap-2 mb-4">
                <Gauge className="w-4 h-4 text-teal-400" />
                <h3 className="panel-header mb-0">Pressure</h3>
              </div>
              <PressureDisplay
                vacuumBar={currentData?.vacuum_bar}
                pressurePsi={currentData?.pressure_psi}
                currentMa={currentData?.pressure_mA}
              />
            </div>
            
            {/* Load Cells Card */}
            <div className="panel-card">
              <div className="flex items-center gap-2 mb-4">
                <Scale className="w-4 h-4 text-blue-400" />
                <h3 className="panel-header mb-0">Load Cells</h3>
              </div>
              <LoadCellGrid
                loadCells={{
                  cell1: currentData?.load_cell_1_kg,
                  cell2: currentData?.load_cell_2_kg,
                  cell3: currentData?.load_cell_3_kg,
                  cell4: currentData?.load_cell_4_kg,
                }}
                total={currentData?.total_force_kg ?? currentData?.gross_weight_kg}
              />
            </div>

            <IOStatusDisplay ioStates={ioStates} />

            <ConnectionStatus
              isConnected={isConnected}
              widgetlordsConnected={systemStatus?.widgetlords_connected}
              modbusConnected={systemStatus?.modbus_connected}
            />
          </div>

          {/* Center - Main chart */}
          <div className="col-span-12 lg:col-span-6 space-y-5">
            <div className="panel-card-elevated h-[480px]">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-teal-400" />
                  <h3 className="panel-header mb-0">Real-Time Data</h3>
                </div>
                {dataHistory.length > 0 && (
                  <span className="text-xs text-slate-500">
                    {dataHistory.length} samples
                  </span>
                )}
              </div>
              <div className="h-[calc(100%-3rem)]">
                <LiveChart
                  data={dataHistory}
                  showVacuum={true}
                  showForce={true}
                  targetVacuum={targetVacuum}
                />
              </div>
            </div>

            {/* Sequence list below chart */}
            <StageList
              sequence={selectedSequence}
              currentStageIndex={stageInfo?.stage_index ?? -1}
            />
          </div>

          {/* Right sidebar - Controls */}
          <div className="col-span-12 lg:col-span-3 space-y-5">
            <StageProgress
              testRunning={testRunning}
              stageInfo={stageInfo}
              progress={progress}
              statusMessage={statusMessage}
              sequence={selectedSequence}
            />

            <ControlPanel
              testRunning={testRunning}
              ioStates={ioStates}
              sequences={sequences}
              selectedSequence={selectedSequenceName}
              onSequenceSelect={handleSequenceSelect}
              onStartTestRequest={handleStartTestRequest}
              onTestStopped={handleTestStopped}
              onTareComplete={clearHistory}
              onWeighAssembly={handleWeighAssembly}
              onNewSequence={handleNewSequence}
              onEditSequence={handleEditSequence}
            />
            
            {/* Current Test Metadata Summary */}
            {testRunning && currentMetadata && (
              <div className="panel-card">
                <h3 className="panel-header">Current Test</h3>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Test ID</span>
                    <span className="text-slate-300 font-mono text-xs">{currentMetadata.test_id}</span>
                  </div>
                  {currentMetadata.material && (
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Material</span>
                      <span className="text-slate-300">{currentMetadata.material}</span>
                    </div>
                  )}
                  {currentMetadata.sample_id && (
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Sample</span>
                      <span className="text-slate-300">{currentMetadata.sample_id}</span>
                    </div>
                  )}
                  {currentMetadata.notes && (
                    <div className="pt-2 border-t border-panel-border">
                      <p className="text-xs text-slate-500 mb-1">Notes</p>
                      <p className="text-sm text-slate-400 line-clamp-2">{currentMetadata.notes}</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="px-6 py-4 border-t border-panel-border/50 bg-panel-bg/50">
        <div className="flex items-center justify-between text-xs text-slate-600">
          <div className="flex items-center gap-4">
            <span>EPDM Vacuum Fixture v2.0.0</span>
            <span className="text-slate-700">•</span>
            <span>Noo-Noo Web Interface</span>
          </div>
          <span suppressHydrationWarning className="font-mono">
            {currentData?.datetime || '---'}
          </span>
        </div>
      </footer>
      
      {/* Gasket Weighing Modal */}
      <GasketWeighingModal
        isOpen={isWeighingModalOpen}
        onClose={() => setIsWeighingModalOpen(false)}
        onCapture={handleWeighingCapture}
        onSkip={handleWeighingSkip}
        currentData={currentData}
      />
      
      {/* Test Metadata Modal */}
      <TestMetadataModal
        isOpen={isMetadataModalOpen}
        onClose={() => setIsMetadataModalOpen(false)}
        onSubmit={handleMetadataSubmit}
        sequenceName={selectedSequenceName}
        isLoading={isStartingTest}
        gasketWeight={gasketWeighingResult}
        onReweigh={() => {
          setIsMetadataModalOpen(false);
          setIsWeighingModalOpen(true);
        }}
      />
      
      {/* Test Data Browser Modal */}
      <TestDataBrowser
        isOpen={isDataBrowserOpen}
        onClose={() => setIsDataBrowserOpen(false)}
      />
      
      {/* Sequence Editor Modal */}
      <SequenceEditorModal
        isOpen={isSequenceEditorOpen}
        onClose={() => {
          setIsSequenceEditorOpen(false);
          setSequenceToEdit(null);
        }}
        onSave={handleSaveSequence}
        initialSequence={sequenceToEdit}
        existingSequenceNames={sequences.map(s => s.name)}
      />
    </div>
  );
}
