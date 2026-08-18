import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Card, Input, Button, Typography, message, Descriptions, Spin } from 'antd'
import { CloudOutlined } from '@ant-design/icons'
import http from '../../services/http'

const { Title, Text } = Typography

export default function WeatherPage() {
  const location = useLocation()
  const prefill = new URLSearchParams(location.search).get('text') || new URLSearchParams(location.search).get('topic') || ''
  const [city, setCity] = useState(prefill)
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const run = async (c?: string) => {
    const q = (c ?? city).trim()
    if (!q) { message.warning('请输入城市名'); return }
    setLoading(true)
    try {
      const r: any = await http.post('/api/tools/weather', { city: q })
      if (r.code === 0) setResult(r.data.result)
      else { setResult(null); message.warning(r.msg) }
    } catch { message.error('请求失败') }
    finally { setLoading(false) }
  }

  useEffect(() => { if (prefill) run(prefill) }, []) // eslint-disable-line

  return (
    <div>
      <Title level={3}><CloudOutlined style={{ color: '#06b6d4' }} /> 天气查询 Weather</Title>
      <Text type="secondary">数据源 open-meteo · 免费无需 API key</Text>
      <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
        <Input value={city} onChange={e => setCity(e.target.value)} placeholder="城市名，如：北京 / Shanghai / Tokyo"
          onKeyDown={e => { if (e.key === 'Enter') run() }} style={{ maxWidth: 320 }} />
        <Button type="primary" loading={loading} onClick={() => run()} style={{ borderRadius: 100 }}>查询</Button>
      </div>
      <div style={{ marginTop: 20 }}>
        {loading && <Spin />}
        {result && (
          <Card size="small" style={{ borderRadius: 16, maxWidth: 480, background: 'linear-gradient(135deg, rgba(6,182,212,0.08), rgba(59,130,246,0.04))', border: '1px solid rgba(6,182,212,0.25)' }}>
            <Descriptions column={1} size="small" items={Object.entries(result).map(([k, v]) => ({
              key: k, label: <Text type="secondary">{k}</Text>,
              children: <Text strong style={{ fontSize: k === '温度' ? 20 : 14 }}>{String(v)}</Text>,
            }))} />
          </Card>
        )}
      </div>
    </div>
  )
}
