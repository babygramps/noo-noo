'use client';

import { useMemo } from 'react';
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
      force: d.gross_weight_kg || 0,
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
      <div className="h-full flex items-center justify-center text-gray-500">
        <div className="text-center">
          <div className="text-4xl mb-2">📊</div>
          <div>Waiting for data...</div>
        </div>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart
        data={chartData}
        margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#363b44" />
        
        <XAxis
          dataKey="index"
          tick={{ fill: '#8b949e', fontSize: 10 }}
          tickLine={{ stroke: '#363b44' }}
          axisLine={{ stroke: '#363b44' }}
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
            tick={{ fill: '#58a6ff', fontSize: 11 }}
            tickLine={{ stroke: '#363b44' }}
            axisLine={{ stroke: '#363b44' }}
            label={{
              value: 'Vacuum (bar)',
              angle: -90,
              position: 'insideLeft',
              fill: '#58a6ff',
              fontSize: 11,
            }}
          />
        )}
        
        {showForce && (
          <YAxis
            yAxisId="force"
            orientation="right"
            domain={forceDomain}
            tick={{ fill: '#3fb950', fontSize: 11 }}
            tickLine={{ stroke: '#363b44' }}
            axisLine={{ stroke: '#363b44' }}
            label={{
              value: 'Force (kg)',
              angle: 90,
              position: 'insideRight',
              fill: '#3fb950',
              fontSize: 11,
            }}
          />
        )}
        
        <Tooltip
          contentStyle={{
            backgroundColor: '#23272f',
            border: '1px solid #363b44',
            borderRadius: '8px',
          }}
          labelStyle={{ color: '#8b949e' }}
          formatter={(value: number, name: string) => {
            const unit = name === 'Vacuum' ? ' bar' : ' kg';
            return [value.toFixed(3) + unit, name];
          }}
          labelFormatter={(value) => {
            const d = chartData[value];
            return d ? d.label : '';
          }}
        />
        
        <Legend
          wrapperStyle={{ paddingTop: '10px' }}
          formatter={(value) => (
            <span style={{ color: '#8b949e' }}>{value}</span>
          )}
        />
        
        {showVacuum && (
          <Line
            yAxisId="vacuum"
            type="monotone"
            dataKey="vacuum"
            name="Vacuum"
            stroke="#58a6ff"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#58a6ff' }}
            isAnimationActive={false}
          />
        )}
        
        {showForce && (
          <Line
            yAxisId="force"
            type="monotone"
            dataKey="force"
            name="Force"
            stroke="#3fb950"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#3fb950' }}
            isAnimationActive={false}
          />
        )}
        
        {/* Target vacuum reference line */}
        {targetVacuum && showVacuum && (
          <ReferenceLine
            yAxisId="vacuum"
            y={Math.abs(targetVacuum)}
            stroke="#d29922"
            strokeDasharray="5 5"
            label={{
              value: `Target: ${Math.abs(targetVacuum)} bar`,
              fill: '#d29922',
              fontSize: 10,
              position: 'insideTopRight',
            }}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
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
        <span className="text-gray-600 text-xs">No data</span>
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


