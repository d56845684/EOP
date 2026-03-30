'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import { lineApi, LineBindingAdminItem } from '@/lib/api/line'
import { MessageSquare, Send, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import DashboardLayout from '@/components/DashboardLayout'

const CHANNELS = ['student', 'teacher', 'employee'] as const
const channelLabels: Record<string, string> = {
  student: '學生',
  teacher: '老師',
  employee: '員工',
}

interface SendResult {
  lineUserId: string
  name: string
  success: boolean
  message: string
}

export default function LineTestingPage() {
  const { user } = useAuth()

  const [channel, setChannel] = useState<string>('student')
  const [items, setItems] = useState<LineBindingAdminItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [messageText, setMessageText] = useState('')
  const [sending, setSending] = useState(false)
  const [results, setResults] = useState<SendResult[]>([])

  const fetchBindings = useCallback(async () => {
    setLoading(true)
    setError(null)
    setSelected(new Set())
    setResults([])
    try {
      const res = await lineApi.listBindings(channel)
      setItems(res.items || [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '載入失敗')
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [channel])

  useEffect(() => {
    fetchBindings()
  }, [fetchBindings])

  const toggleSelect = (lineUserId: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(lineUserId)) {
        next.delete(lineUserId)
      } else {
        next.add(lineUserId)
      }
      return next
    })
  }

  const toggleAll = () => {
    if (selected.size === items.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(items.map((i) => i.line_user_id)))
    }
  }

  const handleSend = async () => {
    if (!messageText.trim() || selected.size === 0) return
    setSending(true)
    setResults([])

    const selectedItems = items.filter((i) => selected.has(i.line_user_id))
    const newResults: SendResult[] = []

    for (const item of selectedItems) {
      try {
        const res = await lineApi.sendMessage(item.line_user_id, messageText.trim(), channel)
        newResults.push({
          lineUserId: item.line_user_id,
          name: item.line_display_name || item.name || item.email || item.line_user_id,
          success: res.success,
          message: res.message,
        })
      } catch (e: unknown) {
        newResults.push({
          lineUserId: item.line_user_id,
          name: item.line_display_name || item.name || item.email || item.line_user_id,
          success: false,
          message: e instanceof Error ? e.message : '發送失敗',
        })
      }
      setResults([...newResults])
    }

    setSending(false)
  }

  return (
    <DashboardLayout>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <MessageSquare className="w-6 h-6 text-green-600" />
          <h1 className="text-2xl font-bold text-gray-900">LINE 訊息測試</h1>
        </div>

        {/* Channel Tabs */}
        <div className="flex gap-2 mb-6">
          {CHANNELS.map((ch) => (
            <button
              key={ch}
              onClick={() => setChannel(ch)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                channel === ch
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {channelLabels[ch]}頻道
            </button>
          ))}
        </div>

        {/* User Table */}
        <div className="bg-white rounded-lg border border-gray-200 mb-6">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <span className="text-sm text-gray-500">
              {channelLabels[channel]}頻道綁定用戶（{items.length} 人）
            </span>
            {items.length > 0 && (
              <button
                onClick={toggleAll}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                {selected.size === items.length ? '取消全選' : '全選'}
              </button>
            )}
          </div>

          {loading ? (
            <div className="p-8 text-center text-gray-400">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
              載入中...
            </div>
          ) : error ? (
            <div className="p-8 text-center text-red-500">{error}</div>
          ) : items.length === 0 ? (
            <div className="p-8 text-center text-gray-400">此頻道沒有綁定用戶</div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-gray-500 uppercase border-b border-gray-100">
                  <th className="px-4 py-2 w-10"></th>
                  <th className="px-4 py-2">LINE 名稱</th>
                  <th className="px-4 py-2">系統名稱</th>
                  <th className="px-4 py-2">Email</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.line_user_id}
                    className={`border-b border-gray-50 cursor-pointer hover:bg-gray-50 ${
                      selected.has(item.line_user_id) ? 'bg-green-50' : ''
                    }`}
                    onClick={() => toggleSelect(item.line_user_id)}
                  >
                    <td className="px-4 py-2">
                      <input
                        type="checkbox"
                        checked={selected.has(item.line_user_id)}
                        onChange={() => toggleSelect(item.line_user_id)}
                        className="rounded border-gray-300"
                      />
                    </td>
                    <td className="px-4 py-2 text-sm font-medium text-gray-900">
                      {item.line_display_name || '-'}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-600">
                      {item.name || '-'}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-500">
                      {item.email || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Message Input */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">訊息內容</label>
          <textarea
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            rows={3}
            placeholder="輸入要發送的 LINE 訊息..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 resize-none"
          />
          <div className="flex items-center justify-between mt-3">
            <span className="text-sm text-gray-500">
              已選 {selected.size} 人
            </span>
            <button
              onClick={handleSend}
              disabled={sending || selected.size === 0 || !messageText.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {sending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              發送
            </button>
          </div>
        </div>

        {/* Send Results */}
        {results.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-3">發送結果</h3>
            <div className="space-y-2">
              {results.map((r) => (
                <div
                  key={r.lineUserId}
                  className={`flex items-center gap-2 px-3 py-2 rounded text-sm ${
                    r.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                  }`}
                >
                  {r.success ? (
                    <CheckCircle className="w-4 h-4 flex-shrink-0" />
                  ) : (
                    <XCircle className="w-4 h-4 flex-shrink-0" />
                  )}
                  <span className="font-medium">{r.name}</span>
                  <span className="text-gray-500">— {r.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
