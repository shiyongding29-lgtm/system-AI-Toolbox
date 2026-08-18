import { useState, useEffect, useCallback } from 'react'
import { Drawer, Tabs, List, Button, Tag, Empty, message, Input, Table, Popconfirm, Typography } from 'antd'
import { DeleteOutlined, ClearOutlined, SettingOutlined, HistoryOutlined, DatabaseOutlined, KeyOutlined } from '@ant-design/icons'
import http from '../services/http'

const { Text } = Typography

interface Session { id: number; session_key: string; title: string; message_count: number; updated_at: string }
interface Entity { id: number; entity_type: string; entity_key: string; entity_value: string; source: string }
interface KeyStatus { [tool: string]: { configured: boolean; source: string | null; masked: string } }

export default function MemoryPanel({ open, onClose, onSelectSession }: {
  open: boolean
  onClose: () => void
  onSelectSession?: (sessionKey: string) => void
}) {
  const [sessions, setSessions] = useState<Session[]>([])
  const [entities, setEntities] = useState<Entity[]>([])
  const [keyStatus, setKeyStatus] = useState<KeyStatus>({})
  const [keyInput, setKeyInput] = useState<Record<string, string>>({})

  const load = useCallback(async () => {
    try { const r: any = await http.get('/api/agent/sessions'); if (r.code === 0) setSessions(r.data) } catch {}
    try { const r: any = await http.get('/api/agent/memory'); if (r.code === 0) setEntities(r.data) } catch {}
    try { const r: any = await http.get('/api/agent/settings'); if (r.code === 0) setKeyStatus(r.data) } catch {}
  }, [])

  useEffect(() => { if (open) load() }, [open, load])

  const deleteSession = async (id: number) => {
    await http.delete(`/api/agent/sessions/${id}`); message.success('已删除'); load()
  }
  const deleteEntity = async (id: number) => {
    await http.delete(`/api/agent/memory/${id}`); load()
  }
  const clearEntities = async () => {
    await http.post('/api/agent/memory/clear'); message.success('已清空'); load()
  }
  const saveKeys = async () => {
    const payload: Record<string, string> = {}
    Object.entries(keyInput).forEach(([k, v]) => { if (v.trim()) payload[`${k}_api_key`] = v.trim() })
    const r: any = await http.put('/api/agent/settings', payload)
    if (r.code === 0) { setKeyStatus(r.data); setKeyInput({}); message.success('已保存') }
  }

  const TYPE_LABELS: Record<string, string> = { owner: '负责人', language: '语言', style: '风格', fact: '事实' }

  const sessionsTab = (
    <List size="small" dataSource={sessions} locale={{ emptyText: <Empty description="暂无会话" /> }}
      renderItem={(s) => (
        <List.Item
          style={{ cursor: 'pointer', padding: '10px 8px' }}
          onClick={() => { onSelectSession?.(s.session_key); onClose() }}
          actions={[<Popconfirm key="d" title="删除会话?" onConfirm={(e) => { e?.stopPropagation(); deleteSession(s.id) }}><Button type="text" size="small" danger icon={<DeleteOutlined />} /></Popconfirm>]}
        >
          <List.Item.Meta
            title={<Text style={{ fontSize: 13 }} ellipsis>{s.title}</Text>}
            description={<span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>{s.message_count} 条消息 · {s.updated_at}</span>}
          />
        </List.Item>
      )}
    />
  )

  const memoryTab = (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
        <Button size="small" icon={<ClearOutlined />} onClick={clearEntities}>清空记忆</Button>
      </div>
      <Table size="small" rowKey="id" dataSource={entities} pagination={false} locale={{ emptyText: <Empty description="暂无实体记忆（说「记住：常用负责人是张三」即可添加）" /> }}
        columns={[
          { title: '类型', dataIndex: 'entity_type', width: 70, render: (t: string) => <Tag style={{ fontSize: 10, borderRadius: 100 }}>{TYPE_LABELS[t] || t}</Tag> },
          { title: '键', dataIndex: 'entity_key', ellipsis: true },
          { title: '值', dataIndex: 'entity_value', ellipsis: true },
          { title: '来源', dataIndex: 'source', width: 56, render: (s: string) => <Text style={{ fontSize: 10 }} type="secondary">{s}</Text> },
          { title: '', width: 40, render: (_, r: Entity) => <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={() => deleteEntity(r.id)} /> },
        ]}
      />
    </div>
  )

  const settingsTab = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Text type="secondary" style={{ fontSize: 12 }}>外部数据工具 API Key（天气/汇率有免费通道，可不配置；股价需 key）</Text>
      {Object.entries(keyStatus).map(([tool, s]) => (
        <div key={tool} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <KeyOutlined style={{ color: s.configured ? '#10b981' : 'rgba(255,255,255,0.3)' }} />
          <span style={{ width: 110, fontSize: 12, color: '#c8d6e5' }}>{tool}</span>
          {s.configured
            ? <Tag color="green" style={{ fontSize: 10, borderRadius: 100 }}>已配置 {s.masked}（{s.source}）</Tag>
            : <Tag style={{ fontSize: 10, borderRadius: 100 }}>未配置</Tag>}
          <Input size="small" placeholder="输入 key 覆盖" style={{ width: 150, fontSize: 11 }}
            onChange={(e) => setKeyInput(prev => ({ ...prev, [tool]: e.target.value }))} />
        </div>
      ))}
      <Button size="small" type="primary" onClick={saveKeys} style={{ alignSelf: 'flex-end', borderRadius: 100 }}>保存</Button>
    </div>
  )

  return (
    <Drawer open={open} onClose={onClose} title="🧠 Agent 记忆中心" width={440}
      styles={{ header: { borderBottom: '1px solid rgba(255,255,255,0.06)' }, body: { padding: '12px 16px' } }}>
      <Tabs size="small" defaultActiveKey="sessions" items={[
        { key: 'sessions', label: <span><HistoryOutlined /> 历史会话</span>, children: sessionsTab },
        { key: 'memory', label: <span><DatabaseOutlined /> 实体记忆</span>, children: memoryTab },
        { key: 'settings', label: <span><SettingOutlined /> 设置</span>, children: settingsTab },
      ]} />
    </Drawer>
  )
}
