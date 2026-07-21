import { useEffect, useState } from 'react';
import { Card, Typography, Checkbox, Tag, Space, Spin, Empty, Button, Popover } from 'antd';
import { ClockCircleOutlined, SettingOutlined } from '@ant-design/icons';
import { modelApi, type FieldConfig } from '../api/models';

const { Text } = Typography;

interface ChatterLogEntry {
  id: number;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  created_by_name: string | null;
  created_at: string;
}

interface ChatterProps {
  modelName: string;
  recordId: number;
  fields: Record<string, FieldConfig>;
}

/** Format ISO timestamp to relative time string */
function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

/** Format ISO timestamp to date + time string */
function formatDateTime(iso: string): string {
  const d = new Date(iso);
  const date = d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
  const time = d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
  return `${date} ${time}`;
}

export default function Chatter({ modelName, recordId, fields }: ChatterProps) {
  const [logs, setLogs] = useState<ChatterLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [popoverOpen, setPopoverOpen] = useState(false);

  // Visibility state: default from field config, overridable via localStorage
  const storageKey = `chatter.${modelName}`;
  const defaultVisibility: Record<string, boolean> = {};
  Object.entries(fields).forEach(([key, f]) => {
    defaultVisibility[key] = f.chatter_show !== false; // default true
  });

  const [visibility, setVisibility] = useState<Record<string, boolean>>(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      return saved ? { ...defaultVisibility, ...JSON.parse(saved) } : defaultVisibility;
    } catch {
      return defaultVisibility;
    }
  });

  // Fetch logs when record changes
  useEffect(() => {
    if (!recordId) return;
    setLoading(true);
    modelApi.getChatterLogs(modelName, recordId)
      .then(setLogs)
      .catch(() => setLogs([]))
      .finally(() => setLoading(false));
  }, [modelName, recordId]);

  // Toggle field visibility + persist to localStorage
  const toggleField = (fieldName: string) => {
    setVisibility((prev) => {
      const next = { ...prev, [fieldName]: !prev[fieldName] };
      localStorage.setItem(storageKey, JSON.stringify(next));
      return next;
    });
  };

  // Get field label
  const fieldLabel = (name: string): string => {
    return fields[name]?.label || name;
  };

  // Count visible logs
  const visibleLogs = logs.filter((log) => visibility[log.field_name] !== false);

  // Filter fields for the popover (skip one2many, id, audit)
  const filterableFields = Object.keys(fields).filter(
    k => fields[k].type !== 'one2many' && k !== 'id' && k !== 'is_deleted'
  );

  // Build popover content
  const popoverContent = (
    <div style={{ minWidth: 180 }}>
      <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
        Show/Hide Fields
      </Text>
      {filterableFields.map((fieldName) => (
        <div key={fieldName} style={{ padding: '2px 0' }}>
          <Checkbox
            checked={visibility[fieldName] !== false}
            onChange={() => toggleField(fieldName)}
            style={{ fontSize: 12 }}
          >
            {fieldLabel(fieldName)}
          </Checkbox>
        </div>
      ))}
    </div>
  );

  const hiddenCount = filterableFields.filter(k => visibility[k] === false).length;

  return (
    <Card
      title={
        <Space size={6}>
          <ClockCircleOutlined style={{ fontSize: 13, color: '#666' }} />
          <span>Activity Log</span>
        </Space>
      }
      size="small"
      styles={{
        header: {
          borderBottom: '1px solid #e8e8e8',
          padding: '8px 12px',
          minHeight: 40,
        },
        body: { padding: 12, maxHeight: 400, overflowY: 'auto' },
      }}
      extra={
        filterableFields.length > 0 && (
          <Popover
            content={popoverContent}
            trigger="click"
            open={popoverOpen}
            onOpenChange={setPopoverOpen}
            placement="bottomRight"
          >
            <Button
              type="text"
              size="small"
              icon={<SettingOutlined />}
              style={{ color: hiddenCount > 0 ? '#1677ff' : '#999' }}
            />
          </Popover>
        )
      }
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 20 }}><Spin size="small" /></div>
      ) : logs.length === 0 ? (
        <Empty description="No activity yet" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <>
          {/* Log entries */}
          {visibleLogs.length === 0 ? (
            <Text type="secondary" style={{ fontSize: 12 }}>
              All fields hidden. Click ⚙️ to show changes.
            </Text>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {visibleLogs.map((log) => (
                <div key={log.id} style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 8,
                  padding: '5px 0',
                  borderBottom: '1px solid #f0f0f0',
                }}>
                  <ClockCircleOutlined style={{ fontSize: 12, color: '#999', marginTop: 4 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    {/* Row 1: username + field tag + relative time */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 1 }}>
                      <Text strong style={{ fontSize: 11, color: '#333' }}>
                        {log.created_by_name || 'System'}
                      </Text>
                      <Tag color="default" style={{ fontSize: 10, lineHeight: '16px', margin: 0 }}>
                        {fieldLabel(log.field_name)}
                      </Tag>
                    </div>
                    {/* Row 2: old → new value */}
                    <div style={{ fontSize: 12, lineHeight: 1.4, wordBreak: 'break-word', paddingLeft: 0 }}>
                      {log.old_value != null ? (
                        <span>
                          <Text delete style={{ fontSize: 12, color: '#999' }}>
                            {log.old_value}
                          </Text>
                          {' → '}
                        </span>
                      ) : null}
                      <Text style={{ fontSize: 12 }}>
                        {log.new_value || <span style={{ color: '#999' }}>(empty)</span>}
                      </Text>
                    </div>
                    {/* Row 3: exact timestamp */}
                    <div style={{ marginTop: 1 }}>
                      <Text type="secondary" style={{ fontSize: 10 }}>
                        {formatDateTime(log.created_at)} ({timeAgo(log.created_at)})
                      </Text>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </Card>
  );
}
