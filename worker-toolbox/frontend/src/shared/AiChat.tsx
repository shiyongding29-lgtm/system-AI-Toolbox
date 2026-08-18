import { useState, useRef, useEffect, useCallback } from 'react'
import { Button, Input, Typography, Spin, message, Tag } from 'antd'
import { SendOutlined, CloseOutlined, SettingOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import http from '../services/http'
import AgentStepsTimeline, { type AgentStep } from './AgentStepsTimeline'
import MemoryPanel from './MemoryPanel'

const { Text } = Typography

// ── Action config — maps tool types to URL params ──
const TOOL_PARAMS: Record<string, { route: string; params?: string[] }> = {
  'todo':           { route: '',          params: ['task','deadline','owner'] },
  'pomodoro':       { route: 'pomodoro', params: ['work'] },
  'email':          { route: 'email-doc', params: ['to','hint','mode','style','subject'] },
  'translation':    { route: 'translation-assistant', params: ['text','mode'] },
  'research':       { route: 'deep-research', params: ['topic'] },
  'ppt':            { route: 'ppt-outline', params: ['slides','style'] },
  'summary':        { route: 'document-summary' },
  'mindmap':        { route: 'mindmap' },
  'data':           { route: 'data-analysis' },
  'spreadsheet':    { route: 'spreadsheet' },
  'meeting':        { route: 'meeting-recorder' },
  'weekly_report':  { route: 'weekly-report', params: ['auto'] },
  'task_planning':  { route: 'task-planning' },
  'image-analyzer': { route: 'image-analyzer' },
  'chart-generator':{ route: 'chart-generator' },
  'doc-compare':    { route: 'document-comparison' },
  'multi-source':   { route: 'multi-source-reader' },
  'rag-qa':         { route: 'rag-qa' },
  'info-extraction': { route: 'info-extraction' },
  'table-generator': { route: 'table-generator' },
  'pdf-toolkit': { route: 'pdf-toolkit' },
  'sentiment-analyzer': { route: 'sentiment-analyzer' },
  'file-converter': { route: 'file-converter' },
  'todo-add': { route: '' },
  'web-scraper': { route: 'web-scraper' },
  'qr-generator': { route: 'qr-generator' },
  // 新工具
  'calculator': { route: 'code-tools', params: ['text'] },
  'date_calc': { route: 'code-tools', params: ['text'] },
  'unit_converter': { route: 'code-tools', params: ['text'] },
  'word_counter': { route: 'code-tools', params: ['text'] },
  'json_formatter': { route: 'code-tools', params: ['text'] },
  'weather': { route: 'weather', params: ['text'] },
  'exchange_rate': { route: 'exchange-rate', params: ['text'] },
  'stock_quote': { route: 'stock', params: ['text'] },
  'stock_predictor': { route: 'stock-predictor', params: ['text'] },
  'fruit_classifier': { route: 'fruit-classifier', params: ['text'] },
  'spam_classifier': { route: 'spam-classifier', params: ['text'] },
  'priority_classifier': { route: 'priority-classifier', params: [] },
  'delay_risk': { route: 'delay-risk', params: [] },
  'attrition_risk': { route: 'attrition-risk', params: [] },
  'anomaly_detector': { route: 'anomaly-detector', params: [] },
}

interface Action { type: string; label: string; run: () => Promise<void> }
interface Message { role: 'user' | 'assistant'; content: string; actions?: Action[]; steps?: AgentStep[]; degraded?: boolean }

const SESSION_KEY = 'agent-session-key'

function buildActions(parsed: any, navigate: ReturnType<typeof useNavigate>, onClose: () => void, originalText: string): Action[] {
  let { tool, params = {} } = parsed
  const cfg = TOOL_PARAMS[tool]
  if (!cfg || !cfg.route) {
    // todo — special case: create directly via API
    if (tool === 'todo') {
      let task = params.task || originalText
      task = task.replace(/提醒我|记得|别忘了|帮我记|帮我记录|帮我.*记/g, '').replace(/[：:，,\s]+/g, ' ').trim()
      task = task.replace(/明天|后天|今天/g, '').replace(/\s+/g, ' ').trim() || originalText

      const today = new Date()
      let deadline = params.deadline || ''
      if (!deadline) {
        if (/后天/.test(originalText)) { const t = new Date(today); t.setDate(t.getDate()+2); deadline = `${t.getFullYear()}-${String(t.getMonth()+1).padStart(2,'0')}-${String(t.getDate()).padStart(2,'0')}` }
        else if (/明天/.test(originalText)) { const t = new Date(today); t.setDate(t.getDate()+1); deadline = `${t.getFullYear()}-${String(t.getMonth()+1).padStart(2,'0')}-${String(t.getDate()).padStart(2,'0')}` }
        else if (/今天/.test(originalText)) { deadline = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}` }
      }

      const dueLabel = deadline ? ` 📅 ${deadline}` : ''
      return [{
        type: 'create_todo', label: `✅ 添加待办: ${task}${dueLabel}`,
        run: async () => {
          try {
            await http.post('/api/todos', { task, owner: '', deadline, priority: 2, source: 'ai-assistant' })
            message.success(`已添加: ${task}`)
          } catch { message.error('添加失败') }
        },
      }]
    }
    return []
  }

  const qs: string[] = []
  if (tool === 'pomodoro' && !params.work) {
    const m = originalText.match(/(\d+)\s*(分钟|分|min)/i)
    if (m) params = { ...params, work: parseInt(m[1]) }
  }
  if (tool === 'ppt' && !params.slides) {
    const m = originalText.match(/(\d+)\s*(页|张|slides?|pages?)/i)
    if (m) params = { ...params, slides: parseInt(m[1]) }
  }
  ;(cfg.params || []).forEach((k: string) => { if (params[k] != null) qs.push(`${k}=${encodeURIComponent(String(params[k]))}`) })
  qs.push(`${tool === 'email' ? 'full' : 'topic'}=${encodeURIComponent(originalText.substring(0, 200))}`)

  const labelMap: Record<string, string> = {
    'pomodoro': `🍅 ${params.work || 25} 分钟番茄钟`,
    'email': `✉️ 写邮件`,
    'translation': `🌐 翻译`,
    'research': `🔍 调研: ${params.topic || ''}`,
    'ppt': `📽️ ${params.slides || ''} 页 PPT`,
    'meeting': `🎙️ 会议记录`,
    'summary': `📄 文档摘要`,
    'todo': `✅ 添加待办`,
    'mindmap': `🧠 思维导图`,
    'data': `📈 数据分析`,
    'spreadsheet': `📊 智能表格`,
    'weekly_report': `📋 周报`,
    'task_planning': `🗓️ 任务规划`,
    'image-analyzer': `🖼️ 图片分析`,
    'chart-generator': `📊 图表生成`,
    'doc-compare': `⚖️ 文档对比`,
    'multi-source': `📖 多源阅读`,
    'rag-qa': `📚 知识库问答`,
    'info-extraction': `📋 信息提取`,
    'table-generator': `📋 表格生成`,
    'pdf-toolkit': `📑 PDF工具`,
    'sentiment-analyzer': `💬 情感分析`,
    'file-converter': `🔄 文件轉換`,
    'todo-add': `✅ 待辦列表`,
    'web-scraper': `🕷️ 網頁抓取`,
    'qr-generator': `📱 QR二維碼`,
    'calculator': `🧮 计算器`,
    'date_calc': `📅 日期计算`,
    'unit_converter': `⚖️ 单位换算`,
    'word_counter': `🔢 字数统计`,
    'json_formatter': `🧾 JSON格式化`,
    'weather': `🌤️ 天气查询`,
    'exchange_rate': `💱 汇率查询`,
    'stock_quote': `📈 股价查询`,
  }

  return [{
    type: 'open_tool', label: labelMap[tool] || `✅ 打开 ${cfg.route}`,
    run: async () => { navigate(`/tools/${cfg.route}?${qs.join('&')}`); onClose() },
  }]
}

// Agent final.actions → 前端 Action
function agentActions(raw: any[], navigate: ReturnType<typeof useNavigate>, onClose: () => void): Action[] {
  return (raw || []).map((a: any) => ({
    type: a.type, label: a.label,
    run: async () => {
      if (a.type === 'open_tool') {
        const qs = Object.entries(a.params || {}).map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join('&')
        navigate(`/tools/${a.route}${qs ? '?' + qs : ''}`); onClose()
      } else if (a.type === 'open_workflow') {
        localStorage.setItem('pending_workflow', JSON.stringify(a.plan || {}))
        navigate('/tools/workflow?load=ai-plan'); onClose()
      }
    },
  }))
}

// ── Fallback parser (LLM unavailable) ──
function fallbackParse(text: string): { tool: string; params: Record<string, string>; reply: string } {
  const today = new Date()
  const tmr = new Date(today); tmr.setDate(tmr.getDate() + 1)
  const yyyy = String(tmr.getFullYear()), mm = String(tmr.getMonth() + 1).padStart(2, '0'), dd = String(tmr.getDate()).padStart(2, '0')

  if (/提醒我|记得|别忘了|帮我记|创建待办|添加待办/.test(text)) {
    let task = text.replace(/提醒我|记得|别忘了|帮我记|创建(?:一个)?待办|添加(?:一个)?待办/g, '').replace(/^要|^去|^给|^的|^了|^做|^：|^:/, '').trim()
    let deadline = ''
    if (/明天/.test(text)) deadline = `${yyyy}-${mm}-${dd}`
    else if (/后天/.test(text)) { const d2 = new Date(today); d2.setDate(d2.getDate()+2); deadline = `${d2.getFullYear()}-${String(d2.getMonth()+1).padStart(2,'0')}-${String(d2.getDate()).padStart(2,'0')}` }
    else if (/今天/.test(text)) deadline = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`
    return { tool: 'todo', params: { task: task.substring(0, 200), deadline }, reply: `好的，帮你记下了 📋` }
  }
  const pm = text.match(/(\d+)\s*(分钟|分|min)/i)
  if (pm && /番茄|pomodoro|专注|计时|timer|focus/.test(text.toLowerCase())) return { tool: 'pomodoro', params: { work: String(parseInt(pm[1])) }, reply: `帮你打开 ${pm[1]} 分钟番茄钟 🍅` }
  if (/写.*邮件|发.*邮件|请假.*邮件|给.*写/.test(text)) {
    const to = (text.match(/(?:给|帮)\s*(\S{1,6})\s*(?:写|发|回)/) || [])[1] || ''
    return { tool: 'email', params: { to }, reply: `帮你${to ? '给' + to : ''}写邮件 ✉️` }
  }
  const tm = text.match(/(?:翻译|翻译一下)\s*[:：]?\s*(.+)/i)
  if (tm) return { tool: 'translation', params: { text: tm[1].trim(), mode: 'translate_zh_en' }, reply: '帮你翻译 ✨' }
  const rm = text.match(/(?:调研|帮我搜|搜索|帮我查|了解)\s*(.+)/i)
  if (rm) return { tool: 'research', params: { topic: rm[1].trim() }, reply: `帮你调研「${rm[1].trim().substring(0, 30)}」🔍` }
  let slides = (text.match(/(\d+)\s*(页|张|slides?|pages?)/i) || [])[1]
  if (/ppt|演示|幻灯片|简报|presentation/.test(text.toLowerCase())) return { tool: 'ppt', params: { slides: slides || '0' }, reply: '帮你生成 PPT 大纲 📽️' }

  return { tool: 'none', params: {}, reply: '试试说：\n• "提醒我明天交报告"\n• "帮我算 (8+2)*5/2"\n• "北京今天天气"\n• "总结这段文字并提取待办"' }
}

// ── Component ──
export default function AiChat({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const [memoryOpen, setMemoryOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<any>(null)
  const pollTimerRef = useRef<any>(null)
  const sessionKeyRef = useRef<string>(localStorage.getItem(SESSION_KEY) || '')

  useEffect(() => {
    if (open) {
      setMessages([{
        role: 'assistant',
        content: '你好！我是你的 AI Agent 助手，可以连续对话、多步骤执行、记住你的偏好。\n\n• "提醒我明天交报告"\n• "帮我算 (8+2)*5/2"\n• "北京今天天气"\n• "总结这段文字并提取待办"\n• "记住：常用负责人是张三"\n\n快请求秒回，复杂任务会展示执行过程 👇',
      }])
      setInput(''); setThinking(false)
      setTimeout(() => inputRef.current?.focus(), 200)
    }
    return () => { if (pollTimerRef.current) clearInterval(pollTimerRef.current) }
  }, [open])

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const handleSend = useCallback(() => {
    const text = input.trim()
    if (!text || thinking) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: text }, { role: 'assistant', content: '', steps: [] }])
    setThinking(true)

    http.post('/api/agent/chat', { session_key: sessionKeyRef.current || undefined, text })
      .then((res: any) => {
        const data = res.code === 0 ? res.data : null
        if (data?.session_key) {
          sessionKeyRef.current = data.session_key
          localStorage.setItem(SESSION_KEY, data.session_key)
        }

        // ── 快路径（0 LLM）──
        if (data?.fast) {
          setThinking(false)
          const parsed = data.fast
          if (parsed.type === 'workflow' && parsed.plan) {
            const nodes = parsed.plan.nodes || []
            const nodeList = nodes.map((n: any) => n.label).join(' → ')
            setMessages(prev => prev.map((m, i) => i === prev.length - 1 ? {
              role: 'assistant' as const,
              content: `🔀 **${parsed.plan.title || 'Workflow'}**\n${nodeList}${parsed.source === 'plan_cache' || parsed.source === 'plan_cache_exact' ? '\n\n⚡ 命中历史方案，0 LLM' : ''}`,
              actions: [
                { type: 'open_workflow', label: '✅ 确认执行', run: async () => { localStorage.setItem('pending_workflow', JSON.stringify(parsed.plan)); navigate('/tools/workflow?load=ai-plan'); onClose() } },
                { type: 'open_workflow_edit', label: '✏️ 修改', run: async () => { localStorage.setItem('pending_workflow', JSON.stringify(parsed.plan)); navigate('/tools/workflow?load=ai-plan'); onClose() } },
              ],
            } : m))
            return
          }
          const actions = buildActions(parsed, navigate, onClose, text)
          if (actions.length === 0) {
            setMessages(prev => prev.map((m, i) => i === prev.length - 1 ? { role: 'assistant' as const, content: parsed.reply || '好的' } : m))
          } else {
            setMessages(prev => prev.map((m, i) => i === prev.length - 1 ? { role: 'assistant' as const, content: parsed.reply || '好的', actions } : m))
          }
          return
        }

        // ── Agent 路径：轮询状态 ──
        if (data?.turn_id) {
          const turnId = data.turn_id
          pollTimerRef.current = setInterval(async () => {
            try {
              const r: any = await http.get(`/api/agent/status/${turnId}`)
              if (r.code !== 0 || !r.data) return
              const turn = r.data
              setMessages(prev => prev.map((m, i) => i === prev.length - 1
                ? { ...m, steps: turn.steps || [] }
                : m))
              if (turn.status === 'done' || turn.status === 'error' || turn.status === 'need_input') {
                clearInterval(pollTimerRef.current)
                setThinking(false)
                const final = turn.final || {}
                setMessages(prev => prev.map((m, i) => i === prev.length - 1
                  ? {
                      role: 'assistant' as const,
                      content: final.content || '（无输出）',
                      steps: turn.steps || [],
                      actions: agentActions(final.actions || [], navigate, onClose),
                      degraded: final.degraded,
                    }
                  : m))
              }
            } catch { /* 轮询失败继续 */ }
          }, 1500)
          return
        }

        // 异常：fallback
        setThinking(false)
        const fb = fallbackParse(text)
        const actions = buildActions(fb, navigate, onClose, text)
        setMessages(prev => prev.map((m, i) => i === prev.length - 1 ? { role: 'assistant' as const, content: fb.reply, actions: actions.length ? actions : undefined } : m))
      })
      .catch(() => {
        setThinking(false)
        const fb = fallbackParse(text)
        const actions = buildActions(fb, navigate, onClose, text)
        setMessages(prev => prev.map((m, i) => i === prev.length - 1 ? { role: 'assistant' as const, content: fb.reply, actions: actions.length ? actions : undefined } : m))
      })
  }, [input, thinking, navigate, onClose])

  if (!open) return null

  return (
    <div style={{ position: 'fixed', bottom: 90, right: 24, zIndex: 1001, width: 500, maxHeight: 680, borderRadius: 20, overflow: 'hidden', background: 'linear-gradient(180deg, rgba(10,15,40,0.98), rgba(13,17,37,0.95))', backdropFilter: 'blur(24px) saturate(180%)', WebkitBackdropFilter: 'blur(24px) saturate(180%)', boxShadow: '0 0 60px rgba(0,229,255,0.1), 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(0,229,255,0.08)', border: '1px solid rgba(0,229,255,0.12)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 12, background: 'linear-gradient(135deg, rgba(0,229,255,0.08), rgba(124,58,237,0.06))', borderBottom: '1px solid rgba(0,229,255,0.08)' }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #00e5ff, #7c3aed)', fontSize: 16, fontWeight: 900, color: '#fff', boxShadow: '0 0 16px rgba(0,229,255,0.3)' }}>AI</div>
        <div style={{ flex: 1 }}>
          <Text strong style={{ color: '#e0e8ff', fontSize: 14, display: 'block' }}>AI Agent</Text>
          <Text style={{ color: 'rgba(255,255,255,0.4)', fontSize: 11 }}>感知 · 规划 · 执行 · 反思 · 记忆</Text>
        </div>
        <Button type="text" size="small" icon={<SettingOutlined />} onClick={() => setMemoryOpen(true)} style={{ color: 'rgba(255,255,255,0.3)' }} />
        <Button type="text" size="small" icon={<CloseOutlined />} onClick={onClose} style={{ color: 'rgba(255,255,255,0.3)', fontSize: 14 }} />
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '16px 18px', maxHeight: 460, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{ maxWidth: '92%', padding: '10px 16px', borderRadius: 16, fontSize: 13, lineHeight: 1.7, background: msg.role === 'user' ? 'linear-gradient(135deg, #00e5ff, #7c3aed)' : 'rgba(255,255,255,0.04)', color: msg.role === 'user' ? '#0a0e27' : '#c8d6e5', borderBottomRightRadius: msg.role === 'user' ? 4 : 16, borderBottomLeftRadius: msg.role === 'assistant' ? 4 : 16, border: msg.role === 'assistant' ? '1px solid rgba(255,255,255,0.06)' : 'none', whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontWeight: msg.role === 'user' ? 600 : 400 }}>
              {msg.content}
              {msg.degraded && <div style={{ marginTop: 6 }}><Tag color="orange" style={{ fontSize: 10, borderRadius: 100 }}>⚠️ 部分降级</Tag></div>}
            </div>
            {msg.steps && msg.steps.length > 0 && msg.role === 'assistant' && (
              <div style={{ maxWidth: '92%', width: '100%', marginTop: 4, padding: '4px 10px', borderRadius: 10, background: 'rgba(0,229,255,0.03)', border: '1px solid rgba(0,229,255,0.06)' }}>
                <AgentStepsTimeline steps={msg.steps} />
              </div>
            )}
            {msg.actions?.map((act, j) => (
              <Button key={j} size="small" onClick={act.run} style={{ borderRadius: 12, textAlign: 'left', fontSize: 12, height: 'auto', padding: '8px 14px', marginTop: 6, ...(j === 0 ? { background: 'linear-gradient(135deg, #10b981, #059669)', border: 'none', color: '#fff', fontWeight: 600 } : { background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)', color: '#c8d6e5' }) }}>
                {act.label}
              </Button>
            ))}
          </div>
        ))}
        {thinking && <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', opacity: 0.5 }}><Spin size="small" /><Text style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12 }}>Agent 思考中...</Text></div>}
        <div ref={messagesEndRef} />
      </div>

      <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(0,229,255,0.08)', display: 'flex', gap: 8, alignItems: 'center', background: 'rgba(0,229,255,0.02)' }}>
        <Input ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }} placeholder="输入你的需求..." variant="borderless" disabled={thinking} style={{ fontSize: 13, color: '#c8d6e5' }} />
        <Button type="primary" shape="circle" size="small" icon={<SendOutlined />} onClick={handleSend} loading={thinking} disabled={!input.trim()} style={{ flexShrink: 0, borderRadius: '50%', width: 36, height: 36, background: input.trim() ? 'linear-gradient(135deg, #00e5ff, #7c3aed)' : 'rgba(255,255,255,0.06)', border: 'none', boxShadow: input.trim() ? '0 0 12px rgba(0,229,255,0.3)' : 'none' }} />
      </div>

      <MemoryPanel open={memoryOpen} onClose={() => setMemoryOpen(false)} />
    </div>
  )
}
