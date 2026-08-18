import { useState, useEffect } from 'react'
import { Card, Input, Button, Typography, message, Statistic, Row, Col, Descriptions, Alert, Tag } from 'antd'
import { LineChartOutlined } from '@ant-design/icons'
import http from '../../services/http'

const { Title, Text } = Typography

export default function StockPredictPage() {
  const [info, setInfo] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [input, setInput] = useState<Record<string, string>>({})

  useEffect(() => {
    http.get('/api/tools/stock-predict/info').then((r: any) => {
      if (r.code === 0) setInfo(r.data)
      else setInfo({ error: r.msg })
    }).catch(() => setInfo({ error: '加载失败' }))
  }, [])

  const run = async () => {
    setLoading(true)
    try {
      const feats: Record<string, number> = {}
      Object.entries(input).forEach(([k, v]) => { if (v && v.trim()) feats[k] = parseFloat(v) })
      const r: any = await http.post('/api/tools/stock-predict', feats)
      if (r.code === 0) setResult(r.data)
      else message.warning(r.msg)
    } catch { message.error('请求失败') }
    finally { setLoading(false) }
  }

  const metrics = info?.metrics || {}

  return (
    <div>
      <Title level={3}><LineChartOutlined style={{ color: '#f97316' }} /> 股票预测 Stock Predictor</Title>
      <Tag color="orange" style={{ borderRadius: 100 }}>ML 教学示例</Tag>
      <Text type="secondary" style={{ marginLeft: 8 }}>sklearn 线性回归(收盘价) + 逻辑回归(涨跌方向)</Text>

      {info?.error && <Alert type="error" style={{ marginTop: 16 }} showIcon message={info.error} />}

      {info && !info.error && (
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col xs={24} md={6}>
            <Card size="small" style={{ borderRadius: 12 }}><Statistic title="数据点" value={info.data_points} suffix="天" /></Card>
          </Col>
          <Col xs={24} md={6}>
            <Card size="small" style={{ borderRadius: 12 }}><Statistic title="收盘价 MAE" value={`$${metrics.mae}`} /></Card>
          </Col>
          <Col xs={24} md={6}>
            <Card size="small" style={{ borderRadius: 12 }}><Statistic title="收盘价 R²" value={metrics.r2} /></Card>
          </Col>
          <Col xs={24} md={6}>
            <Card size="small" style={{ borderRadius: 12 }}><Statistic title="方向准确率" value={`${(metrics.direction_accuracy * 100).toFixed(1)}%`} /></Card>
          </Col>
        </Row>
      )}

      <Alert type="warning" showIcon style={{ marginTop: 16 }}
        message="⚠️ 教学示例：线性/逻辑回归无法可靠预测股市，方向准确率约 40%（不如抛硬币），结果仅供参考，不构成投资建议。" />

      <Card size="small" title="输入今日行情（留空则用最新一天预测「明天」）" style={{ marginTop: 16, borderRadius: 12 }}>
        <Row gutter={12}>
          {['open', 'high', 'low', 'close', 'volume'].map(k => (
            <Col xs={12} md={4} key={k}>
              <Text type="secondary" style={{ fontSize: 11 }}>{k}</Text>
              <Input size="small" placeholder={k === 'volume' ? '成交量' : '价格'} value={input[k] || ''}
                onChange={e => setInput(p => ({ ...p, [k]: e.target.value }))} />
            </Col>
          ))}
          <Col xs={24} md={4}>
            <Button type="primary" loading={loading} onClick={run} style={{ borderRadius: 100, marginTop: 20 }}>预测</Button>
          </Col>
        </Row>
      </Card>

      {result && (
        <Card size="small" style={{ marginTop: 16, borderRadius: 12, background: 'linear-gradient(135deg, rgba(249,115,22,0.08), rgba(239,68,68,0.04))', border: '1px solid rgba(249,115,22,0.25)' }}>
          <Descriptions column={2} size="small" items={[
            { key: 'close', label: '预测次日收盘价', children: <Text strong style={{ fontSize: 18, color: '#f97316' }}>${result.predicted_close}</Text> },
            { key: 'dir', label: '涨跌方向', children: <Text strong>{result.direction}（上涨概率 {(result.up_probability * 100).toFixed(1)}%）</Text> },
            { key: 'last', label: '最新收盘价', children: `$${result.last_close}` },
          ]} />
          <Text type="secondary" style={{ fontSize: 11 }}>{result.disclaimer}</Text>
        </Card>
      )}
    </div>
  )
}
