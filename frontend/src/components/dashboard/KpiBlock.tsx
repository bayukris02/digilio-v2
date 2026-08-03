import { Card, Statistic } from 'antd';
import ReactECharts from 'echarts-for-react';
import type { DashboardBlock } from '../../api/dashboard';

function fmtValue(block: DashboardBlock, value: number): string {
  const func = block.aggregate?.func ?? 'count';
  if (func === 'sum' || func === 'avg') {
    return `Rp ${Number(value).toLocaleString('id-ID', { maximumFractionDigits: 0 })}`;
  }
  return Number(value).toLocaleString('id-ID');
}

/** Sparkline mini-chart (ECharts, tanpa axis — hanya garis tipis) */
function Sparkline({ series }: { series: { label: string; value: number }[] }) {
  const option = {
    grid: { left: 2, right: 2, top: 6, bottom: 2 },
    xAxis: { type: 'category', show: false, data: series.map((s) => s.label) },
    yAxis: { type: 'value', show: false },
    series: [
      {
        type: 'line',
        data: series.map((s) => s.value),
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#1677ff' },
        areaStyle: { color: 'rgba(22,119,255,0.08)' },
      },
    ],
    tooltip: { trigger: 'axis' },
  };
  return <ReactECharts option={option} style={{ height: 44 }} notMerge lazyUpdate />;
}

export default function KpiBlock({ block }: { block: DashboardBlock }) {
  const value = block.data.value ?? 0;
  const series = block.data.series ?? [];
  return (
    <Card size="small" styles={{ body: { padding: '14px 16px' } }}>
      <Statistic
        title={block.title}
        value={fmtValue(block, value)}
        valueStyle={{ fontSize: 20, fontWeight: 600 }}
      />
      {series.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <Sparkline series={series} />
        </div>
      )}
    </Card>
  );
}
