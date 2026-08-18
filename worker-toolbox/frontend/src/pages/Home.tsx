import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Typography, Row, Col, Card, Checkbox, Tag, Button, Space, Popconfirm, theme, Input, Statistic, Progress, Table, Spin, Tooltip } from 'antd'
import {
  AudioOutlined, FileTextOutlined, MailOutlined, TranslationOutlined,
  CalendarOutlined, SearchOutlined, CheckSquareOutlined, BulbOutlined,
  IdcardOutlined, GlobalOutlined, BarChartOutlined, DiffOutlined,
  ScheduleOutlined, ReadOutlined, FilePptOutlined, ClockCircleOutlined,
  DeleteOutlined, ReloadOutlined, BranchesOutlined, TableOutlined,
  FilterOutlined, ThunderboltOutlined, FireOutlined, CheckCircleOutlined, StarFilled, StarOutlined, PictureOutlined, FilePdfOutlined, SmileOutlined, SwapOutlined, RobotOutlined, QrcodeOutlined,
  CalculatorOutlined, CloudOutlined, DollarOutlined, StockOutlined, LineChartOutlined, ExperimentOutlined, StopOutlined, AimOutlined, TeamOutlined, RadarChartOutlined,
} from '@ant-design/icons'
import http from '../services/http'
import { TOOL_LABELS, TOOL_COLORS } from '../shared'
import AiChat from '../shared/AiChat'

const { Title, Text } = Typography

const TOOL_CATEGORIES = [
  {
    name: '🎯 Skills 技能', tools: [
      { key: 'skills', title: 'Skills', sub: '技能庫', icon: <StarFilled />, color: '#00e5ff' },
    ]
  },
  {
    name: 'Workflow', icon: '🔀', tools: [
      { key: 'workflow', title: 'AI Workflow', sub: '智能工作流', icon: <ThunderboltOutlined />, color: '#00e5ff' },
      { key: 'robot', title: 'Scheduled Agent', sub: '定時智能體 · Cron 調度', icon: <RobotOutlined />, color: '#7c3aed' },
    ]
  },
  {
    name: '📥 Input 輸入採集', tools: [
      { key: 'meeting-recorder', title: 'Meeting Notes', sub: '會議記錄', icon: <AudioOutlined />, color: '#6366f1' },
      { key: 'image-analyzer', title: 'Image Analyzer', sub: '圖片分析', icon: <PictureOutlined />, color: '#ec4899' },
      { key: 'pdf-toolkit', title: 'PDF Toolkit', sub: 'PDF工具', icon: <FilePdfOutlined />, color: '#ef4444' },
      { key: 'file-converter', title: 'File Converter', sub: '文件轉換', icon: <SwapOutlined />, color: '#6366f1' },
      { key: 'web-scraper', title: 'Web Scraper', sub: '網頁抓取', icon: <GlobalOutlined />, color: '#f97316' },
    ]
  },
  {
    name: '⚙️ AI 處理', tools: [
      { key: 'translation-assistant', title: 'Translation', sub: '翻譯寫作', icon: <TranslationOutlined />, color: '#8b5cf6' },
      { key: 'document-summary', title: 'Doc Summary', sub: '文件摘要', icon: <FileTextOutlined />, color: '#3b82f6' },
      { key: 'mindmap', title: 'Mind Map', sub: '思維導圖', icon: <BranchesOutlined />, color: '#ec4899' },
      { key: 'sentiment-analyzer', title: 'Sentiment Analyzer', sub: '情感分析', icon: <SmileOutlined />, color: '#8b5cf6' },
      { key: 'info-extraction', title: 'Info Extract', sub: '資訊提取', icon: <IdcardOutlined />, color: '#0ea5e9' },
      { key: 'table-generator', title: 'Table Generator', sub: '表格生成', icon: <TableOutlined />, color: '#3b82f6' },
      { key: 'data-analysis', title: 'Data Analysis', sub: '數據分析', icon: <BarChartOutlined />, color: '#3b5ccc' },
    ]
  },
  {
    name: '📤 Output 生成輸出', tools: [
      { key: 'ppt-outline', title: 'PPT / HTML', sub: '簡報生成', icon: <FilePptOutlined />, color: '#ef4444' },
      { key: 'chart-generator', title: 'Chart Generator', sub: '圖表生成', icon: <BarChartOutlined />, color: '#22c55e' },
      { key: 'email-doc', title: 'Email & Docs', sub: '郵件公文', icon: <MailOutlined />, color: '#06b6d4' },
      { key: 'deep-research', title: 'Deep Research', sub: '深度調研', icon: <GlobalOutlined />, color: '#14b8a6' },
      { key: 'weekly-report', title: 'Weekly Report', sub: '週報', icon: <CalendarOutlined />, color: '#f59e0b' },
      { key: 'todo-extraction', title: 'Todo Extract', sub: '待辦提取', icon: <CheckSquareOutlined />, color: '#10b981' },
      { key: 'qr-generator', title: 'QR Generator', sub: '二維碼', icon: <QrcodeOutlined />, color: '#6366f1' },
    ]
  },
  {
    name: '🗂️ 知識管理', tools: [
      { key: 'rag-qa', title: 'Knowledge Q&A', sub: '知識庫問答', icon: <SearchOutlined />, color: '#f97316' },
      { key: 'multi-source-reader', title: 'Multi-Source', sub: '多源閱讀', icon: <ReadOutlined />, color: '#65a30d' },
      { key: 'document-comparison', title: 'Doc Compare', sub: '文件對比', icon: <DiffOutlined />, color: '#a855f7' },
      { key: 'spreadsheet', title: 'Spreadsheet AI', sub: '智能表格', icon: <TableOutlined />, color: '#22c55e' },
    ]
  },
  {
    name: '⏰ 自動化與效率', tools: [
      { key: 'task-planning', title: 'Task Planner', sub: '任務規劃', icon: <ScheduleOutlined />, color: '#e11d48' },
      { key: 'pomodoro', title: 'Pomodoro', sub: '番茄鐘', icon: <ClockCircleOutlined />, color: '#f43f5e' },
    ]
  },
  {
    name: '🔧 智能小工具', tools: [
      { key: 'code-tools', title: 'Smart Tools', sub: '計算/日期/換算', icon: <CalculatorOutlined />, color: '#22c55e' },
      { key: 'weather', title: 'Weather', sub: '天氣查詢', icon: <CloudOutlined />, color: '#06b6d4' },
      { key: 'exchange-rate', title: 'Exchange', sub: '匯率查詢', icon: <DollarOutlined />, color: '#14b8a6' },
      { key: 'stock', title: 'Stock', sub: '股價查詢', icon: <StockOutlined />, color: '#ef4444' },
      { key: 'stock-predictor', title: 'Stock Predict', sub: '股票預測', icon: <LineChartOutlined />, color: '#f97316' },
      { key: 'fruit-classifier', title: 'Fruit Classify', sub: '水果識別', icon: <ExperimentOutlined />, color: '#22c55e' },
      { key: 'spam-classifier', title: 'Spam Detect', sub: '垃圾郵件檢測', icon: <StopOutlined />, color: '#ef4444' },
      { key: 'priority-classifier', title: 'Task Priority', sub: '任務優先級', icon: <AimOutlined />, color: '#8b5cf6' },
      { key: 'delay-risk', title: 'Delay Risk', sub: '延期風險檢測', icon: <ClockCircleOutlined />, color: '#f97316' },
      { key: 'attrition-risk', title: 'Attrition Risk', sub: '離職風險預測', icon: <TeamOutlined />, color: '#14b8a6' },
      { key: 'anomaly-detector', title: 'Anomaly Detect', sub: '異常員工識別', icon: <RadarChartOutlined />, color: '#f59e0b' },
    ]
  },
]

const ALL_TOOLS = TOOL_CATEGORIES.flatMap(c => c.tools)

const FAVORITES_KEY = 'toolbox-favorites'
function loadFavorites(): string[] {
  try { return JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]') } catch { return [] }
}
function saveFavs(favs: string[]) {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(favs))
}

interface Todo { id: number; task: string; owner: string; deadline: string; priority: number; completed: boolean; source: string; created_at: string; is_overdue: boolean }
interface HistoryItem { id: number; tool_type: string; title: string; created_at: string }

const WEEKDAYS = ['Sun 日', 'Mon 一', 'Tue 二', 'Wed 三', 'Thu 四', 'Fri 五', 'Sat 六']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function useDateTime() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 30000)
    return () => clearInterval(t)
  }, [])
  const d = now.getDate()
  const suffix = d === 1 ? 'st' : d === 2 ? 'nd' : d === 3 ? 'rd' : 'th'
  return {
    weekday: WEEKDAYS[now.getDay()],
    dateStr: `${WEEKDAYS[now.getDay()]}, ${MONTHS[now.getMonth()]} ${d}${suffix}`,
    dateShort: `${now.getMonth() + 1}/${d}`,
    timeStr: now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }),
  }
}

function generateICS(task: string, deadline: string) {
  const uid = Date.now() + Math.random().toString(36)
  return `BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Worker Toolbox//EN
BEGIN:VEVENT
DTSTART;VALUE=DATE:${deadline.replace(/-/g, '')}
DTEND;VALUE=DATE:${deadline.replace(/-/g, '')}
SUMMARY:${task}
UID:${uid}@worker-toolbox
BEGIN:VALARM
TRIGGER:-PT30M
ACTION:DISPLAY
DESCRIPTION:${task} is due!
END:VALARM
END:VEVENT
END:VCALENDAR`
}

function downloadICS(task: string, deadline: string) {
  const blob = new Blob([generateICS(task, deadline)], { type: 'text/calendar;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = `${task.slice(0, 20)}.ics`; a.click()
  URL.revokeObjectURL(url)
}

function downloadAllICS(todos: Todo[]) {
  const withDeadline = todos.filter(t => t.deadline && !t.completed)
  if (!withDeadline.length) return
  let ics = 'BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Worker Toolbox//EN\n'
  withDeadline.forEach(t => {
    ics += `BEGIN:VEVENT\nDTSTART;VALUE=DATE:${t.deadline.replace(/-/g, '')}\nDTEND;VALUE=DATE:${t.deadline.replace(/-/g, '')}\nSUMMARY:${t.task}\nUID:${Date.now()}${Math.random().toString(36)}@wt\nEND:VEVENT\n`
  })
  ics += 'END:VCALENDAR'
  const blob = new Blob([ics], { type: 'text/calendar;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = 'all-todos.ics'; a.click()
  URL.revokeObjectURL(url)
}

interface DashboardData {
  total_history: number
  today_count: number
  weekly_counts: { tool_type: string; count: number }[]
  todo_stats: { total: number; completed: number; active: number; overdue: number }
  recent_activity: { tool_type: string; title: string; created_at: string }[]
}

function Home({ themeMode, onToggleTheme }: { themeMode: 'light' | 'dark'; onToggleTheme: () => void }) {
  const navigate = useNavigate()
  const { token } = theme.useToken()
  const [todos, setTodos] = useState<Todo[]>([])
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [favorites, setFavorites] = useState<string[]>(loadFavorites)
  const [searchText, setSearchText] = useState('')
  const [filterFav, setFilterFav] = useState(false)
  const [dashData, setDashData] = useState<DashboardData | null>(null)
  const [dashLoading, setDashLoading] = useState(true)
  const [chatOpen, setChatOpen] = useState(false)
  const [robots, setRobots] = useState<any[]>([])

  const loadRobots = async () => {
    try { const r = await http.get('/api/robot/list'); if (r.code === 0) setRobots(r.data) } catch {}
  }
  const isDark = themeMode === 'dark'

  // Keyboard shortcut: Cmd+J to open AI on home page
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'j') {
        e.preventDefault()
        setChatOpen(v => !v)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])
  const dt = useDateTime()

  const loadAll = useCallback(async () => {
    try { const d: any = await http.get('/api/todos'); if (d.code === 0) setTodos(d.data) } catch {}
    try { const d: any = await http.get('/api/history/list', { params: { page_size: 20 } }); if (d.code === 0) setHistory(d.data || []) } catch {}
  }, [])

  const loadDashboard = useCallback(async () => {
    setDashLoading(true)
    try { const d: any = await http.get('/api/dashboard'); if (d.code === 0) setDashData(d.data) } catch {}
    finally { setDashLoading(false) }
  }, [])

  useEffect(() => { loadAll(); loadDashboard(); loadRobots() }, [loadAll, loadDashboard])

  const toggleTodo = async (id: number, completed: boolean) => { await http.put(`/api/todos/${id}`, { completed: !completed }); loadAll(); loadDashboard() }
  const deleteTodo = async (id: number) => { await http.delete(`/api/todos/${id}`); loadAll(); loadDashboard() }
  const incompleteTodos = todos.filter(t => !t.completed)
  const completedTodos = todos.filter(t => t.completed)
  const overdueCount = todos.filter(t => t.is_overdue && !t.completed).length

  const filteredCategories = useMemo(() => {
    const q = searchText.toLowerCase()
    return TOOL_CATEGORIES.map(cat => ({
      ...cat,
      tools: cat.tools.filter(t => {
        if (filterFav && !favorites.includes(t.key)) return false
        if (q && !t.title.toLowerCase().includes(q) && !t.sub.includes(q) && !t.key.includes(q)) return false
        return true
      })
    })).filter(cat => cat.tools.length > 0)
  }, [searchText, filterFav, favorites])

  // Dashboard computed values
  const doneRate = dashData && dashData.todo_stats.total > 0
    ? Math.round((dashData.todo_stats.completed / dashData.todo_stats.total) * 100)
    : 0

  const weeklyColumns = [
    { title: 'Tool', dataIndex: 'tool_type', key: 'tool',
      render: (t: string) => (
        <span style={{ fontSize: 12 }}>
          <span style={{ display: 'inline-block', width: 7, height: 7, borderRadius: '50%', background: TOOL_COLORS[t] || token.colorPrimary, marginRight: 6 }} />
          {TOOL_LABELS[t] || t}
        </span>
      ),
    },
    { title: 'Uses', dataIndex: 'count', key: 'count', width: 50,
      render: (c: number) => <Text strong style={{ fontSize: 12 }}>{c}</Text>,
    },
    { title: '%', dataIndex: 'count', key: 'share', width: 80,
      render: (c: number) => {
        const total = dashData ? dashData.weekly_counts.reduce((s, i) => s + i.count, 0) || 1 : 1
        return <Progress percent={Math.round((c / total) * 100)} size="small" style={{ minWidth: 60, margin: 0 }} />
      },
    },
  ]

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '16px 28px', minHeight: '100vh', position: 'relative', zIndex: 1 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={2} style={{ margin: 0, fontWeight: 800, letterSpacing: -0.5 }}>
            <span style={{ background: 'linear-gradient(135deg, #00e5ff 0%, #7c3aed 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>AI Toolbox</span>
          </Title>
          <Text style={{ fontSize: 12, color: '#5a6d8a' }}>AI-Powered · 24 Tools · All-in-One</Text>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Space size={4}>
            <Button size="small" icon={<ReloadOutlined />} onClick={() => { loadAll(); loadDashboard(); loadRobots() }} style={{ borderRadius: 100 }}>Refresh</Button>
            <button onClick={onToggleTheme} style={{
              border: '1px solid ' + token.colorBorderSecondary, borderRadius: 20, padding: '6px 12px', cursor: 'pointer',
              fontSize: 15, background: token.colorBgContainer, display: 'flex', alignItems: 'center', gap: 4,
            }}>{themeMode === 'dark' ? '🌙' : '☀️'}</button>
          </Space>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#00e5ff', letterSpacing: -0.3 }}>{dt.dateStr}</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: '#e0e8ff', fontFamily: "'SF Mono', monospace", letterSpacing: -1, textShadow: '0 0 20px rgba(0,229,255,0.3)' }}>{dt.timeStr}</div>
          </div>
        </div>
      </div>

      <Row gutter={24}>
        {/* Left column */}
        <Col xs={24} lg={15}>
          {/* Scheduled Agent section */}
          {robots.length > 0 && (
            <Card size="small"
              title={<span style={{ color: '#00e5ff' }}>🤖 Scheduled Agent 定時智能體（Cron 調度）</span>}
              style={{
                borderRadius: 16, marginBottom: 20, border: '1px solid rgba(0,229,255,0.3)',
                background: 'linear-gradient(135deg, rgba(0,229,255,0.06), rgba(124,58,237,0.05), rgba(0,229,255,0.02))',
                boxShadow: '0 0 40px rgba(0,229,255,0.1), 0 0 80px rgba(0,229,255,0.05), inset 0 1px 0 rgba(0,229,255,0.08)',
                animation: 'glowPulse 3s infinite',
              }}
              styles={{ body: { padding: '12px 20px' } }}>
              <Row gutter={[12, 12]}>
                {robots.map((r, i) => {
                  const schedLabel = r.schedule_type === 'daily' ? `每天 ${r.time}` : r.schedule_type === 'weekly' ? `每週${['一','二','三','四','五','六','日'][r.weekday||0]} ${r.time}` : `每月${r.month_day}號 ${r.time}`
                  return (
                    <Col key={r.id} xs={24} sm={12} md={8} lg={6}>
                      <div style={{
                        borderRadius: 14, padding: '16px',
                        border: `1px solid ${r.enabled ? 'rgba(16,185,129,0.3)' : 'rgba(255,255,255,0.08)'}`,
                        background: r.enabled ? 'rgba(16,185,129,0.05)' : 'rgba(255,255,255,0.02)',
                        boxShadow: r.enabled ? '0 0 16px rgba(16,185,129,0.1)' : 'none',
                        position: 'relative', overflow: 'hidden',
                      }}>
                        {r.enabled && <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: 'linear-gradient(90deg, transparent, #10b981, transparent)', animation: 'scanLine 3s infinite' }} />}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                          <div>
                            <Text strong style={{ fontSize: 14, display: 'block', color: r.enabled ? '#e0e8ff' : '#8899bb' }} ellipsis>
                              {r.name || `Robot ${String(i+1).padStart(4,'0')}`}
                            </Text>
                            <Tag color={r.enabled ? 'green' : 'default'} style={{ borderRadius: 100, fontSize: 10, marginTop: 2 }}>
                              {r.enabled ? '⚡ Active' : '⏸ Paused'}
                            </Tag>
                          </div>
                        </div>
                        <Text style={{ fontSize: 11, display: 'block', color: '#8899bb', marginBottom: 4 }}>📋 {schedLabel}</Text>
                        {r.first_input && <Text style={{ fontSize: 10, color: '#5a6d8a', display: 'block', marginBottom: 8 }} ellipsis>📝 {r.first_input.substring(0, 60)}</Text>}
                        <div style={{ display: 'flex', gap: 4 }}>
                          <Button size="small" style={{ borderRadius: 100, fontSize: 10, background: 'rgba(0,229,255,0.08)', border: '1px solid rgba(0,229,255,0.15)', color: '#00e5ff' }}
                            onClick={() => navigate('/tools/robot')}>✏️ Edit</Button>
                          <Button size="small" style={{ borderRadius: 100, fontSize: 10 }}
                            onClick={async () => { await http.post(`/api/robot/${r.id}/toggle`); loadRobots() }}>{r.enabled ? '⏸' : '▶'}</Button>
                          <Popconfirm title="Delete Robot?" onConfirm={async () => { await http.delete(`/api/robot/${r.id}`); loadRobots() }}>
                            <Button size="small" danger icon={<DeleteOutlined />} style={{ borderRadius: 100 }} />
                          </Popconfirm>
                        </div>
                      </div>
                    </Col>
                  )
                })}
              </Row>
            </Card>
          )}

          {/* ── Apple Watch style tool grid ── */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 8 }}>
            <Input size="small" prefix={<SearchOutlined style={{ opacity: 0.3 }} />}
              placeholder="搜尋工具...  Search tools" value={searchText}
              onChange={e => setSearchText(e.target.value)} allowClear
              style={{ width: 220, borderRadius: 8 }} />
            <Button size="small" type={filterFav ? 'primary' : 'default'}
              onClick={() => setFilterFav(!filterFav)}
              style={{ borderRadius: 100, fontSize: 11 }}>
              <StarFilled style={{ fontSize: 10, marginRight: 4 }} />Favorites
            </Button>
          </div>

          {filteredCategories.length === 0 && (
            <div style={{ textAlign: 'center', padding: 40, opacity: 0.4 }}>
              <FilterOutlined style={{ fontSize: 32 }} />
              <div style={{ marginTop: 8, fontSize: 13 }}>No tools match</div>
            </div>
          )}

          {/* Workflow — big standalone card */}
          {(() => {
            const wfCat = filteredCategories.find(c => c.name === 'Workflow')
            const wf = wfCat?.tools[0]
            if (!wf) return null
            return (
              <div key="workflow-section" style={{ marginBottom: 8 }}>
                <Card hoverable onClick={() => navigate(`/tools/${wf.key}`)} size="small"
                  className="neon-card"
                  styles={{ body: { padding: '28px 24px' } }}
                  style={{
                    borderRadius: 20, border: '1px solid rgba(0,229,255,0.3)',
                    background: 'linear-gradient(135deg, rgba(0,229,255,0.1), rgba(124,58,237,0.08))',
                    boxShadow: '0 0 32px rgba(0,229,255,0.2)', marginBottom: 24,
                    transition: 'all 0.3s', animation: 'glowPulse 2s infinite',
                  }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div style={{
                      width: 56, height: 56, borderRadius: 16, flexShrink: 0,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      background: '#00e5ff20', color: '#00e5ff', fontSize: 28,
                      boxShadow: '0 0 20px rgba(0,229,255,0.4)',
                    }}><ThunderboltOutlined /></div>
                    <div>
                      <Text strong style={{ fontSize: 18, color: '#00e5ff', display: 'block' }}>{wf.title}</Text>
                      <Text style={{ fontSize: 12, color: '#8899bb' }}>{wf.sub}</Text>
                    </div>
                  </div>
                </Card>
              </div>
            )
          })()}

          {/* All other tools — single bubble pool */}
          <div style={{
            display: 'flex', flexWrap: 'wrap', gap: 14, justifyContent: 'flex-start',
          }}>
            {filteredCategories.filter(c => c.name !== 'Workflow').flatMap(c => c.tools).map(tool => (
              <div key={tool.key} className="tool-bubble"
                onClick={() => navigate(`/tools/${tool.key}`)}
                style={{ width: 90, height: 100 }}>
                <div style={{ position: 'absolute', top: -2, right: 2, zIndex: 2 }}
                  onClick={(e: any) => { e.stopPropagation(); }}>
                  {favorites.includes(tool.key)
                    ? <StarFilled style={{ color: '#f59e0b', fontSize: 11 }}
                        onClick={(e2: any) => { e2.stopPropagation(); setFavorites(prev => prev.filter(k => k !== tool.key)); saveFavs(favorites.filter(k => k !== tool.key)) }} />
                    : <StarOutlined style={{ opacity: 0.2, fontSize: 11 }}
                        onClick={(e2: any) => { e2.stopPropagation(); setFavorites(prev => [...prev, tool.key]); saveFavs([...favorites, tool.key]) }} />}
                </div>
                <div className="bubble-icon" style={{
                  width: 54, height: 54, borderRadius: 16,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: `${tool.color}15`, color: tool.color, fontSize: 24,
                  boxShadow: `0 4px 16px ${tool.color}10`,
                }}>{tool.icon}</div>
                <Text style={{ fontSize: 10, marginTop: 6, textAlign: 'center', color: token.colorTextSecondary, lineHeight: 1.3, maxWidth: 80 }} ellipsis={{ tooltip: tool.title }}>{tool.title}</Text>
              </div>
            ))}
          </div>
        </Col>

        {/* Right column */}
        <Col xs={24} lg={9}>
          {/* Todos card */}
          <Card size="small" title={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span><CheckSquareOutlined style={{ color: '#ef4444', marginRight: 8 }} />Todos 待辦事項</span>
              <Space size={4}>
                {overdueCount > 0 && <Tag color="red" style={{ borderRadius: 100 }}>{overdueCount} overdue 逾期</Tag>}
                <Button size="small" icon={<CalendarOutlined />} onClick={() => downloadAllICS(todos)} style={{ borderRadius: 100 }}>Calendar 日曆</Button>
                <Button type="link" size="small" onClick={() => navigate('/tools/todos')}>All 全部</Button>
              </Space>
            </div>
          }
            styles={{ body: { padding: 0, maxHeight: 320, overflow: 'auto' } }}
            style={{ marginBottom: 16, borderRadius: 14, border: 'none', background: token.colorBgContainer }}>
            {todos.length === 0 && <div style={{ padding: 24, textAlign: 'center' }}><Text type="secondary">No todos yet 暫無待辦事項</Text></div>}
            {todos.filter(t => !t.completed).map(t => (
              <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 20px', borderBottom: `1px solid ${token.colorBorderSecondary}`, background: t.is_overdue ? 'rgba(239,68,68,0.04)' : 'transparent', borderLeft: t.is_overdue ? '3px solid #ef4444' : '3px solid transparent' }}>
                <Checkbox checked={false} onChange={() => toggleTodo(t.id, t.completed)} style={{ transform: 'scale(1.1)' }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Text style={{ fontSize: 13 }} ellipsis={{ tooltip: t.task }}>{t.task}</Text>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 2 }}>
                    {t.is_overdue && <Tag color="red" style={{ fontSize: 10, borderRadius: 100, lineHeight: '18px' }}>Overdue 逾期</Tag>}
                    {t.owner && <Text type="secondary" style={{ fontSize: 10 }}>{t.owner}</Text>}
                    {t.deadline && <Text type="secondary" style={{ fontSize: 10 }}>{t.deadline}</Text>}
                    {t.deadline && (
                      <Button size="small" type="link" icon={<CalendarOutlined />} onClick={() => downloadICS(t.task, t.deadline)} style={{ fontSize: 10, padding: 0, height: 18 }}>
                        Add to Calendar 加入日曆
                      </Button>
                    )}
                  </div>
                </div>
                <Popconfirm title="Delete 刪除?" onConfirm={() => deleteTodo(t.id)}>
                  <Button size="small" danger icon={<DeleteOutlined />} type="text" />
                </Popconfirm>
              </div>
            ))}
            {completedTodos.length > 0 && <div style={{ padding: '8px 20px 12px' }}><Text type="secondary" style={{ fontSize: 11 }}>{completedTodos.length} completed 已完成</Text></div>}
          </Card>

          {/* Weekly tool usage (compact) */}
          {dashData && dashData.weekly_counts.length > 0 && (
            <Card size="small" title={<span><BarChartOutlined style={{ marginRight: 6, color: token.colorPrimary }} />本周工具使用</span>}
              style={{ marginBottom: 16, borderRadius: 14, border: 'none', background: token.colorBgContainer }}
              styles={{ body: { padding: 4 } }}>
              <Table dataSource={dashData.weekly_counts} columns={weeklyColumns}
                rowKey="tool_type" size="small" pagination={false} showHeader={false} />
            </Card>
          )}

          {/* Recent activity */}
          <Card size="small" title={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span><ClockCircleOutlined style={{ color: token.colorPrimary, marginRight: 8 }} />Recent 最近使用</span>
              <Button type="link" size="small" onClick={() => navigate('/tools/history')}>All 全部</Button>
            </div>
          }
            styles={{ body: { padding: 0, maxHeight: 280, overflow: 'auto' } }}
            style={{ borderRadius: 14, border: 'none', background: token.colorBgContainer }}>
            {history.length === 0 && <div style={{ padding: 24, textAlign: 'center' }}><Text type="secondary">No history yet 暫無記錄</Text></div>}
            {history.slice(0, 10).map(h => (
              <div key={h.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 20px', borderBottom: `1px solid ${token.colorBorderSecondary}` }}>
                <Tag color="blue" style={{ margin: 0, borderRadius: 100, fontSize: 10 }}>{TOOL_LABELS[h.tool_type] || h.tool_type}</Tag>
                <Text ellipsis style={{ flex: 1, fontSize: 13 }}>{h.title}</Text>
                <Text type="secondary" style={{ fontSize: 10, flexShrink: 0 }}>{h.created_at}</Text>
              </div>
            ))}
          </Card>
        </Col>
      </Row>

      {/* AI Chat button (bottom-right) */}
      {/* AI floating button */}
      <div style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1000 }}>
        <Button
          shape="circle" size="large"
          onClick={() => setChatOpen(true)}
          style={{
            width: 52, height: 52, borderRadius: '50%',
            boxShadow: '0 0 24px rgba(0,229,255,0.35)',
            background: 'linear-gradient(135deg, #0a0e27, #1a1040)',
            border: '1.5px solid rgba(0,229,255,0.3)',
            color: '#00e5ff', fontSize: 16, fontWeight: 900,
            letterSpacing: 1, fontFamily: "'Inter','SF Pro Display',sans-serif",
          }}
        >AI</Button>
      </div>

      {/* AI Chat */}
      <AiChat open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  )
}

export default Home
