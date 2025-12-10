'use client';

import { useMemo } from 'react';
import Image from 'next/image';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { SensorData } from '@/lib/api';

interface LiveChartProps {
  data: SensorData[];
  showVacuum?: boolean;
  showForce?: boolean;
  targetVacuum?: number | null;
  maxPoints?: number;
}

export function LiveChart({
  data,
  showVacuum = true,
  showForce = true,
  targetVacuum,
  maxPoints = 300,
}: LiveChartProps) {
  // Transform data for chart
  const chartData = useMemo(() => {
    const slicedData = data.slice(-maxPoints);
    
    return slicedData.map((d, index) => ({
      index,
      time: d.timestamp,
      vacuum: Math.abs(d.vacuum_bar || 0),
      // Use total_force_kg (sum of software-tared load cells) with fallback to gross_weight_kg
      force: d.total_force_kg ?? d.gross_weight_kg ?? 0,
      label: new Date(d.timestamp * 1000).toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }),
    }));
  }, [data, maxPoints]);

  // Calculate Y axis domains
  const vacuumDomain = useMemo(() => {
    if (!showVacuum || chartData.length === 0) return [0, 1];
    const maxVacuum = Math.max(...chartData.map(d => d.vacuum), targetVacuum || 0.5, 0.1);
    return [0, Math.ceil(maxVacuum * 10) / 10 + 0.1];
  }, [chartData, showVacuum, targetVacuum]);

  const forceDomain = useMemo(() => {
    if (!showForce || chartData.length === 0) return [0, 100];
    const maxForce = Math.max(...chartData.map(d => d.force), 100);
    return [0, Math.ceil(maxForce / 50) * 50 + 50];
  }, [chartData, showForce]);

  if (chartData.length === 0) {
    return (
      <div className="relative h-full w-full">
        {/* Watermark */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-3/4 h-3/4 relative opacity-[0.04]">
            <Image
              src="/noo-noo-logo.png"
              alt=""
              fill
              className="object-contain"
              aria-hidden="true"
            />
          </div>
        </div>
        
        <div className="relative h-full flex items-center justify-center">
          <div className="text-center">
            <div className="flex items-center justify-center w-16 h-16 mx-auto rounded-2xl bg-slate-800/50 border border-slate-700/50 mb-4">
              <svg className="w-8 h-8 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div className="text-sm text-slate-500">Waiting for data...</div>
            <div className="text-xs text-slate-600 mt-1">Start a test to see real-time graphs</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      {/* Watermark */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-0">
        <div className="w-3/4 h-3/4 relative opacity-[0.04]">
          <Image
            src="/noo-noo-logo.png"
            alt=""
            fill
            className="object-contain"
            aria-hidden="true"
          />
        </div>
      </div>
      
      {/* Chart */}
      <ResponsiveContainer width="100%" height="100%" className="relative z-10">
        <LineChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
        >
        <CartesianGrid strokeDasharray="3 3" stroke="#2a3140" opacity={0.5} />
        
        <XAxis
          dataKey="index"
          tick={{ fill: '#64748b', fontSize: 10 }}
          tickLine={{ stroke: '#2a3140' }}
          axisLine={{ stroke: '#2a3140' }}
          tickFormatter={(value) => {
            // Show time label every N ticks
            const d = chartData[value];
            if (d && value % 30 === 0) {
              return d.label;
            }
            return '';
          }}
        />
        
        {showVacuum && (
          <YAxis
            yAxisId="vacuum"
            domain={vacuumDomain}
            tick={{ fill: '#4fd1c5', fontSize: 11 }}
            tickLine={{ stroke: '#2a3140' }}
            axisLine={{ stroke: '#2a3140' }}
            label={{
              value: 'Vacuum (bar)',
              angle: -90,
              position: 'insideLeft',
              fill: '#4fd1c5',
              fontSize: 11,
            }}
          />
        )}
        
        {showForce && (
          <YAxis
            yAxisId="force"
            orientation="right"
            domain={forceDomain}
            tick={{ fill: '#3b82f6', fontSize: 11 }}
            tickLine={{ stroke: '#2a3140' }}
            axisLine={{ stroke: '#2a3140' }}
            label={{
              value: 'Force (kg)',
              angle: 90,
              position: 'insideRight',
              fill: '#3b82f6',
              fontSize: 11,
            }}
          />
        )}
        
        <Tooltip
          contentStyle={{
            backgroundColor: '#1a1f2a',
            border: '1px solid #2a3140',
            borderRadius: '12px',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
          }}
          labelStyle={{ color: '#64748b', fontSize: 11, marginBottom: 4 }}
          itemStyle={{ fontSize: 12 }}
          formatter={(value: number, name: string) => {
            const unit = name === 'Vacuum' ? ' bar' : ' kg';
            const color = name === 'Vacuum' ? '#4fd1c5' : '#3b82f6';
            return [<span key={name} style={{ color }}>{value.toFixed(3)}{unit}</span>, name];
          }}
          labelFormatter={(value) => {
            const d = chartData[value];
            return d ? d.label : '';
          }}
        />
        
        <Legend
          wrapperStyle={{ paddingTop: '10px' }}
          formatter={(value) => (
            <span style={{ color: '#94a3b8', fontSize: 12 }}>{value}</span>
          )}
        />
        
        {showVacuum && (
          <Line
            yAxisId="vacuum"
            type="monotone"
            dataKey="vacuum"
            name="Vacuum"
            stroke="#4fd1c5"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#4fd1c5', stroke: '#0f1218', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        )}
        
        {showForce && (
          <Line
            yAxisId="force"
            type="monotone"
            dataKey="force"
            name="Force"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#3b82f6', stroke: '#0f1218', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        )}
        
        {/* Target vacuum reference line */}
        {targetVacuum && showVacuum && (
          <ReferenceLine
            yAxisId="vacuum"
            y={Math.abs(targetVacuum)}
            stroke="#f59e0b"
            strokeDasharray="6 4"
            strokeWidth={1.5}
            label={{
              value: `Target: ${Math.abs(targetVacuum)} bar`,
              fill: '#f59e0b',
              fontSize: 10,
              position: 'insideTopRight',
            }}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
    </div>
  );
}

interface MiniChartProps {
  data: SensorData[];
  dataKey: 'vacuum_bar' | 'gross_weight_kg';
  color: string;
  height?: number;
}

export function MiniChart({ data, dataKey, color, height = 60 }: MiniChartProps) {
  const chartData = useMemo(() => {
    return data.slice(-60).map((d, index) => ({
      index,
      value: dataKey === 'vacuum_bar' ? Math.abs(d[dataKey] || 0) : (d[dataKey] || 0),
    }));
  }, [data, dataKey]);

  if (chartData.length < 2) {
    return (
      <div style={{ height }} className="flex items-center justify-center">
        <span className="text-slate-600 text-xs">No data</span>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
