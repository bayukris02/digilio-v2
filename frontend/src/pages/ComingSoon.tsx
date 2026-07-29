import { Typography, Card } from 'antd';
import { ToolOutlined } from '@ant-design/icons';

export default function ComingSoon() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
      <Card style={{ textAlign: 'center', padding: '40px 60px', borderRadius: 12 }}>
        <ToolOutlined style={{ fontSize: 48, color: '#faad14' }} />
        <Typography.Title level={3} style={{ marginTop: 16, marginBottom: 4 }}>
          Coming Soon
        </Typography.Title>
        <Typography.Text type="secondary">
          Halaman ini sedang dalam pengembangan
        </Typography.Text>
      </Card>
    </div>
  );
}
