import { Typography, Tag } from 'antd'
import { EyeOutlined, BulbOutlined, ThunderboltOutlined, SearchOutlined, SendOutlined } from '@ant-design/icons'

const { Text } = Typography

export interface AgentStep {
  phase: 'perceive' | 'plan' | 'act' | 'reflect' | 'output'
  label: string
  status: 'done' | 'running' | 'error' | 'pending'
  detail?: string
}

const PHASE_META: Record<string, { icon: React.ReactNode; label: string }> = {
  perceive: { icon: <EyeOutlined />, label: '感知' },
  plan: { icon: <BulbOutlined />, label: '规划' },
  act: { icon: <ThunderboltOutlined />, label: '执行' },
  reflect: { icon: <SearchOutlined />, label: '反思' },
  output: { icon: <SendOutlined />, label: '输出' },
}

export default function AgentStepsTimeline({ steps }: { steps: AgentStep[] }) {
  if (!steps || steps.length === 0) return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '8px 0 2px' }}>
      {steps.map((s, i) => {
        const meta = PHASE_META[s.phase] || { icon: '•', label: s.phase }
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: 11 }}>
            <span style={{
              width: 18, height: 18, borderRadius: 9, flexShrink: 0, marginTop: 1,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: s.status === 'error' ? 'rgba(255,77,106,0.15)' : s.status === 'running' ? 'rgba(0,229,255,0.15)' : 'rgba(255,255,255,0.06)',
              color: s.status === 'error' ? '#ff4d6a' : s.status === 'running' ? '#00e5ff' : 'rgba(255,255,255,0.5)',
              animation: s.status === 'running' ? 'glowPulse 1s infinite' : undefined,
            }}>
              {meta.icon}
            </span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <span style={{ color: 'rgba(255,255,255,0.35)', marginRight: 6 }}>{meta.label}</span>
              <Text style={{ color: s.status === 'error' ? '#ff8fa3' : 'rgba(200,214,229,0.85)', fontSize: 11 }} ellipsis={{ tooltip: s.detail }}>
                {s.label}
              </Text>
              {s.status === 'error' && s.detail && (
                <div style={{ color: '#ff4d6a', fontSize: 10, marginTop: 2, wordBreak: 'break-all' }}>{s.detail}</div>
              )}
              {s.status === 'running' && <Tag style={{ marginLeft: 6, fontSize: 9, lineHeight: '14px', borderRadius: 100, padding: '0 6px', color: '#00e5ff', background: 'rgba(0,229,255,0.08)', border: 'none' }}>进行中</Tag>}
            </div>
          </div>
        )
      })}
    </div>
  )
}
