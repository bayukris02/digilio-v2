import { useEffect, useState } from 'react';
import { Modal, Spin, Card, Row, Col, Tag, Space, Button, Result } from 'antd';
import { ArrowRightOutlined } from '@ant-design/icons';
import type { ModelConfig } from '../api/models';
import { modelApi } from '../api/models';
import { formatDate } from '../utils/format';

interface QuickViewProps {
  visible: boolean;
  modelName: string;
  recordId: number;
  onClose: () => void;
  onOpenFullForm?: () => void;
}

/**
 * Read-only detail modal for related records (Many2One external link).
 * Generic — works with any model. Zero config per model.
 */
export default function QuickViewModal({
  visible, modelName, recordId, onClose, onOpenFullForm,
}: QuickViewProps) {
  const [config, setConfig] = useState<ModelConfig | null>(null);
  const [record, setRecord] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!visible || !modelName || !recordId) return;

    setLoading(true);
    setError(null);
    setConfig(null);
    setRecord(null);

    Promise.all([
      modelApi.getConfig(modelName),
      modelApi.getRecord(modelName, recordId),
    ])
      .then(([cfg, rec]) => {
        setConfig(cfg);
        setRecord(rec);
      })
      .catch((err) => {
        setError(err?.response?.data?.error || err?.message || 'Failed to load record');
      })
      .finally(() => setLoading(false));
  }, [visible, modelName, recordId]);

  /** Show a single field value as read-only display */
  function renderValue(key: string, field: ModelConfig['fields'][string], value: unknown): React.ReactNode {
    if (value === null || value === undefined) return <span style={{ color: '#bbb' }}>—</span>;

    switch (field.type) {
      case 'boolean':
        return value ? <Tag color="green">Yes</Tag> : <Tag color="red">No</Tag>;

      case 'date':
        return <span>{formatDate(String(value))}</span>;

      case 'selection': {
        const colors = (field as Record<string, unknown>).colors as Record<string, string> | undefined;
        const opt = (field.options as { value: string; label: string }[] || []).find(
          (o) => o.value === value,
        );
        const label = opt?.label || String(value);
        const color = colors?.[String(value)];
        return color ? <Tag color={color}>{label}</Tag> : <span style={{ fontWeight: 500 }}>{label}</span>;
      }

      case 'monetary':
      case 'float': {
        const num = Number(value);
        if (isNaN(num)) return <span>{String(value)}</span>;
        return <span>Rp {num.toLocaleString('id-ID')}</span>;
      }

      case 'many2one': {
        // Show the display name if value is {id, name} object, otherwise raw
        if (typeof value === 'object' && value !== null) {
          return <span>{(value as Record<string, unknown>).name as string || `#${(value as Record<string, unknown>).id}`}</span>;
        }
        return <span>#{value}</span>;
      }

      case 'integer': {
        const intVal = Number(value);
        return <span>{isNaN(intVal) ? String(value) : intVal.toLocaleString('id-ID')}</span>;
      }

      default:
        return <span>{String(value)}</span>;
    }
  }

  /** Fields to display — exclude one2many + audit/base fields */
  function getDisplayFields(): [string, ModelConfig['fields'][string]][] {
    if (!config?.fields) return [];
    const skipKeys = new Set(['id', 'created_at', 'updated_at', 'created_by', 'is_deleted']);
    return Object.entries(config.fields).filter(([key, field]) => {
      if (skipKeys.has(key)) return false;
      if (field.type === 'one2many') return false;
      return true;
    });
  }

  const displayFields = getDisplayFields();
  const recordLabel = record?.name as string || record?.reference as string || `#${recordId}`;

  return (
    <Modal
      title={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <span>
            {config?.verbose_name || modelName}
            {' — '}
            {recordLabel}
          </span>
          {onOpenFullForm && (
            <Button
              size="small"
              type="text"
              icon={<ArrowRightOutlined />}
              onClick={onOpenFullForm}
            >
              Open
            </Button>
          )}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={520}
      destroyOnClose
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 32 }}>
          <Spin />
        </div>
      ) : error ? (
        <Result
          status="error"
          title="Failed to load record"
          subTitle={error}
        />
      ) : (
        <Card
          size="small"
          styles={{
            body: { padding: 0 },
          }}
        >
          {displayFields.map(([key, field]) => (
            <Row
              key={key}
              style={{
                padding: '6px 12px',
                borderBottom: '1px solid #f0f0f0',
                alignItems: 'flex-start',
              }}
            >
              <Col
                span={8}
                style={{
                  fontSize: 11,
                  color: '#888',
                  paddingTop: 2,
                }}
              >
                {field.label}
              </Col>
              <Col span={16} style={{ fontSize: 12 }}>
                {renderValue(key, field, record?.[key])}
              </Col>
            </Row>
          ))}
          {displayFields.length === 0 && (
            <div style={{ padding: 16, color: '#999', textAlign: 'center' }}>
              No fields to display.
            </div>
          )}
        </Card>
      )}
    </Modal>
  );
}
