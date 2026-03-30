'use client'

import React from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface ErrorBoundaryProps {
  children: React.ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] gap-4 p-8">
          <div className="w-14 h-14 rounded-full bg-amber-50 flex items-center justify-center">
            <AlertTriangle className="w-7 h-7 text-amber-500" />
          </div>
          <h2 className="text-lg font-semibold text-slate-800">頁面發生錯誤</h2>
          <p className="text-sm text-slate-500 text-center max-w-md">
            抱歉，此頁面發生了非預期的錯誤。請嘗試重新整理頁面。
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null })
              window.location.reload()
            }}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg
              bg-primary-500 text-white hover:bg-primary-600 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            重新整理
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
