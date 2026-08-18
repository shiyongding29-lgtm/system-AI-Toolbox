import { useState, useEffect } from 'react'
import { Card, Input, Button, Typography, message, Statistic, Row, Col, Alert, Tag, Space } from 'antd'
import { StopOutlined } from '@ant-design/icons'
import http from '../../services/http'

const { Title, Text } = Typography

export default function SpamClassifierPage() {
  const [info, setInfo] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [text, setText] = useState('')

  useEffect(() => {
    http.get('/api/tools/spam-classify/info').then((r: any) => {
      if (r.code === 0) setInfo(r.data)
      else setInfo({ error: r.msg })
    }).catch(() => setInfo({ error: '加载失败' }))
  }, [])

  const run = async () => {
    if (!text.trim()) { message.warning('请输入要判断的文本'); return }
    setLoading(true)
    try {
      const r: any = await http.post('/api/tools/spam-classify', { text })
      if (r.code === 0) setResult(r.data)
      else message.warning(r.msg)
    } catch { message.error('请求失败') }
    finally { setLoading(false) }
  }

  const m = info?.metrics || {}
  const isSpam = result?.label === 'spam'

  return (
    <div>
      <Title level={3}><StopOutlined style={{ color: '#ef4444' }} /> 垃圾邮件检测 Spam Detector</Title>
      <Tag color="red" style={{ borderRadius: 100 }}>ML 教学示例</Tag>
      <Text type="secondary" style={{ marginLeft: 8 }}>随机森林 · 关键词 + 长度等 34 个特征 · 5571 条短信</Text>

      {info?.error && <Alert type="error" style={{ marginTop: 16 }} showIcon message={info.error} />}

      {info && !info.error && (
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col xs={24} md={6}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="准确率" value={`${(m.accuracy * 100).toFixed(1)}%`} /></Card></Col>
          <Col xs={24} md={6}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="精确率" value={`${(m.precision * 100).toFixed(1)}%`} /></Card></Col>
          <Col xs={24} md={6}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="召回率" value={`${(m.recall * 100).toFixed(1)}%`} /></Card></Col>
          <Col xs={24} md={6}><Card size="small" style={{ borderRadius: 12 }}><Statistic title="F1" value={`${(m.f1 * 100).toFixed(1)}%`} /></Card></Col>
        </Row>
      )}

      <Card size="small" title="粘贴邮件/短信内容" style={{ marginTop: 16, borderRadius: 12 }}>
        <Input.TextArea value={text} onChange={e => setText(e.target.value)} autoSize={{ minRows: 4, maxRows: 10 }}
          placeholder={'如：Free entry in 2 a wkly comp to win FA Cup final tkts, text FA to 87121...'} />
        <Button type="primary" loading={loading} onClick={run} style={{ borderRadius: 100, marginTop: 12 }}>检测</Button>
      </Card>

      {result && (
        <Card size="small" style={{ marginTop: 16, borderRadius: 12, background: isSpam ? 'rgba(239,68,68,0.06)' : 'rgba(34,197,94,0.06)', border: `1px solid ${isSpam ? 'rgba(239,68,68,0.3)' : 'rgba(34,197,94,0.3)'}` }}>
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Text strong style={{ fontSize: 20 }}>{result.result}</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              垃圾概率 {(result.spam_probability * 100).toFixed(1)}%（阈值 50%）
            </Text>
            {result.keywords_hit?.length > 0 && (
              <div style={{ marginTop: 4 }}>
                <Text type="secondary" style={{ fontSize: 12, marginRight: 6 }}>命中关键词：</Text>
                {result.keywords_hit.map((k: string) => <Tag key={k} color="red" style={{ borderRadius: 100 }}>{k}</Tag>)}
              </div>
            )}
            <Text type="secondary" style={{ fontSize: 11 }}>{result.disclaimer}</Text>
          </Space>
        </Card>
      )}
    </div>
  )
}
