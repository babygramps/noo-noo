'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSensorData } from '@/hooks/useWebSocket';
import { SensorDisplay, LoadCellGrid, PressureDisplay, ConnectionStatus } from '@/components/SensorDisplay';
import { LiveChart } from '@/components/LiveChart';
import { ControlPanel, IOStatusDisplay } from '@/components/ControlPanel';
import { StageProgress, StageList } from '@/components/StageProgress';
import * as api from '@/lib/api';
import type { SequenceSummary, Sequence } from '@/lib/api';

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
    clearHistory,
  } = useSensorData(600); // 1 minute of data at 10Hz

  // Local state
  const [sequences, setSequences] = useState<SequenceSummary[]>([]);
  const [selectedSequenceName, setSelectedSequenceName] = useState<string | null>(null);
  const [selectedSequence, setSelectedSequence] = useState<Sequence | null>(null);
  const [systemStatus, setSystemStatus] = useState<api.SystemStatus | null>(null);

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
  const handleTestStarted = useCallback(() => {
    clearHistory();
  }, [clearHistory]);

  const handleTestStopped = useCallback(() => {
    // Test stopped
  }, []);

  const handleSequenceSelect = useCallback((name: string) => {
    setSelectedSequenceName(name || null);
  }, []);

  // Get target vacuum from current stage
  const targetVacuum = selectedSequence?.stages?.[stageInfo?.stage_index ?? 0]?.target_vacuum_bar ?? null;

  return (
    <div className="min-h-screen bg-panel-bg p-4">
      {/* Header */}
      <header className="mb-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">
              Noo-Noo
            </h1>
            <p className="text-sm text-gray-500">
              Web Control Interface
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div
                className={`status-indicator ${
                  isConnected ? 'status-indicator-running' : 'status-indicator-error'
                }`}
              />
              <span className="text-sm text-gray-400">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            {testRunning && (
              <div className="bg-green-900/50 border border-green-700 rounded-lg px-3 py-1">
                <span className="text-green-400 text-sm font-medium animate-pulse">
                  TEST RUNNING
                </span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main content grid */}
      <div className="grid grid-cols-12 gap-4">
        {/* Left sidebar - Sensor displays */}
        <div className="col-span-12 lg:col-span-3 space-y-4">
          <PressureDisplay
            vacuumBar={currentData?.vacuum_bar}
            pressurePsi={currentData?.pressure_psi}
            currentMa={currentData?.pressure_mA}
          />
          
          <LoadCellGrid
            loadCells={{
              cell1: currentData?.load_cell_1_kg,
              cell2: currentData?.load_cell_2_kg,
              cell3: currentData?.load_cell_3_kg,
              cell4: currentData?.load_cell_4_kg,
            }}
            total={currentData?.total_force_kg}
          />

          <IOStatusDisplay ioStates={ioStates} />

          <ConnectionStatus
            isConnected={isConnected}
            widgetlordsConnected={systemStatus?.widgetlords_connected}
            modbusConnected={systemStatus?.modbus_connected}
          />
        </div>

        {/* Center - Main chart */}
        <div className="col-span-12 lg:col-span-6">
          <div className="panel-card h-[500px]">
            <h3 className="panel-header">Real-Time Data</h3>
            <div className="h-[calc(100%-2rem)]">
              <LiveChart
                data={dataHistory}
                showVacuum={true}
                showForce={true}
                targetVacuum={targetVacuum}
              />
            </div>
          </div>

          {/* Sequence list below chart */}
          <div className="mt-4">
            <StageList
              sequence={selectedSequence}
              currentStageIndex={stageInfo?.stage_index ?? -1}
            />
          </div>
        </div>

        {/* Right sidebar - Controls */}
        <div className="col-span-12 lg:col-span-3 space-y-4">
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
            onTestStarted={handleTestStarted}
            onTestStopped={handleTestStopped}
          />
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-8 pt-4 border-t border-panel-border">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>EPDM Vacuum Fixture v2.0.0</span>
          <span suppressHydrationWarning>
            {currentData?.datetime || '---'}
          </span>
        </div>
      </footer>
    </div>
  );
}


