import { useState, useEffect } from 'react'
import { Card, Input, Button, Typography, message, Statistic, Row, Col, Descriptions, Alert, Tag, Space } from 'antd'
import { ExperimentOutlined } from '@ant-design/icons'
import http from '../../services/http'

const { Title, Text } = Typography

const FEATURE_LABELS: Record<string, { label: string; placeholder: string }> = {
  mass: { label: '质量 mass (克)', placeholder: '如 192' },
  width: { label: '宽度 width (厘米)', placeholder: '如 8.4' },
  height: { label: '高度 height (厘米)', placeholder: '如 7.3' },
  color_score: { label: '颜色分数 color_score (0~1)', placeholder: '如 0.55' },
}

export default function FruitClassifierPage() {
  const [info, setInfo] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [input, setInput] = useState<Record<string, string>>({})

  useEffect(() => {
    http.get('/api/tools/fruit-classify/info').then((r: any) => {
      if (r.code === 0) setInfo(r.data)
      else setInfo({ error: r.msg })
    }).catch(() => setInfo({ error: '加载失败' }))
  }, [])

  const run = async () => {
    const feats: Record<string, number> = {}
    for (const k of ['mass', 'width', 'height', 'color_score']) {
      const v = input[k]?.trim()
      if (!v) { message.warning(`请填写 ${FEATURE_LABELS[k].label}`); return }
      feats[k] = parseFloat(v)
    }
    setLoading(true)
    try {
      const r: any = await http.post('/api/tools/fruit-classify', feats)
      if (r.code === 0) setResult(r.data)
      else message.warning(r.msg)
    } catch { message.error('请求失败') }
    finally { setLoading(false) }
  }

  return (
    <div>
      <Title level={3}><ExperimentOutlined style={{ color: '#22c55e' }} /> 水果识别 Fruit Classifier</Title>
      <Tag color="green" style={{ borderRadius: 100 }}>ML 教学示例</Tag>
      <Text type="secondary" style={{ marginLeft: 8 }}>K-NN 最近邻分类 · 59 样本 · 4 类水果</Text>

      {info?.error && <Alert type="error" style={{ marginTop: 16 }} showIcon message={info.error} />}

      {info && !info.error && (
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col xs={24} md={6}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="样本数" value={info.data_points} /></Card></Col>
          <Col xs={24} md={6}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="准确率" value={`${(info.metrics.accuracy * 100).toFixed(0)}%`} /></Card></Col>
          <Col xs={24} md={6}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="K 值" value={info.k} /></Card></Col>
          <Col xs={24} md={6}>
            <Card size="small" style={{ borderRadius: 12 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>类别</Text>
              <div style={{ fontSize: 13 }}>{info.labels?.join(' / ')}</div>
            </Card>
          </Col>
        </Row>
      )}

      <Card size="small" title="输入水果的测量值" style={{ marginTop: 16, borderRadius: 12 }}>
        <Row gutter={12}>
          {['mass', 'width', 'height', 'color_score'].map(k => (
            <Col xs={12} md={5} key={k}>
              <Text type="secondary" style={{ fontSize: 11 }}>{FEATURE_LABELS[k].label}</Text>
              <Input size="small" placeholder={FEATURE_LABELS[k].placeholder} value={input[k] || ''}
                onChange={e => setInput(p => ({ ...p, [k]: e.target.value }))} />
            </Col>
          ))}
          <Col xs={24} md={4}>
            <Button type="primary" loading={loading} onClick={run} style={{ borderRadius: 100, marginTop: 20 }}>识别</Button>
          </Col>
        </Row>
        <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 12 }}>
          参考：苹果 192g/8.4/7.3/0.55 · 蜜柑 86g/6.2/4.7/0.80 · 柠檬 150g/6.5/8.5/0.72（高瘦） · 橙子 200g/8.0/8.0/0.75
        </Text>
      </Card>

      {result && (
        <Card size="small" style={{ marginTop: 16, borderRadius: 12, background: 'rgba(34,197,94,0.06)', border: '1px solid rgba(34,197,94,0.25)' }}>
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Text strong style={{ fontSize: 20 }}>{result.result}</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>平均邻居距离：{result.avg_neighbor_distance}（越小越确定）</Text>
            <div style={{ marginTop: 4 }}>
              {Object.entries(result.probabilities || {}).map(([k, v]) => (
                <Tag key={k} color={v === result.confidence ? 'green' : 'default'} style={{ borderRadius: 100 }}>{k}: {(Number(v) * 100).toFixed(0)}%</Tag>
              ))}
            </div>
            <Text type="secondary" style={{ fontSize: 11 }}>{result.disclaimer}</Text>
          </Space>
        </Card>
      )}
    </div>
  )
}
