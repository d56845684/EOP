'use client'

import { useEffect, useRef, useCallback } from 'react'

const IDLE_TIMEOUT_MS = 10 * 60 * 1000 // 10 分鐘
const ACTIVITY_EVENTS = ['mousedown', 'keydown', 'scroll', 'touchstart', 'pointermove'] as const

/**
 * 閒置超時 hook — 使用者在後台畫面靜置超過 10 分鐘自動登出
 *
 * 雙層保障：
 * 1. setTimeout 在活躍 tab 精確觸發
 * 2. visibilitychange 在 tab 恢復時立即檢查（瀏覽器會節流背景 tab 的 timer）
 */
export function useIdleTimeout(onTimeout: () => void) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastActivityRef = useRef(Date.now())
  const callbackRef = useRef(onTimeout)
  callbackRef.current = onTimeout

  const resetTimer = useCallback(() => {
    lastActivityRef.current = Date.now()
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      callbackRef.current()
    }, IDLE_TIMEOUT_MS)
  }, [])

  useEffect(() => {
    resetTimer()

    const activityHandler = () => resetTimer()
    for (const evt of ACTIVITY_EVENTS) {
      window.addEventListener(evt, activityHandler, { passive: true })
    }

    // 背景 tab 恢復時，瀏覽器可能已節流 setTimeout，立即補檢查
    const visibilityHandler = () => {
      if (document.visibilityState === 'visible') {
        const elapsed = Date.now() - lastActivityRef.current
        if (elapsed >= IDLE_TIMEOUT_MS) {
          callbackRef.current()
        } else {
          // 重置 timer 為剩餘時間
          if (timerRef.current) clearTimeout(timerRef.current)
          timerRef.current = setTimeout(() => {
            callbackRef.current()
          }, IDLE_TIMEOUT_MS - elapsed)
        }
      }
    }
    document.addEventListener('visibilitychange', visibilityHandler)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
      for (const evt of ACTIVITY_EVENTS) {
        window.removeEventListener(evt, activityHandler)
      }
      document.removeEventListener('visibilitychange', visibilityHandler)
    }
  }, [resetTimer])
}
