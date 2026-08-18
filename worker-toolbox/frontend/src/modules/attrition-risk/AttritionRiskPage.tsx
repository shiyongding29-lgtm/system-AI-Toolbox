import { useState, useEffect } from 'react'
import { Card, InputNumber, Select, Button, Typography, message, Statistic, Row, Col, Alert, Space, Progress } from 'antd'
import { TeamOutlined } from '@ant-design/icons'
import http from '../../services/http'

const { Title, Text } = Typography

const FIELDS: Record<string, { label: string; min: number; max: number; step: number; placeholder: string }> = {
  tenure: { label: '工龄(年)', min: 0, max: 40, step: 0.5, placeholder: '如 3' },
  salary: { label: '月薪资(元)', min: 0, max: 100000, step: 500, placeholder: '如 15000' },
  raise_pct: { label: '最近加薪幅度(%)', min: 0, max: 30, step: 0.5, placeholder: '如 4.5' },
  performance: { label: '绩效评分(1~5)', min: 1, max: 5, step: 0.1, placeholder: '如 3.5' },
  overtime_hours: { label: '月加班时长(小时)', min: 0, max: 100, step: 1, placeholder: '如 20' },
  months_since_promotion: { label: '距上次晋升(月)', min: 0, max: 120, step: 1, placeholder: '从未晋升填 120' },
  age: { label: '年龄', min: 20, max: 60, step: 1, placeholder: '如 30' },
  attendance_anomalies: { label: '考勤异常次数', min: 0, max: 20, step: 1, placeholder: '如 2' },
}

const DEPARTMENTS = ['技术部', '销售部', '市场部', '财务部', '人事部', '运营部']

export default function AttritionRiskPage() {
  const [info, setInfo] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [input, setInput] = useState<Record<string, number | null>>({})
  const [department, setDepartment] = useState<string>('')

  useEffect(() => {
    http.get('/api/tools/attrition-risk/info').then((r: any) => {
      if (r.code === 0) setInfo(r.data)
      else setInfo({ error: r.msg })
    }).catch(() => setInfo({ error: '加载失败' }))
  }, [])

  const run = async () => {
    for (const k of Object.keys(FIELDS)) {
      if (input[k] === null || input[k] === undefined) { message.warning(`请填写 ${FIELDS[k].label}`); return }
    }
    if (!department) { message.warning('请选择部门'); return }
    setLoading(true)
    try {
      const r: any = await http.post('/api/tools/attrition-risk', { ...input, department })
      if (r.code === 0) setResult(r.data)
      else message.warning(r.msg)
    } catch { message.error('请求失败') }
    finally { setLoading(false) }
  }

  const m = info?.metrics || {}

  return (
    <div>
      <Title level={3}><TeamOutlined style={{ color: '#14b8a6' }} /> 员工离职风险预测 Attrition Risk</Title>
      <Text type="secondary" style={{ marginLeft: 8 }}>FCN 全连接网络 · Sigmoid 输出离职概率 · 9 特征</Text>

      {info?.error && <Alert type="error" style={{ marginTop: 16 }} showIcon message={info.error} />}

      {info && !info.error && (
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col xs={12} md={4}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="训练数据" value={info.data_points} suffix="条" /></Card></Col>
          <Col xs={12} md={4}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="AUC" value={`${(m.auc * 100).toFixed(1)}%`} /></Card></Col>
          <Col xs={12} md={4}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="精确率" value={`${(m.precision * 100).toFixed(1)}%`} /></Card></Col>
          <Col xs={12} md={4}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="召回率" value={`${(m.recall * 100).toFixed(1)}%`} /></Card></Col>
          <Col xs={12} md={4}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="F1" value={m.f1} /></Card></Col>
        </Row>
      )}

      <Card size="small" title="输入员工特征" style={{ marginTop: 16, borderRadius: 12 }}>
        <Row gutter={12}>
          {Object.entries(FIELDS).map(([k, cfg]) => (
            <Col xs={12} md={8} lg={6} key={k}>
              <Text type="secondary" style={{ fontSize: 11 }}>{cfg.label}</Text>
              <InputNumber value={input[k] ?? null} onChange={v => setInput(p => ({ ...p, [k]: v }))}
                min={cfg.min} max={cfg.max} step={cfg.step} placeholder={cfg.placeholder} style={{ width: '100%' }} />
            </Col>
          ))}
          <Col xs={12} md={8} lg={6}>
            <Text type="secondary" style={{ fontSize: 11 }}>部门</Text>
            <Select value={department || undefined} onChange={setDepartment}
              options={DEPARTMENTS.map(d => ({ label: d, value: d }))}
              style={{ width: '100%' }} placeholder="选择部门" />
          </Col>
          <Col xs={24}>
            <Button type="primary" loading={loading} onClick={run} style={{ borderRadius: 100, marginTop: 12 }}>预测离职风险</Button>
          </Col>
        </Row>
      </Card>

      {result && (
        <Card size="small" style={{ marginTop: 16, borderRadius: 12, background: 'rgba(20,184,166,0.06)', border: '1px solid rgba(20,184,166,0.25)' }}>
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Text strong style={{ fontSize: 22 }}>{result.result}</Text>
            <div style={{ maxWidth: 360 }}>
              <Progress percent={Math.round(result.attrition_probability * 100)}
                status={result.risk_level === '高' ? 'exception' : result.risk_level === '中' ? 'normal' : 'success'}
                format={p => `离职概率 ${p}%`} />
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>留任概率 {(result.stay_probability * 100).toFixed(1)}%</Text>
            <Text type="secondary" style={{ fontSize: 11 }}>{result.disclaimer}</Text>
          </Space>
        </Card>
      )}
    </div>
  )
}
