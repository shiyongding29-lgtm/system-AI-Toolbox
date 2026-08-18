import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Typography, Button, Card, Tag, message, Popconfirm, Row, Col } from 'antd'
import { PlusOutlined, EditOutlined, RobotOutlined, DeleteOutlined } from '@ant-design/icons'
import http from '../../services/http'

const { Title, Text } = Typography

export default function MyRobotPage() {
  const navigate = useNavigate()
  const [robots, setRobots] = useState<any[]>([])
  const [history, setHistory] = useState<Record<string, any[]>>({})
  const [expanded, setExpanded] = useState<string | null>(null)

  const load = async () => {
    try { const r = await http.get('/api/robot/list'); if (r.code === 0) setRobots(r.data) } catch {}
  }
  const loadHistory = async (rid: string) => {
    try { const r = await http.get(`/api/robot/${rid}/history`); if (r.code === 0) setHistory(prev => ({...prev, [rid]: r.data})) } catch {}
  }
  useEffect(() => { load() }, [])

  const startEdit = (r: any) => {
    localStorage.setItem('editing_robot', JSON.stringify(r))
    navigate('/tools/workflow?edit-robot=1')
  }

  const toggleRobot = async (id: string) => {
    await http.post(`/api/robot/${id}/toggle`); load()
  }

  const deleteRobot = async (id: string) => {
    await http.delete(`/api/robot/${id}`); load()
  }

  return (
    <div style={{ padding: '0 24px', maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>
            <RobotOutlined style={{ color: '#00e5ff', marginRight: 8, filter: 'drop-shadow(0 0 8px rgba(0,229,255,0.5))' }} />
            <span style={{ background: 'linear-gradient(135deg, #00e5ff, #7c3aed)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Scheduled Agent 定時智能體（Cron 調度）</span>
          </Title>
          <Text style={{ color: '#5a6d8a', fontSize: 12 }}>Automated workflow execution</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/tools/workflow')}
          style={{ borderRadius: 100, background: 'linear-gradient(135deg, #00e5ff, #7c3aed)', border: 'none', boxShadow: '0 0 16px rgba(0,229,255,0.3)' }}>
          New Robot
        </Button>
      </div>

      {robots.length === 0 && (
        <Card style={{ borderRadius: 16, textAlign: 'center', padding: 60, border: '1px dashed rgba(0,229,255,0.2)', background: 'rgba(0,229,255,0.02)' }}>
          <RobotOutlined style={{ fontSize: 48, color: '#00e5ff', opacity: 0.3 }} />
          <div style={{ marginTop: 16 }}><Text style={{ color: '#8899bb' }}>No robots yet. Create one from Workflow page.</Text></div>
          <Button type="primary" style={{ marginTop: 16, borderRadius: 100 }} onClick={() => navigate('/tools/workflow')}>Go to Workflow</Button>
        </Card>
      )}

      <Row gutter={[16, 16]}>
        {robots.map((r, i) => {
          const sched = r.schedule_type === 'daily' ? `每天 ${r.time}`
            : r.schedule_type === 'weekly' ? `每週${['一','二','三','四','五','六','日'][r.weekday || 0]} ${r.time}`
            : `每月${r.month_day}號 ${r.time}`
          return (
            <Col key={r.id} xs={24} md={12} lg={8}>
              <Card hoverable size="small" className="neon-card"
                style={{
                  borderRadius: 16, border: r.enabled ? '1px solid rgba(16,185,129,0.3)' : '1px solid rgba(255,255,255,0.08)',
                  background: r.enabled ? 'rgba(16,185,129,0.04)' : 'rgba(255,255,255,0.02)',
                  boxShadow: r.enabled ? '0 0 20px rgba(16,185,129,0.1)' : 'none', position: 'relative',
                }}>
                {r.enabled && <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: 'linear-gradient(90deg, transparent, #10b981, transparent)' }} />}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <div>
                    <Text strong style={{ fontSize: 14, display: 'block' }}>{r.name || `Robot ${String(i+1).padStart(4,'0')}`}</Text>
                    <Tag color={r.enabled ? 'green' : 'default'} style={{ borderRadius: 100, fontSize: 10 }}>{r.enabled ? '⚡ Active' : '⏸ Paused'}</Tag>
                  </div>
                  <Popconfirm title="Delete?" onConfirm={() => deleteRobot(r.id)}>
                    <Button size="small" danger icon={<DeleteOutlined />} style={{ borderRadius: 100 }} />
                  </Popconfirm>
                </div>
                <div style={{ padding: '10px 14px', borderRadius: 12, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <Text style={{ fontSize: 11, display: 'block', color: '#8899bb', marginBottom: 4 }}>⏰ {sched}</Text>
                  {r.first_input && <Text style={{ fontSize: 10, color: '#5a6d8a' }}>📝 {r.first_input.substring(0, 80)}</Text>}
                  <Tag style={{ borderRadius: 100, fontSize: 10, marginTop: 6 }}>{(r.plan?.nodes?.length || 0)} tools</Tag>
                </div>
                <div style={{ marginTop: 8, display: 'flex', gap: 4 }}>
                  <Button size="small" icon={<EditOutlined />} style={{ borderRadius: 100, background: 'rgba(0,229,255,0.08)', border: '1px solid rgba(0,229,255,0.15)', color: '#00e5ff' }}
                    onClick={() => startEdit(r)}>Edit</Button>
                  <Button size="small" onClick={() => toggleRobot(r.id)} style={{ borderRadius: 100 }}>{r.enabled ? '⏸' : '▶'}</Button>
                  <Button size="small" style={{ borderRadius: 100 }}
                    onClick={() => { if (expanded === r.id) setExpanded(null); else { loadHistory(r.id); setExpanded(r.id) } }}>
                    📋 History
                  </Button>
                </div>
                {/* Execution history */}
                {expanded === r.id && (
                  <div style={{ marginTop: 8, maxHeight: 200, overflow: 'auto' }}>
                    {(history[r.id] || []).length === 0 && <Text type="secondary" style={{ fontSize: 10 }}>No executions yet</Text>}
                    {(history[r.id] || []).map((h: any, j: number) => (
                      <div key={j} style={{ fontSize: 10, padding: '4px 0', borderBottom: j < (history[r.id]||[]).length-1 ? '1px solid rgba(255,255,255,0.04)' : 'none', display: 'flex', justifyContent: 'space-between' }}>
                        <span><Tag color={h.status==='done'?'green':'red'} style={{ borderRadius: 100, fontSize: 9, marginRight: 4 }}>{h.status}</Tag>{h.result_preview?.substring(0, 40)}</span>
                        <Text type="secondary" style={{ fontSize: 9 }}>{h.time?.substring(5, 16)}</Text>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </Col>
          )
        })}
      </Row>
    </div>
  )
}
