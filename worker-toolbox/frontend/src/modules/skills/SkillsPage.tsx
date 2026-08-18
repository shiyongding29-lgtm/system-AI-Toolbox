import { useState, useEffect, useCallback, useRef } from 'react'
import { Card, Row, Col, Typography, Tag, Button, Drawer, Tabs, Steps, Input, message, Spin, Empty, Popconfirm, Badge } from 'antd'
import { PlusOutlined, DeleteOutlined, ThunderboltOutlined, AudioOutlined } from '@ant-design/icons'
import http from '../../services/http'
import SkillCreateModal from './SkillCreateModal'

const { Title, Text } = Typography

interface SkillSummary {
  id: string; name: string; description: string; icon: string; color: string
  builtin: boolean; aliases: string[]; input_hint: string; node_labels: string[]; type?: string
}
interface SkillDetail extends SkillSummary { prompt: string; plan: { nodes: any[]; edges: any[]; input?: string } }
interface WfNode { id: string; tool: string; label: string; status: string; error?: string }
interface WfStatus { status: string; nodes: WfNode[]; results: Record<string, any> }

export default function SkillsPage() {
  const [skills, setSkills] = useState<SkillSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [active, setActive] = useState<SkillDetail | null>(null)
  const [createOpen, setCreateOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r: any = await http.get('/api/skills')
      if (r.code === 0) setSkills(r.data)
    } catch { message.error('加载技能失败') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const openDetail = async (id: string) => {
    try {
      const r: any = await http.get(`/api/skills/${id}`)
      if (r.code === 0) setActive(r.data)
      else message.warning(r.msg)
    } catch { message.error('加载技能详情失败') }
  }

  const deleteSkill = async (id: string) => {
    const r: any = await http.delete(`/api/skills/${id}`)
    if (r.code === 0) { message.success('已删除'); load() }
    else message.warning(r.msg)
  }

  return (
    <div>
      <Title level={3}>🎯 Skills 技能库</Title>
      <Text type="secondary">技能 = 方法论 + 默认流程。对 AI 助手说「帮我做一份周报」或「会议纪要：…」即可自动命中技能执行。</Text>

      <Row gutter={[16, 16]} style={{ marginTop: 20 }}>
        <Col xs={24} sm={12} lg={8} xl={6}>
          <div onClick={() => setCreateOpen(true)} style={{
            height: '100%', minHeight: 200, borderRadius: 16, cursor: 'pointer',
            border: '1.5px dashed rgba(0,229,255,0.3)', background: 'rgba(0,229,255,0.03)',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10,
          }}>
            <PlusOutlined style={{ fontSize: 28, color: '#00e5ff' }} />
            <Text style={{ color: '#00e5ff', fontSize: 13 }}>新建技能</Text>
            <Text type="secondary" style={{ fontSize: 11 }}>描述 + 方法论 + 工具流程</Text>
          </div>
        </Col>
        {skills.map(s => (
          <Col key={s.id} xs={24} sm={12} lg={8} xl={6}>
            <Card hoverable size="small" onClick={() => openDetail(s.id)}
              style={{ borderRadius: 16, height: '100%', minHeight: 200, border: `1px solid ${s.color}30`, background: `linear-gradient(160deg, ${s.color}0d, rgba(255,255,255,0.01))` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                <div style={{ width: 40, height: 40, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', background: `${s.color}20`, fontSize: 20 }}>{s.icon}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Text strong style={{ fontSize: 15, display: 'block' }} ellipsis>{s.name}</Text>
                  <div>
                    {s.builtin && <Tag color="cyan" style={{ fontSize: 9, borderRadius: 100, marginRight: 4 }}>内置</Tag>}
                    {s.type === 'knowledge' && <Tag color="purple" style={{ fontSize: 9, borderRadius: 100, marginRight: 4 }}>知识型</Tag>}
                    <Text type="secondary" style={{ fontSize: 10 }}>{s.id}</Text>
                  </div>
                </div>
              </div>
              <Text style={{ fontSize: 12, color: '#8899bb', display: 'block', minHeight: 40 }} ellipsis={{ tooltip: s.description }}>{s.description}</Text>
              <div style={{ marginTop: 8 }}>
                {s.node_labels.length > 0 ? (
                  <Steps size="small" progressDot current={-1} items={s.node_labels.map(l => ({ title: l }))}
                    style={{ fontSize: 10 }} />
                ) : (
                  <Text type="secondary" style={{ fontSize: 11 }}>💡 知识型 · 无固定流程，AI 自定工具</Text>
                )}
              </div>
            </Card>
          </Col>
        ))}
      </Row>
      {!loading && skills.length === 0 && <Empty style={{ marginTop: 40 }} description="暂无技能" />}
      {loading && <Spin style={{ marginTop: 40, display: 'block' }} />}

      {active && (
        <Drawer open width={520} onClose={() => setActive(null)}
          title={<span>{active.icon} {active.name} <Tag style={{ fontSize: 10, borderRadius: 100 }} color={active.builtin ? 'cyan' : 'green'}>{active.builtin ? '内置' : '自建'}</Tag></span>}
          extra={!active.builtin && (
            <Popconfirm title="删除技能?" onConfirm={() => { deleteSkill(active.id); setActive(null) }}>
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
          styles={{ header: { borderBottom: '1px solid rgba(255,255,255,0.06)' } }}>
          <Tabs size="small" items={[
            {
              key: 'method', label: '📖 方法',
              children: <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, lineHeight: 1.8, color: '#c8d6e5', background: 'rgba(0,0,0,0.2)', padding: 14, borderRadius: 10, maxHeight: '60vh', overflow: 'auto' }}>{active.prompt || '（无方法论，直接执行流程）'}</pre>,
            },
            ...(active.plan.nodes.length > 0 ? [
              {
                key: 'plan', label: '🔀 流程',
                children: (
                  <div>
                    <Steps direction="vertical" size="small" current={-1}
                      items={active.plan.nodes.map(n => ({ title: n.label, description: <Text type="secondary" style={{ fontSize: 11 }}>{n.tool}</Text> }))} />
                    <Text type="secondary" style={{ fontSize: 11 }}>输入提示：{active.input_hint}</Text>
                  </div>
                ),
              },
              {
                key: 'run', label: '⚡ 执行',
                children: <SkillRunPanel skill={active} />,
              },
            ] : [
              {
                key: 'howto', label: '💡 用法',
                children: (
                  <div>
                    <Text style={{ fontSize: 13, lineHeight: 1.8, display: 'block' }}>
                      这是<b>知识型技能</b>：只有方法论、没有固定流程。命中后 AI 会把方法论注入决策，自行选择合适的工具来完成任务。
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 8 }}>
                      使用方式：对 AI 助手说「用{active.name}的方法帮我……」，或直接提需求，AI 自动识别并应用。
                    </Text>
                  </div>
                ),
              },
            ]),
          ]} />
        </Drawer>
      )}

      <SkillCreateModal open={createOpen} onClose={() => setCreateOpen(false)} onCreated={() => { setCreateOpen(false); load() }} />
    </div>
  )
}

// ── 执行面板 ──

function SkillRunPanel({ skill }: { skill: SkillDetail }) {
  const [text, setText] = useState('')
  const [running, setRunning] = useState(false)
  const [recording, setRecording] = useState(false)
  const [wf, setWf] = useState<WfStatus | null>(null)
  const timerRef = useRef<any>(null)
  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current) }, [])

  const pollWorkflow = (wid: string) => {
    setRunning(true)
    timerRef.current = setInterval(async () => {
      try {
        const s: any = await http.get(`/api/workflow/status/${wid}`)
        if (s.code !== 0 || !s.data) return
        setWf(s.data)
        if (s.data.status === 'done' || s.data.status === 'error') {
          clearInterval(timerRef.current)
          setRunning(false)
        }
      } catch { /* 继续轮询 */ }
    }, 1500)
  }

  const run = async () => {
    if (!text.trim()) { message.warning('请输入内容'); return }
    setWf(null)
    try {
      const r: any = await http.post(`/api/skills/${skill.id}/run`, { text })
      if (r.code !== 0) { message.warning(r.msg); return }
      pollWorkflow(r.data.workflow_id)
    } catch { message.error('执行失败') }
  }

  const input = skill.plan.input || ''
  const supportsAudio = input.includes('audio') || input.includes('record')

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const rec = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      mediaRef.current = rec
      chunksRef.current = []
      rec.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        setRecording(false)
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const formData = new FormData()
        formData.append('file', blob, 'recording.webm')
        setWf(null)
        try {
          const r: any = await http.post(`/api/skills/${skill.id}/run-audio`, formData)
          if (r.code !== 0) { message.warning(r.msg || '转写失败'); return }
          pollWorkflow(r.data.workflow_id)
        } catch { message.error('录音上传失败') }
      }
      rec.start(1000)
      setRecording(true)
    } catch { message.error('无法访问麦克风，请检查权限') }
  }

  const stopRecording = () => { mediaRef.current?.stop() }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {supportsAudio && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Button type="primary" danger={recording} icon={<AudioOutlined />}
            onClick={recording ? stopRecording : startRecording} style={{ borderRadius: 100 }}>
            {recording ? '⏹ 停止录音' : '🎤 开始录音'}
          </Button>
          <Text type="secondary" style={{ fontSize: 11 }}>录完自动转写并执行技能</Text>
        </div>
      )}
      <Text type="secondary" style={{ fontSize: 11 }}>{supportsAudio ? '或粘贴文本：' : '输入内容：'}</Text>
      <Input.TextArea value={text} onChange={e => setText(e.target.value)}
        placeholder={skill.input_hint} autoSize={{ minRows: 4, maxRows: 10 }} style={{ fontSize: 13 }} />
      <Button type="primary" icon={<ThunderboltOutlined />} loading={running} onClick={run} style={{ borderRadius: 100, alignSelf: 'flex-start' }}>
        执行技能
      </Button>
      {wf && (
        <div style={{ border: '1px solid rgba(255,255,255,0.08)', borderRadius: 12, padding: 12 }}>
          <div style={{ marginBottom: 8 }}>
            <Badge status={wf.status === 'done' ? 'success' : wf.status === 'error' ? 'error' : 'processing'}
              text={<Text style={{ fontSize: 12 }}>{wf.status === 'done' ? '执行完成' : wf.status === 'error' ? '执行失败' : '执行中…'}</Text>} />
          </div>
          {wf.nodes.map(n => (
            <div key={n.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
              <Badge status={n.status === 'done' ? 'success' : n.status === 'error' ? 'error' : n.status === 'running' ? 'processing' : 'default'} />
              <Text style={{ fontSize: 12, flex: 1 }}>{n.label}</Text>
              {n.error && <Text type="danger" style={{ fontSize: 10 }} ellipsis={{ tooltip: n.error }}>{n.error.slice(0, 40)}</Text>}
            </div>
          ))}
          {wf.status === 'done' && (
            <div style={{ marginTop: 8, maxHeight: 260, overflow: 'auto' }}>
              {Object.entries(wf.results || {}).filter(([k]) => !k.startsWith('__tool_')).map(([k, v]: [string, any]) => (
                <div key={k} style={{ marginBottom: 8 }}>
                  <Text strong style={{ fontSize: 11 }}>{k}</Text>
                  {typeof v === 'object' && v !== null ? (
                    Object.entries(v).filter(([kk]) => kk !== 'text').map(([kk, vv]) => (
                      <div key={kk} style={{ fontSize: 11, color: '#8899bb', wordBreak: 'break-all' }}>
                        <Text type="secondary" style={{ fontSize: 10 }}>{kk}: </Text>
                        {typeof vv === 'string' && vv.length > 150 ? vv.slice(0, 150) + '…' : String(vv)}
                      </div>
                    ))
                  ) : <Text style={{ fontSize: 11 }}>{String(v)}</Text>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
