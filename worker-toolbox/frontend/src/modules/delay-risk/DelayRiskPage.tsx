import { useState, useEffect } from 'react'
import { Card, Select, Button, Typography, message, Statistic, Row, Col, Alert, Tag, Space, Progress } from 'antd'
import { ClockCircleOutlined } from '@ant-design/icons'
import http from '../../services/http'

const { Title, Text } = Typography

const OPTIONS: Record<string, { label: string; options: { label: string; value: number }[] }> = {
  plan_progress: { label: '计划进度', options: [{ label: '落后', value: 0 }, { label: '正常', value: 1 }, { label: '超前', value: 2 }] },
  manpower_shortage: { label: '人手缺口', options: [{ label: '人手充足', value: 0 }, { label: '人手不足', value: 1 }] },
  req_change: { label: '需求变更', options: [{ label: '很少变更', value: 0 }, { label: '经常改需求', value: 1 }] },
  overtime_freq: { label: '加班频率', options: [{ label: '几乎不加班', value: 0 }, { label: '偶尔加班', value: 1 }, { label: '天天加班', value: 2 }] },
  depend_task: { label: '外部依赖', options: [{ label: '无外部依赖', value: 0 }, { label: '有外部依赖', value: 1 }] },
  urgent_boss: { label: '老板临时需求', options: [{ label: '没有', value: 0 }, { label: '有', value: 1 }] },
}

const RISK_COLOR: Record<string, string> = { high: 'red', medium: 'gold', low: 'green' }
const RISK_CN: Record<string, string> = { high: '高', medium: '中', low: '低' }

export default function DelayRiskPage() {
  const [info, setInfo] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [input, setInput] = useState<Record<string, number>>({})

  useEffect(() => {
    http.get('/api/tools/delay-risk/info').then((r: any) => {
      if (r.code === 0) setInfo(r.data)
      else setInfo({ error: r.msg })
    }).catch(() => setInfo({ error: '加载失败' }))
  }, [])

  const run = async () => {
    for (const k of Object.keys(OPTIONS)) {
      if (input[k] === undefined) { message.warning(`请选择 ${OPTIONS[k].label}`); return }
    }
    setLoading(true)
    try {
      const r: any = await http.post('/api/tools/delay-risk', input)
      if (r.code === 0) setResult(r.data)
      else message.warning(r.msg)
    } catch { message.error('请求失败') }
    finally { setLoading(false) }
  }

  const importances = info?.feature_importances || {}
  const maxImp = Math.max(...Object.values(importances).map(Number), 0.0001)

  return (
    <div>
      <Title level={3}><ClockCircleOutlined style={{ color: '#f97316' }} /> 项目延期风险检测 Delay Risk</Title>
      <Tag color="orange" style={{ borderRadius: 100 }}>ML 教学示例</Tag>
      <Text type="secondary" style={{ marginLeft: 8 }}>XGBoost 梯度提升树 · 6 特征 · 600 条合成数据</Text>

      {info?.error && <Alert type="error" style={{ marginTop: 16 }} showIcon message={info.error} />}

      {info && !info.error && (
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col xs={24} md={6}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="样本数" value={info.data_points} /></Card></Col>
          <Col xs={24} md={6}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="准确率" value={`${(info.metrics.accuracy * 100).toFixed(0)}%`} /></Card></Col>
        </Row>
      )}

      <Card size="small" title="选择项目现状" style={{ marginTop: 16, borderRadius: 12 }}>
        <Row gutter={12}>
          {Object.entries(OPTIONS).map(([k, cfg]) => (
            <Col xs={12} md={4} key={k}>
              <Text type="secondary" style={{ fontSize: 11 }}>{cfg.label}</Text>
              <Select value={input[k]} onChange={v => setInput(p => ({ ...p, [k]: v }))}
                options={cfg.options} style={{ width: '100%' }} placeholder="选择" />
            </Col>
          ))}
          <Col xs={24}>
            <Button type="primary" loading={loading} onClick={run} style={{ borderRadius: 100, marginTop: 12 }}>检测延期风险</Button>
          </Col>
        </Row>
      </Card>

      {result && (
        <Card size="small" style={{ marginTop: 16, borderRadius: 12, background: 'rgba(249,115,22,0.06)', border: '1px solid rgba(249,115,22,0.25)' }}>
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Text strong style={{ fontSize: 22 }}>{result.result}</Text>
            <div>
              {Object.entries(result.probabilities || {}).map(([k, v]) => (
                <Tag key={k} color={RISK_COLOR[k] || 'default'} style={{ borderRadius: 100 }}>
                  {RISK_CN[k] || k}: {(Number(v) * 100).toFixed(0)}%
                </Tag>
              ))}
            </div>
            <Text type="secondary" style={{ fontSize: 11 }}>{result.disclaimer}</Text>
          </Space>
        </Card>
      )}

      {info && !info.error && Object.keys(importances).length > 0 && (
        <Card size="small" title="📊 特征重要性（哪些因素最影响延期）" style={{ marginTop: 16, borderRadius: 12 }}>
          {Object.entries(importances).map(([k, v]: [string, any]) => (
            <div key={k} style={{ marginBottom: 6 }}>
              <Text style={{ fontSize: 12, width: 140, display: 'inline-block' }}>{OPTIONS[k]?.label || k}</Text>
              <Progress percent={Math.round((Number(v) / maxImp) * 100)} size="small" style={{ width: 220, margin: 0 }} />
              <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>{Number(v) * 100}%</Text>
            </div>
          ))}
        </Card>
      )}
    </div>
  )
}
