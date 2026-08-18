import { useState, useEffect } from 'react'
import { Card, InputNumber, Button, Typography, message, Statistic, Row, Col, Alert, Tag, Space, Progress } from 'antd'
import { RadarChartOutlined } from '@ant-design/icons'
import http from '../../services/http'

const { Title, Text } = Typography

const FIELDS: Record<string, { label: string; min: number; max: number; step: number; placeholder: string }> = {
  performance: { label: '绩效评分(1~5)', min: 1, max: 5, step: 0.1, placeholder: '如 4.8' },
  overtime_hours: { label: '月加班时长(小时)', min: 0, max: 100, step: 1, placeholder: '如 2' },
  tenure: { label: '工龄(年)', min: 0, max: 40, step: 0.5, placeholder: '如 5' },
  monthly_salary: { label: '月薪资(元)', min: 0, max: 100000, step: 500, placeholder: '如 15000' },
}

export default function AnomalyDetectorPage() {
  const [info, setInfo] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [viz, setViz] = useState<any>(null)
  const [input, setInput] = useState<Record<string, number | null>>({})

  useEffect(() => {
    http.get('/api/tools/anomaly-detect/info').then((r: any) => {
      if (r.code === 0) setInfo(r.data)
      else setInfo({ error: r.msg })
    }).catch(() => setInfo({ error: '加载失败' }))
  }, [])

  const run = async () => {
    for (const k of Object.keys(FIELDS)) {
      if (input[k] === null || input[k] === undefined) { message.warning(`请填写 ${FIELDS[k].label}`); return }
    }
    setLoading(true)
    try {
      const r: any = await http.post('/api/tools/anomaly-detect/viz', input)
      if (r.code === 0) {
        setResult(r.data.prediction)
        setViz({ image_url: r.data.image_url, explained_variance: r.data.explained_variance })
      } else message.warning(r.msg)
    } catch { message.error('请求失败') }
    finally { setLoading(false) }
  }

  const m = info?.metrics || {}

  return (
    <div>
      <Title level={3}><RadarChartOutlined style={{ color: '#f59e0b' }} /> 异常员工识别 Anomaly Detection</Title>
      <Tag color="orange" style={{ borderRadius: 100 }}>ML 教学示例 · 无监督学习</Tag>
      <Text type="secondary" style={{ marginLeft: 8 }}>K-Means 聚类 · PCA 降维可视化 · 离群检测 · 525 条合成数据</Text>

      {info?.error && <Alert type="error" style={{ marginTop: 16 }} showIcon message={info.error} />}

      {info && !info.error && (
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col xs={12} md={4}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="样本数" value={m.data_points} /></Card></Col>
          <Col xs={12} md={4}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="注入异常" value={m.anomalies_injected} /></Card></Col>
          <Col xs={12} md={4}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="捕获异常" value={m.anomalies_caught} /></Card></Col>
          <Col xs={12} md={4}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="误报" value={m.false_positives} /></Card></Col>
        </Row>
      )}

      <Alert type="info" showIcon style={{ marginTop: 16 }}
        message="原理：聚类后，到最近簇中心距离仍很大的样本 = 行为模式异常（如「绩效很高但加班极低」），标出来交 HR 复核。" />

      <Card size="small" title="输入员工行为特征" style={{ marginTop: 16, borderRadius: 12 }}>
        <Row gutter={12}>
          {Object.entries(FIELDS).map(([k, cfg]) => (
            <Col xs={12} md={6} key={k}>
              <Text type="secondary" style={{ fontSize: 11 }}>{cfg.label}</Text>
              <InputNumber value={input[k] ?? null} onChange={v => setInput(p => ({ ...p, [k]: v }))}
                min={cfg.min} max={cfg.max} step={cfg.step} placeholder={cfg.placeholder} style={{ width: '100%' }} />
            </Col>
          ))}
          <Col xs={24}>
            <Button type="primary" loading={loading} onClick={run} style={{ borderRadius: 100, marginTop: 12 }}>检测异常</Button>
          </Col>
        </Row>
      </Card>

      {result && (
        <Card size="small" style={{ marginTop: 16, borderRadius: 12, background: result.is_anomalous ? 'rgba(245,158,11,0.08)' : 'rgba(34,197,94,0.06)', border: `1px solid ${result.is_anomalous ? 'rgba(245,158,11,0.3)' : 'rgba(34,197,94,0.3)'}` }}>
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Text strong style={{ fontSize: 18 }}>{result.result}</Text>
            <div style={{ maxWidth: 360 }}>
              <Progress percent={Math.round(Math.min(result.anomaly_score, 2) / 2 * 100)}
                status={result.is_anomalous ? 'exception' : 'success'}
                format={() => `异常分数 ${result.anomaly_score.toFixed(2)}（阈值 1.0）`} />
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              到最近簇中心距离：{result.distance}（阈值 {result.threshold}）· 第 {result.cluster + 1} 类员工
            </Text>
            {result.is_anomalous && <Tag color="orange" style={{ borderRadius: 100 }}>⚠️ 建议 HR 复核</Tag>}
            <Text type="secondary" style={{ fontSize: 11 }}>{result.disclaimer}</Text>
          </Space>
        </Card>
      )}

      {viz?.image_url && (
        <Card size="small" title="📊 聚类可视化（PCA 降维到 2 维）" style={{ marginTop: 16, borderRadius: 12 }}>
          <img src={viz.image_url} alt="聚类散点图" style={{ width: '100%', borderRadius: 8 }} />
          <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 6 }}>
            橙色五角星 = 当前员工 · 红叉 = 训练集异常 · 蓝/绿/紫点 = 三个正常员工簇
            {viz.explained_variance?.length === 2 && `（主成分 1+2 解释 ${((viz.explained_variance[0] + viz.explained_variance[1]) * 100).toFixed(0)}% 方差）`}
          </Text>
        </Card>
      )}
    </div>
  )
}
