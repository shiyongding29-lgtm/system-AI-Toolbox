import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Card, Input, Button, Typography, Tabs, message, Tag, Alert } from 'antd'
import { CalculatorOutlined, CalendarOutlined, SwapOutlined, OrderedListOutlined, CodeOutlined } from '@ant-design/icons'
import http from '../../services/http'

const { Text, Title } = Typography

function usePrefill(keys: string[]): string {
  const location = useLocation()
  const params = new URLSearchParams(location.search)
  for (const k of keys) {
    const v = params.get(k)
    if (v) return v
  }
  return ''
}

function ToolBlock({ endpoint, placeholder, title, prefill, render }: {
  endpoint: string; placeholder: string; title: string; prefill: string
  render: (d: any) => React.ReactNode
}) {
  const [input, setInput] = useState(prefill)
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = async (text?: string) => {
    const t = (text ?? input).trim()
    if (!t) { message.warning('请输入内容'); return }
    setLoading(true); setError(''); setResult(null)
    try {
      const r: any = await http.post(endpoint, { text: t })
      if (r.code === 0) setResult(r.data)
      else setError(r.msg || '执行失败')
    } catch { setError('请求失败') }
    finally { setLoading(false) }
  }

  useEffect(() => { if (prefill) run(prefill) }, []) // eslint-disable-line

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Text type="secondary" style={{ fontSize: 13 }}>{title}</Text>
      <Input.TextArea value={input} onChange={e => setInput(e.target.value)} placeholder={placeholder}
        autoSize={{ minRows: 2, maxRows: 6 }} style={{ fontSize: 13, fontFamily: 'SF Mono, monospace' }} />
      <Button type="primary" loading={loading} onClick={() => run()} style={{ borderRadius: 100, alignSelf: 'flex-start' }}>
        执行 実行
      </Button>
      {error && <Alert type="error" showIcon message={error} />}
      {result && (
        <Card size="small" style={{ borderRadius: 12, background: 'rgba(16,185,129,0.04)', border: '1px solid rgba(16,185,129,0.2)' }}>
          {render(result)}
        </Card>
      )}
    </div>
  )
}

export default function CodeToolsPage() {
  const prefill = usePrefill(['text', 'topic'])
  return (
    <div>
      <Title level={3}>🔧 智能小工具 Smart Tools</Title>
      <Text type="secondary">零 LLM 成本 · 纯代码实现 · 也可直接对 AI 助手说「帮我算 (8+2)*5/2」</Text>
      <div style={{ marginTop: 20 }}>
        <Tabs defaultActiveKey="calculator" items={[
          {
            key: 'calculator',
            label: <span><CalculatorOutlined /> 计算器</span>,
            children: <ToolBlock endpoint="/api/tools/calculator" prefill={prefill} placeholder="输入表达式，如 (8+2)*5/2、2**10"
              title="支持四则运算、幂、括号。非法表达式会被安全拒绝。"
              render={(d) => <Text strong style={{ fontSize: 20, fontFamily: 'SF Mono, monospace' }}>{String(d.result)}</Text>} />,
          },
          {
            key: 'date',
            label: <span><CalendarOutlined /> 日期计算</span>,
            children: <ToolBlock endpoint="/api/tools/date-calc" prefill={prefill} placeholder="如：下周五是几号、30天后、3个月后"
              title="支持：今天/明天/后天/下周X/N天后/N周后/N月后"
              render={(d) => <Text strong style={{ fontSize: 18 }}>{String(d.result)}</Text>} />,
          },
          {
            key: 'unit',
            label: <span><SwapOutlined /> 单位换算</span>,
            children: <ToolBlock endpoint="/api/tools/unit-convert" prefill={prefill} placeholder="如：5公里等于多少英里、100华氏度转摄氏度"
              title="支持长度/重量/温度/数据量（米、千克、磅、MB、摄氏度...）"
              render={(d) => <Text strong style={{ fontSize: 18 }}>{String(d.result)}</Text>} />,
          },
          {
            key: 'words',
            label: <span><OrderedListOutlined /> 字数统计</span>,
            children: <ToolBlock endpoint="/api/tools/word-count" prefill={prefill} placeholder="粘贴文本统计字数（中英混合）"
              title="中文字符 + 英文单词 + 总字符数"
              render={(d) => (
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                  {Object.entries(d.result || {}).map(([k, v]) => (
                    <div key={k}><Text type="secondary" style={{ fontSize: 12 }}>{k}</Text>
                      <div><Text strong style={{ fontSize: 18 }}>{String(v)}</Text></div></div>
                  ))}
                </div>
              )} />,
          },
          {
            key: 'json',
            label: <span><CodeOutlined /> JSON格式化</span>,
            children: <ToolBlock endpoint="/api/tools/json-format" prefill={prefill} placeholder='粘贴 JSON，如 {"a":1,"b":[2,3]}'
              title="格式化或校验 JSON 文本"
              render={(d) => <pre style={{ margin: 0, fontSize: 12, fontFamily: 'SF Mono, monospace', color: '#10b981', whiteSpace: 'pre-wrap' }}>{String(d.result)}</pre>} />,
          },
        ]} />
      </div>
      <div style={{ marginTop: 16 }}>
        <Tag style={{ borderRadius: 100 }}>🧮 计算器</Tag>
        <Tag style={{ borderRadius: 100 }}>📅 日期</Tag>
        <Tag style={{ borderRadius: 100 }}>⚖️ 换算</Tag>
        <Tag style={{ borderRadius: 100 }}>🔢 字数</Tag>
        <Tag style={{ borderRadius: 100 }}>🧾 JSON</Tag>
        <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>这些工具已接入工作流编排器，可被 Agent 自动组合</Text>
      </div>
    </div>
  )
}
