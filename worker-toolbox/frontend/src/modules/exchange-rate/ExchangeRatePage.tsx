import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Card, Button, Typography, message, Select, Statistic } from 'antd'
import { DollarOutlined } from '@ant-design/icons'
import http from '../../services/http'

const { Title, Text } = Typography

const CURRENCIES = [
  { value: 'USD', label: 'USD 美元' }, { value: 'CNY', label: 'CNY 人民币' },
  { value: 'EUR', label: 'EUR 欧元' }, { value: 'JPY', label: 'JPY 日元' },
  { value: 'GBP', label: 'GBP 英镑' }, { value: 'HKD', label: 'HKD 港币' },
  { value: 'KRW', label: 'KRW 韩元' }, { value: 'AUD', label: 'AUD 澳元' },
  { value: 'CAD', label: 'CAD 加元' }, { value: 'SGD', label: 'SGD 新加坡元' },
]

export default function ExchangeRatePage() {
  const location = useLocation()
  const prefill = new URLSearchParams(location.search).get('text') || new URLSearchParams(location.search).get('topic') || ''
  const [base, setBase] = useState('USD')
  const [target, setTarget] = useState('CNY')
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // 从预填文本提取货币对
    const m = prefill.match(/([A-Za-z]{3})\s*(?:兑|換|换|转|to|→|->|对)\s*([A-Za-z]{3})/i)
    if (m) { setBase(m[1].toUpperCase()); setTarget(m[2].toUpperCase()) }
  }, [prefill])

  const run = async () => {
    setLoading(true)
    try {
      const r: any = await http.post('/api/tools/exchange-rate', { base, target })
      if (r.code === 0) setResult(r.data.result)
      else { setResult(null); message.warning(r.msg) }
    } catch { message.error('请求失败') }
    finally { setLoading(false) }
  }

  useEffect(() => {
    const m = prefill.match(/([A-Za-z]{3})\s*(?:兑|換|换|转|to|→|->|对)\s*([A-Za-z]{3})/i)
    if (m) run()
  }, []) // eslint-disable-line

  return (
    <div>
      <Title level={3}><DollarOutlined style={{ color: '#14b8a6' }} /> 汇率查询 Exchange Rate</Title>
      <Text type="secondary">数据源 open.er-api.com · 免费无需 API key</Text>
      <div style={{ display: 'flex', gap: 12, marginTop: 20, alignItems: 'center', flexWrap: 'wrap' }}>
        <Select value={base} onChange={setBase} options={CURRENCIES} style={{ width: 170 }} />
        <Text>→</Text>
        <Select value={target} onChange={setTarget} options={CURRENCIES} style={{ width: 170 }} />
        <Button type="primary" loading={loading} onClick={run} style={{ borderRadius: 100 }}>查询</Button>
      </div>
      <div style={{ marginTop: 24 }}>
        {result && (
          <Card size="small" style={{ borderRadius: 16, maxWidth: 420, background: 'rgba(20,184,166,0.06)', border: '1px solid rgba(20,184,166,0.25)' }}>
            <Statistic title={`1 ${result.from} =`} value={result.rate} suffix={result.to} valueStyle={{ color: '#14b8a6', fontWeight: 700 }} />
            <Text type="secondary" style={{ fontSize: 12 }}>{result['说明']}</Text>
          </Card>
        )}
      </div>
    </div>
  )
}
