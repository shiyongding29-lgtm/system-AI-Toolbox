import { useState, useEffect } from 'react'
import { Card, Select, Button, Typography, message, Statistic, Row, Col, Alert, Tag, Space, Collapse } from 'antd'
import { AimOutlined } from '@ant-design/icons'
import http from '../../services/http'

const { Title, Text } = Typography

const OPTIONS: Record<string, { label: string; options: { label: string; value: number }[] }> = {
  deadline: { label: '截止日期', options: [{ label: '宽松', value: 0 }, { label: '正常', value: 1 }, { label: '紧急', value: 2 }] },
  impact: { label: '影响范围', options: [{ label: '低', value: 0 }, { label: '中', value: 1 }, { label: '高', value: 2 }] },
  leader_followup: { label: '领导跟进', options: [{ label: '否', value: 0 }, { label: '是', value: 1 }] },
  workload: { label: '工作量', options: [{ label: '小', value: 0 }, { label: '中', value: 1 }, { label: '大', value: 2 }] },
}

const PRIORITY_COLOR: Record<string, string> = { high: 'red', medium: 'gold', low: 'green' }

export default function PriorityClassifierPage() {
  const [info, setInfo] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [input, setInput] = useState<Record<string, number>>({})

  useEffect(() => {
    http.get('/api/tools/priority-classify/info').then((r: any) => {
      if (r.code === 0) setInfo(r.data)
      else setInfo({ error: r.msg })
    }).catch(() => setInfo({ error: '加载失败' }))
  }, [])

  const run = async () => {
    for (const k of ['deadline', 'impact', 'leader_followup', 'workload']) {
      if (input[k] === undefined) { message.warning(`请选择 ${OPTIONS[k].label}`); return }
    }
    setLoading(true)
    try {
      const r: any = await http.post('/api/tools/priority-classify', input)
      if (r.code === 0) setResult(r.data)
      else message.warning(r.msg)
    } catch { message.error('请求失败') }
    finally { setLoading(false) }
  }

  return (
    <div>
      <Title level={3}><AimOutlined style={{ color: '#8b5cf6' }} /> 任务优先级判断 Task Priority</Title>
      <Tag color="purple" style={{ borderRadius: 100 }}>ML 教学示例</Tag>
      <Text type="secondary" style={{ marginLeft: 8 }}>决策树 · 可解释 if-then 规则 · 500 条合成数据</Text>

      {info?.error && <Alert type="error" style={{ marginTop: 16 }} showIcon message={info.error} />}

      {info && !info.error && (
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col xs={24} md={6}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="样本数" value={info.data_points} /></Card></Col>
          <Col xs={24} md={6}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="准确率" value={`${(info.metrics.accuracy * 100).toFixed(0)}%`} /></Card></Col>
        </Row>
      )}

      <Card size="small" title="选择任务特征" style={{ marginTop: 16, borderRadius: 12 }}>
        <Row gutter={12}>
          {Object.entries(OPTIONS).map(([k, cfg]) => (
            <Col xs={12} md={5} key={k}>
              <Text type="secondary" style={{ fontSize: 11 }}>{cfg.label}</Text>
              <Select value={input[k]} onChange={v => setInput(p => ({ ...p, [k]: v }))}
                options={cfg.options} style={{ width: '100%' }} placeholder="选择" size="middle" />
            </Col>
          ))}
          <Col xs={24} md={4}>
            <Button type="primary" loading={loading} onClick={run} style={{ borderRadius: 100, marginTop: 20 }}>判断优先级</Button>
          </Col>
        </Row>
      </Card>

      {result && (
        <Card size="small" style={{ marginTop: 16, borderRadius: 12, background: 'rgba(139,92,246,0.06)', border: '1px solid rgba(139,92,246,0.25)' }}>
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Text strong style={{ fontSize: 22 }}>{result.result}</Text>
            <div>
              {Object.entries(result.probabilities || {}).map(([k, v]) => (
                <Tag key={k} color={PRIORITY_COLOR[k] || 'default'} style={{ borderRadius: 100 }}>
                  {k}: {(Number(v) * 100).toFixed(0)}%
                </Tag>
              ))}
            </div>
            <Text type="secondary" style={{ fontSize: 11 }}>{result.disclaimer}</Text>
          </Space>
        </Card>
      )}

      {info?.tree_rules && (
        <Card size="small" title="🧠 学到的决策规则（可解释性）" style={{ marginTop: 16, borderRadius: 12 }}>
          <Collapse ghost size="small" items={[{
            key: 'rules', label: '展开查看 if-then 规则树',
            children: <pre style={{ fontSize: 11, lineHeight: 1.6, whiteSpace: 'pre-wrap', color: '#c8d6e5' }}>{info.tree_rules}</pre>,
          }]} />
        </Card>
      )}
    </div>
  )
}
