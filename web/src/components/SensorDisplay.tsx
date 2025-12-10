'use client';

import { clsx } from 'clsx';

interface SensorDisplayProps {
  label: string;
  value: number | null | undefined;
  unit: string;
  decimals?: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'primary' | 'warn' | 'error';
  showTrend?: boolean;
  previousValue?: number;
}

export function SensorDisplay({
  label,
  value,
  unit,
  decimals = 2,
  size = 'md',
  variant = 'default',
  showTrend = false,
  previousValue,
}: SensorDisplayProps) {
  const displayValue = value !== null && value !== undefined
    ? value.toFixed(decimals)
    : '---';

  const trend = showTrend && previousValue !== undefined && value !== undefined && value !== null
    ? (value > previousValue ? '↑' : value < previousValue ? '↓' : '→')
    : null;

  const sizeClasses = {
    sm: 'text-xl',
    md: 'text-3xl',
    lg: 'text-5xl',
  };

  const variantClasses = {
    default: 'lcd-value',
    primary: 'lcd-value',
    warn: 'lcd-value-warn',
    error: 'lcd-value-error',
  };

  return (
    <div className="lcd-display p-3 flex flex-col">
      <span className="text-xs text-gray-500 uppercase tracking-wider mb-1">
        {label}
      </span>
      <div className="flex items-baseline gap-2">
        <span className={clsx(sizeClasses[size], variantClasses[variant], 'font-mono tracking-tight')}>
          {displayValue}
        </span>
        <span className="text-sm text-gray-400">{unit}</span>
        {trend && (
          <span className={clsx(
            'text-lg',
            trend === '↑' ? 'text-red-400' : trend === '↓' ? 'text-green-400' : 'text-gray-500'
          )}>
            {trend}
          </span>
        )}
      </div>
    </div>
  );
}

interface LoadCellGridProps {
  loadCells: {
    cell1: number | null | undefined;
    cell2: number | null | undefined;
    cell3: number | null | undefined;
    cell4: number | null | undefined;
  };
  total: number | null | undefined;
}

export function LoadCellGrid({ loadCells, total }: LoadCellGridProps) {
  return (
    <div className="panel-card">
      <h3 className="panel-header">Load Cells</h3>
      
      {/* Total force - large display */}
      <div className="mb-4">
        <SensorDisplay
          label="Total Force"
          value={total}
          unit="kg"
          decimals={1}
          size="lg"
        />
      </div>
      
      {/* Individual cells - 2x2 grid */}
      <div className="grid grid-cols-2 gap-2">
        <SensorDisplay
          label="Cell 1"
          value={loadCells.cell1}
          unit="kg"
          decimals={1}
          size="sm"
        />
        <SensorDisplay
          label="Cell 2"
          value={loadCells.cell2}
          unit="kg"
          decimals={1}
          size="sm"
        />
        <SensorDisplay
          label="Cell 3"
          value={loadCells.cell3}
          unit="kg"
          decimals={1}
          size="sm"
        />
        <SensorDisplay
          label="Cell 4"
          value={loadCells.cell4}
          unit="kg"
          decimals={1}
          size="sm"
        />
      </div>
    </div>
  );
}

interface PressureDisplayProps {
  vacuumBar: number | null | undefined;
  pressurePsi: number | null | undefined;
  currentMa?: number | null | undefined;
}

export function PressureDisplay({ vacuumBar, pressurePsi, currentMa }: PressureDisplayProps) {
  // Determine variant based on vacuum level
  const getVariant = (vacuum: number | null | undefined): 'default' | 'warn' | 'error' => {
    if (vacuum === null || vacuum === undefined) return 'default';
    if (Math.abs(vacuum) > 0.8) return 'error';
    if (Math.abs(vacuum) > 0.5) return 'warn';
    return 'default';
  };

  return (
    <div className="panel-card">
      <h3 className="panel-header">Pressure</h3>
      
      {/* Main vacuum display */}
      <div className="mb-4">
        <SensorDisplay
          label="Vacuum"
          value={vacuumBar}
          unit="bar"
          decimals={3}
          size="lg"
          variant={getVariant(vacuumBar)}
        />
      </div>
      
      {/* Secondary displays */}
      <div className="grid grid-cols-2 gap-2">
        <SensorDisplay
          label="Gauge Pressure"
          value={pressurePsi}
          unit="PSI"
          decimals={2}
          size="sm"
        />
        {currentMa !== undefined && (
          <SensorDisplay
            label="Sensor Current"
            value={currentMa}
            unit="mA"
            decimals={2}
            size="sm"
          />
        )}
      </div>
    </div>
  );
}

interface ConnectionStatusProps {
  isConnected: boolean;
  widgetlordsConnected?: boolean;
  modbusConnected?: boolean;
}

export function ConnectionStatus({ isConnected, widgetlordsConnected, modbusConnected }: ConnectionStatusProps) {
  return (
    <div className="panel-card">
      <h3 className="panel-header">Connection Status</h3>
      <div className="space-y-2">
        <StatusItem label="WebSocket" connected={isConnected} />
        <StatusItem label="WidgetLords SPI" connected={widgetlordsConnected ?? false} />
        <StatusItem label="Modbus TLB4" connected={modbusConnected ?? false} />
      </div>
    </div>
  );
}

function StatusItem({ label, connected }: { label: string; connected: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-300">{label}</span>
      <div className="flex items-center gap-2">
        <div
          className={clsx(
            'status-indicator',
            connected ? 'status-indicator-running' : 'status-indicator-idle'
          )}
        />
        <span className={clsx('text-xs', connected ? 'text-green-400' : 'text-gray-500')}>
          {connected ? 'Connected' : 'Disconnected'}
        </span>
      </div>
    </div>
  );
}

