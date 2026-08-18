import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Card, Input, Button, Typography, message, Descriptions, Tag } from 'antd'
import { StockOutlined } from '@ant-design/icons'
import http from '../../services/http'

const { Title, Text } = Typography

export default function StockPage() {
  const location = useLocation()
  const prefill = new URLSearchParams(location.search).get('text') || new URLSearchParams(location.search).get('topic') || ''
  const [symbol, setSymbol] = useState(prefill)
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [keyConfigured, setKeyConfigured] = useState<boolean | null>(null)

  useEffect(() => {
    http.get('/api/tools/keys-status').then((r: any) => {
      if (r.code === 0) setKeyConfigured(r.data?.stock_quote?.configured ?? false)
    }).catch(() => setKeyConfigured(false))
  }, [])

  const run = async (s?: string) => {
    const q = (s ?? symbol).trim()
    if (!q) { message.warning('请输入股票代码'); return }
    setLoading(true)
    try {
      const r: any = await http.post('/api/tools/stock', { symbol: q })
      if (r.code === 0) setResult(r.data.result)
      else { setResult(null); message.warning(r.msg) }
    } catch { message.error('请求失败') }
    finally { setLoading(false) }
  }

  useEffect(() => { if (prefill) run(prefill) }, []) // eslint-disable-line

  return (
    <div>
      <Title level={3}><StockOutlined style={{ color: '#ef4444' }} /> 股价查询 Stock Quote</Title>
      {keyConfigured === false && (
        <div style={{ marginTop: 8 }}>
          <Tag color="orange" style={{ borderRadius: 100 }}>⚠️ 未配置 STOCK_API_KEY</Tag>
          <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>在 AI 助手右上角 ⚙️ 记忆中心 → 设置 中配置</Text>
        </div>
      )}
      <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
        <Input value={symbol} onChange={e => setSymbol(e.target.value)} placeholder="股票代码，如 AAPL / TSLA"
          onKeyDown={e => { if (e.key === 'Enter') run() }} style={{ maxWidth: 260 }} />
        <Button type="primary" loading={loading} onClick={() => run()} style={{ borderRadius: 100 }}>查询</Button>
      </div>
      <div style={{ marginTop: 20 }}>
        {result && (
          <Card size="small" style={{ borderRadius: 16, maxWidth: 420, background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.2)' }}>
            <Descriptions column={1} size="small" items={Object.entries(result).map(([k, v]) => ({
              key: k, label: <Text type="secondary">{k}</Text>,
              children: <Text strong>{String(v)}</Text>,
            }))} />
          </Card>
        )}
      </div>
    </div>
  )
}
