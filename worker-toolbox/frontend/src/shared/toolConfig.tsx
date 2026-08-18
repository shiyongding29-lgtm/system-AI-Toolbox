import type React from 'react'

export interface ToolConfig {
  key: string
  title: string
  sub: string
  icon: React.ReactNode
  color: string
  group: 'basic' | 'smart'
}

export const TOOL_LABELS: Record<string, string> = {
  'translation-assistant': 'Translation 翻譯', 'email-doc': 'Email 郵件', 'todo-extraction': 'Todo Extract 待辦提取',
  'ppt-outline': 'PPT Outline 簡報', 'weekly-report': 'Weekly Report 週報', 'document-summary': 'Doc Summary 摘要',
  'info-extraction': 'Info Extract 資訊提取', 'meeting-recorder': 'Meeting 會議', 'rag-qa': 'Knowledge Q&A 知識庫',
  'deep-research': 'Deep Research 深研', 'task-planning': 'Task Planner 規劃', 'document-comparison': 'Doc Compare 對比',
  'data-analysis': 'Data Analysis 分析', 'multi-source-reader': 'Multi-Source 多源', 'mindmap': 'Mind Map 思維導圖',
  'spreadsheet': 'Spreadsheet 表格', 'pomodoro': 'Pomodoro 番茄',
  'todos': 'Todo List 待辦', 'history': 'History 歷史',
  'image-analyzer': 'Image Analyzer 圖片分析', 'chart-generator': 'Chart Generator 圖表生成',
  'table-generator': 'Table Generator 表格生成', 'pdf-toolkit': 'PDF Toolkit PDF工具', 'sentiment-analyzer': 'Sentiment 情感分析',
  'file-converter': 'File Converter 文件轉換', 'web-scraper': 'Web Scraper 網頁抓取', 'qr-generator': 'QR Generator 二維碼',
  'workflow': 'AI Workflow 智能工作流', 'robot': 'Scheduled Agent 定時智能體',
  'code-tools': 'Smart Tools 智能小工具', 'weather': 'Weather 天氣查詢',
  'exchange-rate': 'Exchange Rate 匯率查詢', 'stock': 'Stock Quote 股價查詢',
  'stock-predictor': 'Stock Predict 股票預測',
  'fruit-classifier': 'Fruit Classify 水果識別',
  'spam-classifier': 'Spam Detect 垃圾郵件檢測',
  'priority-classifier': 'Task Priority 任務優先級',
  'delay-risk': 'Delay Risk 延期風險檢測',
  'attrition-risk': 'Attrition Risk 離職風險預測',
  'anomaly-detector': 'Anomaly Detect 異常員工識別',
  'skills': 'Skills 技能库',
}

export const TOOL_COLORS: Record<string, string> = {
  'meeting-recorder': '#6366f1', 'document-summary': '#3b82f6', 'email-doc': '#06b6d4',
  'translation-assistant': '#8b5cf6', 'weekly-report': '#f59e0b', 'ppt-outline': '#ef4444',
  'todo-extraction': '#10b981', 'info-extraction': '#0ea5e9', 'rag-qa': '#f97316',
  'deep-research': '#14b8a6', 'task-planning': '#e11d48', 'document-comparison': '#a855f7',
  'data-analysis': '#3b5ccc', 'multi-source-reader': '#65a30d', 'mindmap': '#ec4899',
  'spreadsheet': '#22c55e', 'pomodoro': '#f43f5e', 'todos': '#10b981', 'history': '#f59e0b',
  'image-analyzer': '#ec4899', 'chart-generator': '#22c55e',
  'table-generator': '#3b82f6', 'pdf-toolkit': '#ef4444', 'sentiment-analyzer': '#8b5cf6',
  'file-converter': '#6366f1', 'web-scraper': '#f97316', 'qr-generator': '#6366f1',
  'workflow': '#00e5ff', 'robot': '#7c3aed',
  'code-tools': '#22c55e', 'weather': '#06b6d4', 'exchange-rate': '#14b8a6', 'stock': '#ef4444',
  'stock-predictor': '#f97316',
  'fruit-classifier': '#22c55e',
  'spam-classifier': '#ef4444',
  'priority-classifier': '#8b5cf6',
  'delay-risk': '#f97316',
  'attrition-risk': '#14b8a6',
  'anomaly-detector': '#f59e0b',
  'skills': '#00e5ff',
}
