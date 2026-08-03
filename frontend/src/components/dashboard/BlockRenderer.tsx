import { Card, Col } from 'antd';
import type { DashboardBlock } from '../../api/dashboard';
import type { FieldConfig } from '../../api/models';
import KpiBlock from './KpiBlock';
import ChartBlock from './ChartBlock';
import GridBlock from './GridBlock';

/**
 * Generic block renderer — switch by block.type.
 * Semua tipe block (kpi/bar/pie/line/funnel/aging/grid/summary) dirender di sini,
 * tanpa tahu model spesifik apa pun.
 */
export default function BlockRenderer({
  block,
  fields,
  onNavigate,
}: {
  block: DashboardBlock;
  fields?: Record<string, FieldConfig>;
  onNavigate?: (modelName: string, recordId: number) => void;
}) {
  const span = block.span ?? 8;
  const dataError = block.data?.error;

  let inner: React.ReactNode;
  if (dataError) {
    inner = <div style={{ color: '#ff4d4f', fontSize: 12 }}>{dataError}</div>;
  } else if (block.type === 'kpi') {
    inner = <KpiBlock block={block} />;
  } else if (block.type === 'grid' || block.type === 'summary') {
    inner = <GridBlock block={block} fields={fields} onNavigate={onNavigate} />;
  } else {
    inner = <ChartBlock block={block} fields={fields} />;
  }

  return (
    <Col span={span}>
      <Card
        title={block.title}
        size="small"
        styles={{ header: { fontSize: 13, fontWeight: 600 }, body: { padding: 12 } }}
      >
        {inner}
      </Card>
    </Col>
  );
}
