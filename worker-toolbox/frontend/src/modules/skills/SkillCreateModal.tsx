import { useState, useEffect } from 'react'
import { Modal, Form, Input, Button, Typography, Tag, List, Alert, Collapse, Segmented, message } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import http from '../../services/http'

const { Text } = Typography

interface ToolDef { id: string; name: string; description: string; icon: string; color: string; category: string; inputs: string[]; outputs: string[] }

const EMOJIS = ['🧩', '📄', '🎙️', '📋', '🔍', '📽️', '📈', '💼', '✉️', '🌅', '⚙️', '🧠', '✅', '📊', '🌐']
const COLORS = ['#6366f1', '#3b82f6', '#ec4899', '#f59e0b', '#10b981', '#14b8a6', '#ef4444', '#8b5cf6', '#22c55e', '#06b6d4']

const CATEGORY_NAMES: Record<string, string> = {
  input: '📥 输入采集', process: '⚙️ AI 处理', output: '📤 生成输出',
}

export default function SkillCreateModal({ open, onClose, onCreated }: {
  open: boolean; onClose: () => void; onCreated: () => void
}) {
  const [form] = Form.useForm()
  const [tools, setTools] = useState<ToolDef[]>([])
  const [chain, setChain] = useState<ToolDef[]>([])
  const [icon, setIcon] = useState('🧩')
  const [color, setColor] = useState('#8b5cf6')
  const [saving, setSaving] = useState(false)
  const [skillType, setSkillType] = useState<'workflow' | 'knowledge'>('workflow')

  useEffect(() => {
    if (open) {
      form.resetFields(); setChain([]); setIcon('🧩'); setColor('#8b5cf6'); setSkillType('workflow')
      http.get('/api/workflow/tools').then((r: any) => { if (r.code === 0) setTools(r.data) }).catch(() => {})
    }
  }, [open, form])

  const addTool = (t: ToolDef) => {
    setChain(prev => prev.some(x => x.id === t.id) ? prev : [...prev, t])
  }
  const move = (i: number, d: number) => {
    setChain(prev => {
      const next = [...prev]
      const j = i + d
      if (j < 0 || j >= next.length) return prev
      ;[next[i], next[j]] = [next[j], next[i]]
      return next
    })
  }

  const save = async () => {
    const v = await form.validateFields()
    if (skillType === 'workflow' && chain.length === 0) { message.warning('请至少添加一个工具'); return }
    setSaving(true)
    try {
      const r: any = await http.post('/api/skills', {
        name: v.name, description: v.description, icon, color,
        prompt: v.prompt, tool_ids: chain.map(t => t.id), skill_type: skillType,
      })
      if (r.code === 0) { message.success(`技能「${r.data.name}」已创建，AI 立即可用`); onCreated() }
      else message.warning(r.msg)
    } catch { message.error('创建失败') }
    finally { setSaving(false) }
  }

  return (
    <Modal open={open} onCancel={onClose} title="➕ 新建技能" width={860}
      onOk={save} okText="创建" confirmLoading={saving} cancelText="取消">
      <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
        <Form.Item name="name" label="技能名称" rules={[{ required: true, message: '请输入名称' }, { max: 30 }]}>
          <Input placeholder="如：日报生成" maxLength={30} />
        </Form.Item>
        <Form.Item name="description" label="一句话描述（AI 靠它判断何时用这个技能）" rules={[{ required: true, message: '请输入描述' }, { max: 100 }]}>
          <Input placeholder="如：把每天的工作要点整理成结构化日报" maxLength={100} />
        </Form.Item>
        <Form.Item label="图标与颜色">
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {EMOJIS.map(e => (
              <span key={e} onClick={() => setIcon(e)} style={{ fontSize: 18, cursor: 'pointer', padding: 4, borderRadius: 8, background: icon === e ? 'rgba(0,229,255,0.15)' : 'transparent' }}>{e}</span>
            ))}
            <span style={{ width: 1, background: 'rgba(255,255,255,0.15)', margin: '2px 6px' }} />
            {COLORS.map(c => (
              <span key={c} onClick={() => setColor(c)} style={{ width: 20, height: 20, borderRadius: 6, background: c, cursor: 'pointer', border: color === c ? '2px solid #fff' : 'none' }} />
            ))}
          </div>
        </Form.Item>
        <Form.Item name="prompt" label="方法论（输出原则/结构要求，AI 输出时会遵循）" rules={[{ required: true, message: '请输入方法论' }]}>
          <Input.TextArea rows={5} placeholder={'## 输出原则\n- 结论先行\n- 数据具体\n\n## 输出结构\n1. 今日产出\n2. 问题与风险\n3. 明日计划'} />
        </Form.Item>
        <Form.Item label="技能类型">
          <Segmented value={skillType} onChange={(v) => setSkillType(v as 'workflow' | 'knowledge')}
            options={[
              { label: '🔀 流程型（绑定固定工具流程）', value: 'workflow' },
              { label: '💡 知识型（仅方法论，AI 自定工具）', value: 'knowledge' },
            ]} />
        </Form.Item>
        <Form.Item label="工具流程（按执行顺序添加，输出自动串联）" required style={{ display: skillType === 'workflow' ? undefined : 'none' }}>
          <div style={{ display: 'flex', gap: 12, minHeight: 280 }}>
            {/* 左栏：工具目录 */}
            <div style={{ flex: 1, border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, padding: 8, maxHeight: 300, overflow: 'auto' }}>
              <Collapse size="small" ghost defaultActiveKey={['input', 'process', 'output']}
                items={['input', 'process', 'output'].map(cat => ({
                  key: cat,
                  label: <Text style={{ fontSize: 12 }}>{CATEGORY_NAMES[cat] || cat}</Text>,
                  children: (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {tools.filter(t => t.category === cat).map(t => (
                        <div key={t.id} onClick={() => addTool(t)} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 8px', borderRadius: 8, cursor: 'pointer', fontSize: 12 }}
                          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,229,255,0.06)')}
                          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                          <span>{t.icon}</span>
                          <Text style={{ fontSize: 12 }} ellipsis={{ tooltip: t.description }}>{t.name}</Text>
                          <PlusOutlined style={{ marginLeft: 'auto', fontSize: 10, opacity: 0.5 }} />
                        </div>
                      ))}
                    </div>
                  ),
                }))} />
            </div>
            {/* 右栏：已选流程 */}
            <div style={{ flex: 1, border: '1px solid rgba(16,185,129,0.2)', borderRadius: 10, padding: 8, background: 'rgba(16,185,129,0.03)', maxHeight: 300, overflow: 'auto' }}>
              <List size="small" dataSource={chain} locale={{ emptyText: '从左侧点击添加工具' }}
                renderItem={(t, i) => (
                  <List.Item style={{ padding: '6px 4px' }}
                    actions={[
                      <Button key="up" type="text" size="small" icon={<ArrowUpOutlined />} disabled={i === 0} onClick={() => move(i, -1)} />,
                      <Button key="down" type="text" size="small" icon={<ArrowDownOutlined />} disabled={i === chain.length - 1} onClick={() => move(i, 1)} />,
                      <Button key="del" type="text" size="small" danger icon={<DeleteOutlined />} onClick={() => setChain(prev => prev.filter((_, j) => j !== i))} />,
                    ]}>
                    <Text style={{ fontSize: 12 }}><Tag style={{ fontSize: 10, borderRadius: 100 }}>{i + 1}</Tag> {t.icon} {t.name}</Text>
                  </List.Item>
                )} />
            </div>
          </div>
          {chain.length > 1 && (
            <div style={{ marginTop: 8 }}>
              <Alert type="info" showIcon style={{ fontSize: 11 }}
                message={<span>链路预览：{chain.map(t => t.name).join(' → ')}</span>} />
            </div>
          )}
        </Form.Item>
      </Form>
    </Modal>
  )
}
