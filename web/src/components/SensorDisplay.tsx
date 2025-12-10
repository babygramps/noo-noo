'use client';

import { clsx } from 'clsx';
import { Wifi, WifiOff, Server, Cpu } from 'lucide-react';

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
    lg: 'text-4xl',
  };

  const variantClasses = {
    default: 'lcd-value',
    primary: 'lcd-value',
    warn: 'lcd-value-warn',
    error: 'lcd-value-error',
  };

  return (
    <div className="lcd-display p-4">
      <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">
        {label}
      </span>
      <div className="flex items-baseline gap-2 mt-1">
        <span className={clsx(sizeClasses[size], variantClasses[variant], 'tracking-tight')}>
          {displayValue}
        </span>
        <span className="text-sm text-slate-500 font-medium">{unit}</span>
        {trend && (
          <span className={clsx(
            'text-lg font-bold',
            trend === '↑' ? 'text-red-400' : trend === '↓' ? 'text-emerald-400' : 'text-slate-600'
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
    <div className="space-y-3">
      {/* Total force - large display */}
      <div className="lcd-display p-4">
        <div className="flex items-baseline justify-between">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">
            Total Force
          </span>
          <span className="text-sm text-slate-500 font-medium">kg</span>
        </div>
        <div className="lcd-value text-4xl tracking-tight mt-1">
          {total !== null && total !== undefined ? total.toFixed(1) : '---'}
        </div>
      </div>
      
      {/* Individual cells - 2x2 grid */}
      <div className="grid grid-cols-2 gap-2">
        <MiniLoadCell label="Cell 1" value={loadCells.cell1} />
        <MiniLoadCell label="Cell 2" value={loadCells.cell2} />
        <MiniLoadCell label="Cell 3" value={loadCells.cell3} />
        <MiniLoadCell label="Cell 4" value={loadCells.cell4} />
      </div>
    </div>
  );
}

function MiniLoadCell({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <div className="lcd-display p-2.5">
      <div className="text-[9px] text-slate-500 uppercase tracking-wider mb-0.5">{label}</div>
      <div className="flex items-baseline gap-1">
        <span className="lcd-value text-lg tracking-tight">
          {value !== null && value !== undefined ? value.toFixed(1) : '---'}
        </span>
        <span className="text-[10px] text-slate-600">kg</span>
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

  const variant = getVariant(vacuumBar);

  return (
    <div className="space-y-3">
      {/* Main vacuum display */}
      <div className="lcd-display p-4">
        <div className="flex items-baseline justify-between">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">
            Vacuum
          </span>
          <span className="text-sm text-slate-500 font-medium">bar</span>
        </div>
        <div className={clsx(
          'text-4xl tracking-tight mt-1',
          variant === 'error' ? 'lcd-value-error' : variant === 'warn' ? 'lcd-value-warn' : 'lcd-value'
        )}>
          {vacuumBar !== null && vacuumBar !== undefined ? Math.abs(vacuumBar).toFixed(3) : '---'}
        </div>
      </div>
      
      {/* Secondary displays */}
      <div className="grid grid-cols-2 gap-2">
        <div className="lcd-display p-2.5">
          <div className="text-[9px] text-slate-500 uppercase tracking-wider mb-0.5">Gauge</div>
          <div className="flex items-baseline gap-1">
            <span className="lcd-value text-lg tracking-tight">
              {pressurePsi !== null && pressurePsi !== undefined ? pressurePsi.toFixed(2) : '---'}
            </span>
            <span className="text-[10px] text-slate-600">PSI</span>
          </div>
        </div>
        {currentMa !== undefined && (
          <div className="lcd-display p-2.5">
            <div className="text-[9px] text-slate-500 uppercase tracking-wider mb-0.5">Sensor</div>
            <div className="flex items-baseline gap-1">
              <span className="lcd-value-dim text-lg tracking-tight">
                {currentMa !== null ? currentMa.toFixed(2) : '---'}
              </span>
              <span className="text-[10px] text-slate-600">mA</span>
            </div>
          </div>
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
      <h3 className="panel-header">Connections</h3>
      <div className="space-y-2">
        <StatusItem 
          label="WebSocket" 
          connected={isConnected} 
          icon={isConnected ? <Wifi size={14} /> : <WifiOff size={14} />}
        />
        <StatusItem 
          label="SPI Interface" 
          connected={widgetlordsConnected ?? false}
          icon={<Cpu size={14} />}
        />
        <StatusItem 
          label="Modbus RTU" 
          connected={modbusConnected ?? false}
          icon={<Server size={14} />}
        />
      </div>
    </div>
  );
}

function StatusItem({ 
  label, 
  connected,
  icon 
}: { 
  label: string; 
  connected: boolean;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between py-2 px-3 rounded-lg bg-panel-bg/50 border border-panel-border/30">
      <div className="flex items-center gap-2.5">
        <span className={clsx(
          connected ? 'text-emerald-400' : 'text-slate-600'
        )}>
          {icon}
        </span>
        <span className="text-sm text-slate-300">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <div
          className={clsx(
            'status-indicator',
            connected ? 'status-indicator-running' : 'status-indicator-idle'
          )}
        />
        <span className={clsx(
          'text-xs font-medium',
          connected ? 'text-emerald-400' : 'text-slate-600'
        )}>
          {connected ? 'OK' : '---'}
        </span>
      </div>
    </div>
  );
}
