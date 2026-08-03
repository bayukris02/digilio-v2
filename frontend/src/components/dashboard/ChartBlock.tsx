import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import type { DashboardBlock } from '../../api/dashboard';
import type { FieldConfig } from '../../api/models';

/** Peta value selection → label (dari config field backend, tanpa hardcode) */
function resolveLabel(field: FieldConfig | undefined, value: string): string {
  if (!field || !field.options) return value;
  const opt = field.options.find((o) => o.value === value);
  return opt?.label ?? value;
}

/** Format IDR untuk aggregate sum — deteksi dari field config */
function fmtAxisVal(val: number): string {
  if (Math.abs(val) >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}jt`;
  if (Math.abs(val) >= 1_000) return `${(val / 1_000).toFixed(0)}rb`;
  return String(val);
}

export default function ChartBlock({
  block,
  fields,
}: {
  block: DashboardBlock;
  fields?: Record<string, FieldConfig>;
}) {
  const rows = block.data.rows ?? [];
  const isMoney = block.aggregate?.func === 'sum';
  const height = block.height ?? 260;
  const groupField = fields?.[block.group_by ?? ''];

  const option = useMemo(() => {
    const labels = rows.map((r) =>
      typeof r.label === 'string' ? resolveLabel(groupField, r.label) : String(r.label ?? ''),
    );
    const values = rows.map((r) => Number(r.value ?? 0));

    const baseTooltip = {
      trigger: 'axis' as const,
      valueFormatter: (v: unknown) =>
        isMoney ? `Rp ${Number(v).toLocaleString('id-ID')}` : String(v),
    };

    switch (block.type) {
      case 'pie': {
        const colors = ((groupField as Record<string, unknown> | undefined)?.colors ?? {}) as Record<string, string>;
        const antdToHex: Record<string, string> = {
          default: '#8c8c8c', processing: '#1677ff', success: '#52c41a',
          error: '#ff4d4f', warning: '#faad14',
        };
        return {
          tooltip: {
            trigger: 'item',
            formatter: (p: { name: string; value: number }) =>
              `${p.name}: ${isMoney ? `Rp ${Number(p.value).toLocaleString('id-ID')}` : p.value}`,
          },
          legend: { type: 'scroll', bottom: 0, textStyle: { fontSize: 11 } },
          series: [
            {
              type: 'pie',
              radius: ['38%', '68%'],
              center: ['50%', '44%'],
              avoidLabelOverlap: true,
              itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 1 },
              label: { show: false },
              data: rows.map((r) => ({
                name: resolveLabel(groupField, String(r.label ?? '')),
                value: Number(r.value ?? 0),
                itemStyle: r.label ? { color: antdToHex[colors[String(r.label)] ?? ''] } : undefined,
              })),
            },
          ],
        };
      }
      case 'bar':
        return {
          tooltip: baseTooltip,
          grid: { left: 8, right: 12, top: 24, bottom: 28, containLabel: true },
          xAxis: { type: 'category', data: labels, axisLabel: { fontSize: 10, rotate: labels.length > 5 ? 30 : 0 } },
          yAxis: {
            type: 'value',
            axisLabel: { fontSize: 10, formatter: (v: number) => (isMoney ? fmtAxisVal(v) : String(v)) },
          },
          series: [
            {
              type: 'bar',
              data: values,
              barMaxWidth: 36,
              itemStyle: { color: '#1677ff', borderRadius: [4, 4, 0, 0] },
            },
          ],
        };
      case 'funnel':
        return {
          tooltip: baseTooltip,
          series: [
            {
              type: 'funnel',
              left: '8%', right: '8%', top: 12, bottom: 8,
              minSize: '20%',
              label: { show: true, position: 'inside', fontSize: 11, formatter: '{b}: {c}' },
              itemStyle: { borderColor: '#fff', borderWidth: 1 },
              data: rows.map((r, i) => ({
                name: String(r.label ?? ''),
                value: Number(r.value ?? 0),
                itemStyle: { color: ['#1677ff', '#69b1ff', '#91caff', '#bae0ff', '#e6f4ff'][i % 5] },
              })),
            },
          ],
        };
      case 'aging':
        return {
          tooltip: baseTooltip,
          grid: { left: 8, right: 12, top: 24, bottom: 28, containLabel: true },
          xAxis: { type: 'category', data: labels, axisLabel: { fontSize: 10 } },
          yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
          series: [
            {
              type: 'bar',
              data: values.map((v, i) => ({
                value: v,
                itemStyle: { color: i === 0 ? '#ff4d4f' : '#1677ff', borderRadius: [4, 4, 0, 0] },
              })),
              barMaxWidth: 40,
            },
          ],
        };
      case 'line':
      default:
        return {
          tooltip: baseTooltip,
          grid: { left: 8, right: 12, top: 28, bottom: 24, containLabel: true },
          xAxis: { type: 'category', data: labels, boundaryGap: false, axisLabel: { fontSize: 10 } },
          yAxis: {
            type: 'value',
            axisLabel: { fontSize: 10, formatter: (v: number) => (isMoney ? fmtAxisVal(v) : String(v)) },
          },
          series: [
            {
              type: 'line',
              data: values,
              smooth: true,
              symbol: 'circle',
              symbolSize: 5,
              lineStyle: { width: 2, color: '#1677ff' },
              itemStyle: { color: '#1677ff' },
              areaStyle: { color: 'rgba(22,119,255,0.08)' },
            },
          ],
        };
    }
  }, [rows, block, groupField, isMoney]);

  return <ReactECharts option={option} style={{ height }} notMerge lazyUpdate />;
}
