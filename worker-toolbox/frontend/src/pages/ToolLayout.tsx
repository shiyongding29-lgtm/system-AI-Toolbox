import { useState, useMemo, useCallback, useEffect, Suspense, lazy } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Menu, Typography, Switch, Button, theme, Input, Tooltip } from 'antd'
import {
  AudioOutlined, FileTextOutlined, MailOutlined, TranslationOutlined,
  CalendarOutlined, SearchOutlined, CheckSquareOutlined, IdcardOutlined,
  HomeOutlined, GlobalOutlined, BarChartOutlined, DiffOutlined,
  ScheduleOutlined, ReadOutlined, BulbOutlined, ClockCircleOutlined,
  ThunderboltOutlined, OrderedListOutlined, FilePptOutlined, BranchesOutlined, TableOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined, StarFilled, StarOutlined,
  PictureOutlined, FilePdfOutlined, SmileOutlined, SwapOutlined, RobotOutlined, QrcodeOutlined,
  CalculatorOutlined, CloudOutlined, DollarOutlined, StockOutlined, LineChartOutlined, ExperimentOutlined, StopOutlined, AimOutlined, TeamOutlined, RadarChartOutlined,
} from '@ant-design/icons'
import { ErrorBoundary, LoadingSkeleton } from '../shared'
import CommandPalette from '../shared/CommandPalette'
import AiChat from '../shared/AiChat'
import VoiceInput from '../shared/VoiceInput'

const LazyPage = (factory: () => Promise<any>) => {
  const Comp = lazy(factory)
  return function LazyWrapper() {
    return (
      <ErrorBoundary>
        <Suspense fallback={<LoadingSkeleton />}>
          <Comp />
        </Suspense>
      </ErrorBoundary>
    )
  }
}

const DashboardPage = LazyPage(() => import('../modules/dashboard/DashboardPage'))
const WorkflowPage = LazyPage(() => import('../modules/workflow/WorkflowPage'))

const MeetingRecorderPage = LazyPage(() => import('../modules/meeting-recorder/MeetingRecorderPage'))
const DocumentSummaryPage = LazyPage(() => import('../modules/document-summary/DocumentSummaryPage'))
const EmailDocPage = LazyPage(() => import('../modules/email-doc/EmailDocPage'))
const TranslationAssistantPage = LazyPage(() => import('../modules/translation-assistant/TranslationAssistantPage'))
const WeeklyReportPage = LazyPage(() => import('../modules/weekly-report/WeeklyReportPage'))
const RagQaPage = LazyPage(() => import('../modules/rag-qa/RagQaPage'))
const PptOutlinePage = LazyPage(() => import('../modules/ppt-outline/PptOutlinePage'))
const TodoExtractionPage = LazyPage(() => import('../modules/todo-extraction/TodoExtractionPage'))
const InfoExtractionPage = LazyPage(() => import('../modules/info-extraction/InfoExtractionPage'))
const DeepResearchPage = LazyPage(() => import('../modules/deep-research/DeepResearchPage'))
const DataAnalysisPage = LazyPage(() => import('../modules/data-analysis/DataAnalysisPage'))
const DocumentComparisonPage = LazyPage(() => import('../modules/document-comparison/DocumentComparisonPage'))
const TaskPlanningPage = LazyPage(() => import('../modules/task-planning/TaskPlanningPage'))
const MultiSourceReaderPage = LazyPage(() => import('../modules/multi-source-reader/MultiSourceReaderPage'))
const HistoryPanel = LazyPage(() => import('../modules/history/HistoryPanel'))
const TodoBoard = LazyPage(() => import('../modules/todo-extraction/TodoBoard'))
const MindmapPage = LazyPage(() => import('../modules/mindmap/MindmapPage'))
const SpreadsheetPage = LazyPage(() => import('../modules/spreadsheet/SpreadsheetPage'))
const PomodoroPage = LazyPage(() => import('../modules/pomodoro/PomodoroPage'))
const ImageAnalyzerPage = LazyPage(() => import('../modules/image-analyzer/ImageAnalyzerPage'))
const ChartGeneratorPage = LazyPage(() => import('../modules/chart-generator/ChartGeneratorPage'))
const TableGeneratorPage = LazyPage(() => import('../modules/table-generator/TableGeneratorPage'))
const PdfToolkitPage = LazyPage(() => import('../modules/pdf-toolkit/PdfToolkitPage'))
const SentimentAnalyzerPage = LazyPage(() => import('../modules/sentiment-analyzer/SentimentAnalyzerPage'))
const FileConverterPage = LazyPage(() => import('../modules/file-converter/FileConverterPage'))
const MyRobotPage = LazyPage(() => import('../modules/robot/MyRobotPage'))
const WebScraperPage = LazyPage(() => import('../modules/web-scraper/WebScraperPage'))
const QrGeneratorPage = LazyPage(() => import('../modules/qr-generator/QrGeneratorPage'))
const CodeToolsPage = LazyPage(() => import('../modules/code-tools/CodeToolsPage'))
const WeatherPage = LazyPage(() => import('../modules/weather/WeatherPage'))
const ExchangeRatePage = LazyPage(() => import('../modules/exchange-rate/ExchangeRatePage'))
const StockPage = LazyPage(() => import('../modules/stock/StockPage'))
const StockPredictPage = LazyPage(() => import('../modules/stock/StockPredictPage'))
const FruitClassifierPage = LazyPage(() => import('../modules/fruit-classifier/FruitClassifierPage'))
const SpamClassifierPage = LazyPage(() => import('../modules/spam-classifier/SpamClassifierPage'))
const PriorityClassifierPage = LazyPage(() => import('../modules/priority-classifier/PriorityClassifierPage'))
const DelayRiskPage = LazyPage(() => import('../modules/delay-risk/DelayRiskPage'))
const AttritionRiskPage = LazyPage(() => import('../modules/attrition-risk/AttritionRiskPage'))
const AnomalyDetectorPage = LazyPage(() => import('../modules/anomaly-detector/AnomalyDetectorPage'))
const SkillsPage = LazyPage(() => import('../modules/skills/SkillsPage'))

const { Text } = Typography

const MENU_ITEMS = [
  { key: 'skills',                label: 'Skills 技能',                    icon: <StarFilled /> },
  { key: 'robot',                 label: 'Scheduled Agent 定時智能體',      icon: <RobotOutlined /> },
  { key: 'workflow',             label: 'Workflow 智能工作流',          icon: <ThunderboltOutlined /> },
  { key: 'meeting-recorder',     label: 'Meeting Notes 會議記錄',       icon: <AudioOutlined /> },
  { key: 'document-summary',     label: 'Doc Summary 文件摘要',        icon: <FileTextOutlined /> },
  { key: 'email-doc',            label: 'Email & Docs 郵件公文',       icon: <MailOutlined /> },
  { key: 'translation-assistant',label: 'Translation 翻譯寫作',        icon: <TranslationOutlined /> },
  { key: 'weekly-report',        label: 'Weekly Report 週報',          icon: <CalendarOutlined /> },
  { key: 'ppt-outline',          label: 'PPT / HTML 簡報生成',         icon: <FilePptOutlined /> },
  { key: 'spreadsheet',          label: 'Spreadsheet AI 智能表格',    icon: <TableOutlined /> },
  { key: 'mindmap',              label: 'Mind Map 思維導圖',           icon: <BranchesOutlined /> },
  { key: 'todo-extraction',      label: 'Todo Extract 待辦提取',      icon: <CheckSquareOutlined /> },
  { key: 'todos',                label: 'Todo List 待辦事項',          icon: <OrderedListOutlined /> },
  { key: 'pomodoro',             label: 'Pomodoro 番茄鐘',             icon: <ClockCircleOutlined /> },
  { key: 'dashboard',            label: 'Dashboard 數據看板',            icon: <BarChartOutlined /> },
  { key: 'info-extraction',      label: 'Info Extract 資訊提取',      icon: <IdcardOutlined /> },
  { key: 'rag-qa',               label: 'Knowledge Q&A 知識庫問答',    icon: <SearchOutlined /> },
  { key: 'deep-research',        label: 'Deep Research 深度調研',      icon: <GlobalOutlined /> },
  { key: 'data-analysis',        label: 'Data Analysis 數據分析',      icon: <BarChartOutlined /> },
  { key: 'document-comparison',  label: 'Doc Compare 文件對比',        icon: <DiffOutlined /> },
  { key: 'task-planning',        label: 'Task Planning 任務規劃',      icon: <ScheduleOutlined /> },
  { key: 'multi-source-reader',  label: 'Multi-Source 多源閱讀',       icon: <ReadOutlined /> },
  { key: 'history',              label: 'History 歷史記錄',            icon: <ClockCircleOutlined /> },
  { key: 'image-analyzer',       label: 'Image Analyzer 圖片分析',     icon: <PictureOutlined /> },
  { key: 'chart-generator',      label: 'Chart Generator 圖表生成',    icon: <BarChartOutlined /> },
  { key: 'table-generator',      label: 'Table Generator 表格生成',    icon: <TableOutlined /> },
  { key: 'pdf-toolkit',           label: 'PDF Toolkit PDF工具',         icon: <FilePdfOutlined /> },
  { key: 'sentiment-analyzer',    label: 'Sentiment Analyzer 情感分析',  icon: <SmileOutlined /> },
  { key: 'file-converter',         label: 'File Converter 文件轉換',     icon: <SwapOutlined /> },
  { key: 'web-scraper',            label: 'Web Scraper 網頁抓取',       icon: <GlobalOutlined /> },
  { key: 'qr-generator',           label: 'QR Generator 二維碼',        icon: <QrcodeOutlined /> },
  { key: 'code-tools',             label: 'Smart Tools 智能小工具',     icon: <CalculatorOutlined /> },
  { key: 'weather',                 label: 'Weather 天氣查詢',          icon: <CloudOutlined /> },
  { key: 'exchange-rate',           label: 'Exchange Rate 匯率查詢',    icon: <DollarOutlined /> },
  { key: 'stock',                   label: 'Stock Quote 股價查詢',      icon: <StockOutlined /> },
  { key: 'stock-predictor',         label: 'Stock Predict 股票預測',     icon: <LineChartOutlined /> },
  { key: 'fruit-classifier',        label: 'Fruit Classify 水果識別',    icon: <ExperimentOutlined /> },
  { key: 'spam-classifier',         label: 'Spam Detect 垃圾郵件檢測',   icon: <StopOutlined /> },
  { key: 'priority-classifier',     label: 'Task Priority 任務優先級',   icon: <AimOutlined /> },
  { key: 'delay-risk',              label: 'Delay Risk 延期風險檢測',    icon: <ClockCircleOutlined /> },
  { key: 'attrition-risk',          label: 'Attrition Risk 離職風險',    icon: <TeamOutlined /> },
  { key: 'anomaly-detector',        label: 'Anomaly Detect 異常識別',    icon: <RadarChartOutlined /> },
]

const PAGE_MAP: Record<string, React.ComponentType> = {
  'meeting-recorder': MeetingRecorderPage, 'document-summary': DocumentSummaryPage,
  'email-doc': EmailDocPage, 'translation-assistant': TranslationAssistantPage,
  'weekly-report': WeeklyReportPage, 'rag-qa': RagQaPage,
  'ppt-outline': PptOutlinePage, 'todo-extraction': TodoExtractionPage,
  'info-extraction': InfoExtractionPage, 'deep-research': DeepResearchPage,
  'data-analysis': DataAnalysisPage, 'document-comparison': DocumentComparisonPage,
  'task-planning': TaskPlanningPage, 'multi-source-reader': MultiSourceReaderPage,
  'history': HistoryPanel, 'todos': TodoBoard, 'mindmap': MindmapPage,
  'spreadsheet': SpreadsheetPage,
  'pomodoro': PomodoroPage,
  'dashboard': DashboardPage,
  'workflow': WorkflowPage,
  'robot': MyRobotPage,
  'image-analyzer': ImageAnalyzerPage,
  'chart-generator': ChartGeneratorPage,
  'table-generator': TableGeneratorPage,
  'pdf-toolkit': PdfToolkitPage,
  'sentiment-analyzer': SentimentAnalyzerPage,
  'file-converter': FileConverterPage,
  'web-scraper': WebScraperPage,
  'qr-generator': QrGeneratorPage,
  'code-tools': CodeToolsPage,
  'weather': WeatherPage,
  'exchange-rate': ExchangeRatePage,
  'stock': StockPage,
  'stock-predictor': StockPredictPage,
  'fruit-classifier': FruitClassifierPage,
  'spam-classifier': SpamClassifierPage,
  'priority-classifier': PriorityClassifierPage,
  'delay-risk': DelayRiskPage,
  'attrition-risk': AttritionRiskPage,
  'anomaly-detector': AnomalyDetectorPage,
  'skills': SkillsPage,
}

const FAVORITES_KEY = 'toolbox-favorites'

function loadFavorites(): string[] {
  try { return JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]') } catch { return [] }
}

function saveFavorites(favs: string[]) {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(favs))
}

function ToolLayout({ themeMode, onToggleTheme }: { themeMode: 'light' | 'dark'; onToggleTheme: () => void }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [search, setSearch] = useState('')
  const [favorites, setFavorites] = useState<string[]>(loadFavorites)
  const [cmdOpen, setCmdOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const { token } = theme.useToken()

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setCmdOpen(v => !v)
      }
      // Cmd+J / Ctrl+J 打开 AI 对话
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'j') {
        e.preventDefault()
        setChatOpen(v => !v)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const pathParts = location.pathname.split('/')
  const activeKey = (pathParts[pathParts.length - 1] || '').split('?')[0] // strip query params

  const toggleFavorite = useCallback((key: string) => {
    setFavorites(prev => {
      const next = prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
      saveFavorites(next)
      return next
    })
  }, [])

  const filteredItems = useMemo(() => {
    let items = MENU_ITEMS
    if (search.trim()) {
      const q = search.toLowerCase()
      items = items.filter(i => i.label.toLowerCase().includes(q) || i.key.includes(q))
    }
    return items.map(item => ({
      ...item,
      label: (
        <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.label}</span>
          <span
            onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation(); toggleFavorite(item.key) }}
            style={{
              cursor: 'pointer', fontSize: collapsed ? 16 : 14, flexShrink: 0,
              padding: collapsed ? '4px' : '6px 8px', marginLeft: collapsed ? 0 : 4,
              zIndex: 10, position: 'relative', display: 'inline-flex', alignItems: 'center',
            }}
            title={favorites.includes(item.key) ? '取消收藏' : '加入收藏'}>
              {favorites.includes(item.key)
                ? <StarFilled style={{ color: '#f59e0b' }} />
                : <StarOutlined style={{ opacity: 0.3 }} />}
            </span>
        </span>
      ),
    }))
  }, [search, collapsed, favorites, toggleFavorite])

  const favKeys = useMemo(() => {
    if (!favorites.length) return null
    return favorites.filter(k => MENU_ITEMS.some(m => m.key === k))
  }, [favorites])

  return (
    <div style={{ height: '100vh', display: 'flex' }}>
      {/* Sidebar — glass + neon */}
      <div style={{
        width: collapsed ? 64 : 260, flexShrink: 0, transition: 'width 0.2s ease',
        background: 'rgba(10,15,40,0.85)', backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        borderRight: '1px solid rgba(0,229,255,0.10)',
        boxShadow: '2px 0 24px rgba(0,0,0,0.3)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden', zIndex: 10, position: 'relative',
      }}>
        {/* Subtle scan line effect */}
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 1, background: 'linear-gradient(90deg, transparent, rgba(0,229,255,0.15), transparent)', zIndex: 1, pointerEvents: 'none' }} />
        {/* Logo */}
        <div style={{
          padding: '18px 16px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10,
          borderBottom: '1px solid rgba(0,229,255,0.08)',
        }} onClick={() => navigate('/')}>
          <div style={{
            width: 36, height: 36, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, background: 'linear-gradient(135deg, #00e5ff, #7c3aed)',
            boxShadow: '0 0 16px rgba(0,229,255,0.3)',
          }}>
            <HomeOutlined style={{ color: '#fff', fontSize: 16 }} />
          </div>
          {!collapsed && <Text strong style={{ fontSize: 14, whiteSpace: 'nowrap', background: 'linear-gradient(90deg, #e0e8ff, #00e5ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>AI Toolbox</Text>}
        </div>

        {/* Search */}
        {!collapsed && (
          <div style={{ padding: '8px 12px' }}>
            <Input
              size="small" prefix={<SearchOutlined style={{ opacity: 0.4 }} />}
              placeholder="Search tools 搜索工具..." value={search}
              onChange={e => setSearch(e.target.value)} allowClear
              style={{ borderRadius: 8, border: 'none', background: token.colorFillSecondary }}
            />
          </div>
        )}

        {/* Favorites section */}
        {!collapsed && favKeys && favKeys.length > 0 && (
          <div style={{ padding: '0 12px 4px' }}>
            <Text type="secondary" style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: 1, paddingLeft: 8 }}>
              Favorites 收藏
            </Text>
          </div>
        )}

        {/* Menu */}
        <Menu mode="inline" selectedKeys={activeKey ? [activeKey] : []}
          items={filteredItems}
          onClick={({ key }) => navigate(`/tools/${key}`)}
          style={{ borderRight: 'none', flex: 1, padding: '4px 0', fontSize: 13, overflow: 'auto' }}
        />

        {/* Collapse toggle */}
        <div style={{
          padding: '10px 18px', borderTop: '1px solid rgba(0,229,255,0.08)',
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <Tooltip title={collapsed ? 'Expand 展開' : 'Collapse 收起'}>
            <Button type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{ fontSize: 15, width: 30, height: 30, color: token.colorTextSecondary }}
            />
          </Tooltip>
          {!collapsed && <Text style={{ fontSize: 12, color: token.colorTextSecondary }}>Collapse 收起</Text>}
        </div>

        {/* Theme toggle */}
        <div style={{
          padding: '8px 18px 14px 18px',
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <span style={{ fontSize: 16 }}>{themeMode === 'dark' ? '🌙' : '☀️'}</span>
          {!collapsed && <Text style={{ fontSize: 12, flex: 1, color: token.colorTextSecondary }}>{themeMode === 'dark' ? 'Midnight 午夜' : 'Daylight 白晝'}</Text>}
          <Switch size="small" checked={themeMode === 'dark'} onChange={onToggleTheme} />
        </div>
      </div>

      {/* Main content */}
      <div style={{ flex: 1, overflow: 'auto', background: token.colorBgLayout }}>
        <div className="tool-page" key={activeKey} style={{ padding: 28, maxWidth: 1280, margin: '0 auto' }}>
          {activeKey && PAGE_MAP[activeKey] ? (
            (() => { const Comp = PAGE_MAP[activeKey]; return <Comp key={activeKey} /> })()
          ) : (
            <div style={{ textAlign: 'center', padding: 80, opacity: 0.4 }}>
              <HomeOutlined style={{ fontSize: 48 }} />
              <div style={{ marginTop: 16, fontSize: 16 }}>Select a tool from the sidebar 請從側邊欄選擇工具</div>
            </div>
          )}
        </div>
      </div>

      {/* Command palette */}
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />

      {/* AI Chat */}
      <AiChat open={chatOpen} onClose={() => setChatOpen(false)} />

      {/* AI floating button */}
      <div style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1000 }}>
        <Tooltip title="AI Assistant">
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
        </Tooltip>
      </div>
    </div>
  )
}

export default ToolLayout
