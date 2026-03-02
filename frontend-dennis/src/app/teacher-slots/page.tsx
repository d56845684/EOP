'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import {
    teacherSlotsApi,
    TeacherSlot,
    CreateTeacherSlotData,
    BatchCreateTeacherSlotData,
    BatchDeleteTeacherSlotData,
    BatchUpdateTeacherSlotData,
    BatchDeleteByIdsData,
    BatchUpdateByIdsData,
    UpdateTeacherSlotData,
    TeacherOption,
    TeacherContractOption
} from '@/lib/api/teacherSlots'
import { Plus, Pencil, Trash2, Search, X, Calendar, Clock, CheckCircle, XCircle, AlertCircle, Layers, RefreshCw } from 'lucide-react'
import DashboardLayout from '@/components/DashboardLayout'

const weekdayLabels = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']

export default function TeacherSlotsPage() {
    const { user, profile } = useAuth()

    // State
    const [slots, setSlots] = useState<TeacherSlot[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [filterTeacherId, setFilterTeacherId] = useState('')
    const [dateFrom, setDateFrom] = useState('')
    const [dateTo, setDateTo] = useState('')
    const [filterIsAvailable, setFilterIsAvailable] = useState<string>('')
    const [filterIsBooked, setFilterIsBooked] = useState<string>('')

    // Pagination
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const perPage = 20

    // Options
    const [teacherOptions, setTeacherOptions] = useState<TeacherOption[]>([])
    const [contractOptions, setContractOptions] = useState<TeacherContractOption[]>([])
    const [myTeacherId, setMyTeacherId] = useState<string | null>(null)

    // Modal state
    const [showModal, setShowModal] = useState(false)
    const [modalMode, setModalMode] = useState<'create' | 'batch' | 'edit' | 'batchDelete' | 'batchUpdate'>('create')
    const [editingSlot, setEditingSlot] = useState<TeacherSlot | null>(null)
    const [formError, setFormError] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    // Form data for single create/edit
    const [formTeacher, setFormTeacher] = useState('')
    const [formContract, setFormContract] = useState('')
    const [formDate, setFormDate] = useState('')
    const [formStartTime, setFormStartTime] = useState('')
    const [formEndTime, setFormEndTime] = useState('')
    const [formIsAvailable, setFormIsAvailable] = useState(true)
    const [formNotes, setFormNotes] = useState('')

    // Form data for batch create/delete/update
    const [formStartDate, setFormStartDate] = useState('')
    const [formEndDate, setFormEndDate] = useState('')
    const [formWeekdays, setFormWeekdays] = useState<number[]>([])

    // Form data for batch update (new times)
    const [formNewStartTime, setFormNewStartTime] = useState('')
    const [formNewEndTime, setFormNewEndTime] = useState('')

    // Delete confirmation
    const [deleteConfirm, setDeleteConfirm] = useState<TeacherSlot | null>(null)
    const [deleting, setDeleting] = useState(false)

    // Multi-select state
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
    const [showSelectedActionModal, setShowSelectedActionModal] = useState(false)
    const [selectedActionMode, setSelectedActionMode] = useState<'delete' | 'update'>('delete')
    const [processingSelected, setProcessingSelected] = useState(false)

    const isStaff = profile?.role === 'admin' || profile?.role === 'employee'
    const isTeacher = profile?.role === 'teacher'
    const canManage = isStaff || isTeacher

    // Load teacher options (staff only)
    useEffect(() => {
        const loadOptions = async () => {
            if (isStaff) {
                const res = await teacherSlotsApi.getTeacherOptions()
                if (res.data) setTeacherOptions(res.data)
            }
            if (isTeacher) {
                // Load teacher's own contracts
                const res = await teacherSlotsApi.getMyContracts()
                if (res.data) setContractOptions(res.data)
            }
        }
        if (profile) {
            loadOptions()
        }
    }, [profile, isStaff, isTeacher])

    // Fetch slots
    const fetchSlots = useCallback(async () => {
        setLoading(true)
        setError(null)

        const { data, error } = await teacherSlotsApi.list({
            page,
            per_page: perPage,
            teacher_id: filterTeacherId || undefined,
            date_from: dateFrom || undefined,
            date_to: dateTo || undefined,
            is_available: filterIsAvailable === '' ? undefined : filterIsAvailable === 'true',
            is_booked: filterIsBooked === '' ? undefined : filterIsBooked === 'true',
        })

        if (error) {
            setError(error.message)
        } else if (data) {
            setSlots(data.data)
            setTotalPages(data.total_pages)
            setTotal(data.total)
        }

        setLoading(false)
    }, [page, filterTeacherId, dateFrom, dateTo, filterIsAvailable, filterIsBooked])

    useEffect(() => {
        if (user) {
            fetchSlots()
        }
    }, [user, fetchSlots])

    // Modal handlers
    const openCreateModal = () => {
        setModalMode('create')
        setEditingSlot(null)
        setFormTeacher(isTeacher ? (myTeacherId || '') : '')
        setFormContract('')
        setFormDate('')
        setFormStartTime('')
        setFormEndTime('')
        setFormIsAvailable(true)
        setFormNotes('')
        setFormError(null)
        setShowModal(true)
    }

    const openBatchModal = () => {
        setModalMode('batch')
        setEditingSlot(null)
        setFormTeacher(isTeacher ? (myTeacherId || '') : '')
        setFormContract('')
        setFormStartDate('')
        setFormEndDate('')
        setFormWeekdays([])
        setFormStartTime('')
        setFormEndTime('')
        setFormNotes('')
        setFormError(null)
        setShowModal(true)
    }

    const openEditModal = (slot: TeacherSlot) => {
        setModalMode('edit')
        setEditingSlot(slot)
        setFormTeacher(slot.teacher_id)
        setFormContract(slot.teacher_contract_id || '')
        setFormDate(slot.slot_date)
        setFormStartTime(slot.start_time.substring(0, 5))
        setFormEndTime(slot.end_time.substring(0, 5))
        setFormIsAvailable(slot.is_available)
        setFormNotes(slot.notes || '')
        setFormError(null)
        setShowModal(true)
    }

    const closeModal = () => {
        setShowModal(false)
        setEditingSlot(null)
        setFormError(null)
    }

    const openBatchDeleteModal = () => {
        setModalMode('batchDelete')
        setEditingSlot(null)
        setFormTeacher(isTeacher ? (myTeacherId || '') : '')
        setFormStartDate('')
        setFormEndDate('')
        setFormWeekdays([])
        setFormStartTime('')
        setFormEndTime('')
        setFormError(null)
        setShowModal(true)
    }

    const openBatchUpdateModal = () => {
        setModalMode('batchUpdate')
        setEditingSlot(null)
        setFormTeacher(isTeacher ? (myTeacherId || '') : '')
        setFormStartDate('')
        setFormEndDate('')
        setFormWeekdays([])
        setFormStartTime('')
        setFormEndTime('')
        setFormNewStartTime('')
        setFormNewEndTime('')
        setFormIsAvailable(true)
        setFormNotes('')
        setFormError(null)
        setShowModal(true)
    }

    // Load contracts when teacher selected (staff mode)
    useEffect(() => {
        const loadContracts = async () => {
            if (isStaff && formTeacher) {
                // Fetch contracts for selected teacher
                const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/v1/bookings/options/teacher-contracts/${formTeacher}`, {
                    credentials: 'include'
                })
                if (response.ok) {
                    const result = await response.json()
                    setContractOptions(result.data || [])
                }
            }
        }
        loadContracts()
    }, [formTeacher, isStaff])

    // Form submit
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setFormError(null)
        setSubmitting(true)

        try {
            if (modalMode === 'create') {
                const createData: CreateTeacherSlotData = {
                    teacher_id: formTeacher,
                    teacher_contract_id: formContract || undefined,
                    slot_date: formDate,
                    start_time: formStartTime,
                    end_time: formEndTime,
                    is_available: formIsAvailable,
                    notes: formNotes || undefined,
                }

                const { data, error } = await teacherSlotsApi.create(createData)
                if (error) {
                    setFormError(error.message)
                } else {
                    closeModal()
                    fetchSlots()
                }
            } else if (modalMode === 'batch') {
                if (formWeekdays.length === 0) {
                    setFormError('請至少選擇一個星期')
                    setSubmitting(false)
                    return
                }

                const batchData: BatchCreateTeacherSlotData = {
                    teacher_id: formTeacher,
                    teacher_contract_id: formContract || undefined,
                    start_date: formStartDate,
                    end_date: formEndDate,
                    weekdays: formWeekdays,
                    start_time: formStartTime,
                    end_time: formEndTime,
                    notes: formNotes || undefined,
                }

                const { success, message, error } = await teacherSlotsApi.createBatch(batchData)
                if (error) {
                    setFormError(error.message)
                } else {
                    closeModal()
                    fetchSlots()
                }
            } else if (modalMode === 'batchDelete') {
                const batchDeleteData: BatchDeleteTeacherSlotData = {
                    teacher_id: formTeacher,
                    start_date: formStartDate,
                    end_date: formEndDate,
                    weekdays: formWeekdays.length > 0 ? formWeekdays : undefined,
                    start_time: formStartTime || undefined,
                    end_time: formEndTime || undefined,
                }

                const { success, message, error } = await teacherSlotsApi.deleteBatch(batchDeleteData)
                if (error) {
                    setFormError(error.message)
                } else {
                    closeModal()
                    fetchSlots()
                    if (message) {
                        setError(null)
                    }
                }
            } else if (modalMode === 'batchUpdate') {
                // Check if there's something to update
                if (!formNewStartTime && !formNewEndTime && formIsAvailable === undefined && !formNotes) {
                    setFormError('請至少指定一個要更新的內容')
                    setSubmitting(false)
                    return
                }

                const batchUpdateData: BatchUpdateTeacherSlotData = {
                    teacher_id: formTeacher,
                    start_date: formStartDate,
                    end_date: formEndDate,
                    weekdays: formWeekdays.length > 0 ? formWeekdays : undefined,
                    filter_start_time: formStartTime || undefined,
                    filter_end_time: formEndTime || undefined,
                    new_start_time: formNewStartTime || undefined,
                    new_end_time: formNewEndTime || undefined,
                    is_available: formIsAvailable,
                    notes: formNotes || undefined,
                }

                const { success, message, error } = await teacherSlotsApi.updateBatch(batchUpdateData)
                if (error) {
                    setFormError(error.message)
                } else {
                    closeModal()
                    fetchSlots()
                }
            } else if (editingSlot) {
                const updateData: UpdateTeacherSlotData = {}

                // Only include changed fields
                if (formContract !== (editingSlot.teacher_contract_id || '')) {
                    updateData.teacher_contract_id = formContract || undefined
                }
                if (!editingSlot.is_booked) {
                    // Can only update date/time if not booked
                    if (formDate !== editingSlot.slot_date) updateData.slot_date = formDate
                    if (formStartTime !== editingSlot.start_time.substring(0, 5)) updateData.start_time = formStartTime
                    if (formEndTime !== editingSlot.end_time.substring(0, 5)) updateData.end_time = formEndTime
                }
                if (formIsAvailable !== editingSlot.is_available) updateData.is_available = formIsAvailable
                if (formNotes !== (editingSlot.notes || '')) updateData.notes = formNotes

                const { data, error } = await teacherSlotsApi.update(editingSlot.id, updateData)
                if (error) {
                    setFormError(error.message)
                } else {
                    closeModal()
                    fetchSlots()
                }
            }
        } finally {
            setSubmitting(false)
        }
    }

    // Delete handler
    const handleDelete = async () => {
        if (!deleteConfirm) return
        setDeleting(true)

        const { success, error } = await teacherSlotsApi.delete(deleteConfirm.id)

        if (error) {
            setError(error.message)
        } else {
            setDeleteConfirm(null)
            fetchSlots()
        }

        setDeleting(false)
    }

    // Toggle weekday
    const toggleWeekday = (day: number) => {
        setFormWeekdays(prev =>
            prev.includes(day)
                ? prev.filter(d => d !== day)
                : [...prev, day].sort()
        )
    }

    const formatTime = (time: string) => {
        return time.substring(0, 5)
    }

    // Multi-select handlers
    const toggleSelectSlot = (slotId: string) => {
        setSelectedIds(prev => {
            const newSet = new Set(prev)
            if (newSet.has(slotId)) {
                newSet.delete(slotId)
            } else {
                newSet.add(slotId)
            }
            return newSet
        })
    }

    const toggleSelectAll = () => {
        if (selectedIds.size === slots.filter(s => !s.is_booked).length) {
            // Deselect all
            setSelectedIds(new Set())
        } else {
            // Select all non-booked slots
            setSelectedIds(new Set(slots.filter(s => !s.is_booked).map(s => s.id)))
        }
    }

    const clearSelection = () => {
        setSelectedIds(new Set())
    }

    const openSelectedDeleteModal = () => {
        setSelectedActionMode('delete')
        setFormError(null)
        setShowSelectedActionModal(true)
    }

    const openSelectedUpdateModal = () => {
        setSelectedActionMode('update')
        setFormNewStartTime('')
        setFormNewEndTime('')
        setFormIsAvailable(true)
        setFormNotes('')
        setFormError(null)
        setShowSelectedActionModal(true)
    }

    const handleSelectedAction = async () => {
        setProcessingSelected(true)
        setFormError(null)

        try {
            if (selectedActionMode === 'delete') {
                const { success, message, error } = await teacherSlotsApi.deleteByIds({
                    slot_ids: Array.from(selectedIds)
                })
                if (error) {
                    setFormError(error.message)
                } else {
                    setShowSelectedActionModal(false)
                    clearSelection()
                    fetchSlots()
                }
            } else {
                // Check if there's something to update
                if (!formNewStartTime && !formNewEndTime && !formNotes) {
                    setFormError('請至少指定一個要更新的內容')
                    setProcessingSelected(false)
                    return
                }

                const { success, message, error } = await teacherSlotsApi.updateByIds({
                    slot_ids: Array.from(selectedIds),
                    new_start_time: formNewStartTime || undefined,
                    new_end_time: formNewEndTime || undefined,
                    is_available: formIsAvailable,
                    notes: formNotes || undefined,
                })
                if (error) {
                    setFormError(error.message)
                } else {
                    setShowSelectedActionModal(false)
                    clearSelection()
                    fetchSlots()
                }
            }
        } finally {
            setProcessingSelected(false)
        }
    }

    // Clear selection when page changes or filters change
    useEffect(() => {
        clearSelection()
    }, [page, filterTeacherId, dateFrom, dateTo, filterIsAvailable, filterIsBooked])

    return (
        <DashboardLayout>
            <div className="py-8">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    {/* Header */}
                    <div className="mb-8">
                        <div className="flex items-center justify-between">
                            <div>
                                <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                                    <Calendar className="w-8 h-8 text-blue-600" />
                                    教師時段管理
                                </h1>
                                <p className="mt-2 text-gray-600">
                                    共 {total} 個時段
                                </p>
                            </div>
                            {canManage && (
                                <div className="flex gap-2 flex-wrap">
                                    <button
                                        onClick={openBatchDeleteModal}
                                        className="btn-secondary flex items-center gap-2 text-red-600 hover:text-red-700"
                                    >
                                        <Trash2 className="w-5 h-5" />
                                        批次刪除
                                    </button>
                                    <button
                                        onClick={openBatchUpdateModal}
                                        className="btn-secondary flex items-center gap-2"
                                    >
                                        <RefreshCw className="w-5 h-5" />
                                        批次修改
                                    </button>
                                    <button
                                        onClick={openBatchModal}
                                        className="btn-secondary flex items-center gap-2"
                                    >
                                        <Layers className="w-5 h-5" />
                                        批次新增
                                    </button>
                                    <button
                                        onClick={openCreateModal}
                                        className="btn-primary flex items-center gap-2"
                                    >
                                        <Plus className="w-5 h-5" />
                                        新增時段
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Selection action bar */}
                    {selectedIds.size > 0 && (
                        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <span className="text-blue-800 font-medium">
                                    已選擇 {selectedIds.size} 個時段
                                </span>
                                <button
                                    onClick={clearSelection}
                                    className="text-blue-600 hover:text-blue-800 text-sm"
                                >
                                    取消選擇
                                </button>
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={openSelectedUpdateModal}
                                    className="btn-secondary flex items-center gap-2 text-sm py-1.5"
                                >
                                    <RefreshCw className="w-4 h-4" />
                                    修改選中
                                </button>
                                <button
                                    onClick={openSelectedDeleteModal}
                                    className="btn-danger flex items-center gap-2 text-sm py-1.5"
                                >
                                    <Trash2 className="w-4 h-4" />
                                    刪除選中
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Filters */}
                    <div className="card mb-6">
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                            {/* Teacher filter (staff only) */}
                            {isStaff && (
                                <select
                                    value={filterTeacherId}
                                    onChange={(e) => {
                                        setFilterTeacherId(e.target.value)
                                        setPage(1)
                                    }}
                                    className="input-field"
                                >
                                    <option value="">全部教師</option>
                                    {teacherOptions.map(t => (
                                        <option key={t.id} value={t.id}>{t.name} ({t.teacher_no})</option>
                                    ))}
                                </select>
                            )}

                            {/* Date from */}
                            <input
                                type="date"
                                value={dateFrom}
                                onChange={(e) => {
                                    setDateFrom(e.target.value)
                                    setPage(1)
                                }}
                                className="input-field"
                                placeholder="開始日期"
                            />

                            {/* Date to */}
                            <input
                                type="date"
                                value={dateTo}
                                onChange={(e) => {
                                    setDateTo(e.target.value)
                                    setPage(1)
                                }}
                                className="input-field"
                                placeholder="結束日期"
                            />

                            {/* Availability filter */}
                            <select
                                value={filterIsAvailable}
                                onChange={(e) => {
                                    setFilterIsAvailable(e.target.value)
                                    setPage(1)
                                }}
                                className="input-field"
                            >
                                <option value="">全部狀態</option>
                                <option value="true">可預約</option>
                                <option value="false">不可預約</option>
                            </select>

                            {/* Booked filter */}
                            <select
                                value={filterIsBooked}
                                onChange={(e) => {
                                    setFilterIsBooked(e.target.value)
                                    setPage(1)
                                }}
                                className="input-field"
                            >
                                <option value="">全部</option>
                                <option value="true">預約已滿</option>
                                <option value="false">尚有空位</option>
                            </select>

                            {/* Clear filters */}
                            {(filterTeacherId || dateFrom || dateTo || filterIsAvailable || filterIsBooked) && (
                                <button
                                    onClick={() => {
                                        setFilterTeacherId('')
                                        setDateFrom('')
                                        setDateTo('')
                                        setFilterIsAvailable('')
                                        setFilterIsBooked('')
                                        setPage(1)
                                    }}
                                    className="btn-secondary"
                                >
                                    清除篩選
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                            {error}
                        </div>
                    )}

                    {/* Slots List */}
                    {loading ? (
                        <div className="flex justify-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        </div>
                    ) : slots.length === 0 ? (
                        <div className="card text-center py-12">
                            <Calendar className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 mb-2">沒有找到時段</h3>
                            <p className="text-gray-500">
                                {filterTeacherId || dateFrom || dateTo
                                    ? '請嘗試其他搜尋條件'
                                    : '點擊「新增時段」建立第一個可預約時段'}
                            </p>
                        </div>
                    ) : (
                        <div className="card overflow-hidden">
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            {canManage && (
                                                <th className="px-4 py-3 text-left">
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedIds.size > 0 && selectedIds.size === slots.filter(s => !s.is_booked).length}
                                                        onChange={toggleSelectAll}
                                                        className="w-4 h-4 text-blue-600 rounded border-gray-300"
                                                        title="全選/取消全選（僅未預約的時段）"
                                                    />
                                                </th>
                                            )}
                                            {isStaff && (
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    教師
                                                </th>
                                            )}
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                日期
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                時間
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                狀態
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                預約狀態
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                備註
                                            </th>
                                            {canManage && (
                                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    操作
                                                </th>
                                            )}
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {slots.map((slot) => (
                                            <tr key={slot.id} className={`hover:bg-gray-50 ${selectedIds.has(slot.id) ? 'bg-blue-50' : ''}`}>
                                                {canManage && (
                                                    <td className="px-4 py-4 whitespace-nowrap">
                                                        <input
                                                            type="checkbox"
                                                            checked={selectedIds.has(slot.id)}
                                                            onChange={() => toggleSelectSlot(slot.id)}
                                                            disabled={slot.is_booked}
                                                            className="w-4 h-4 text-blue-600 rounded border-gray-300 disabled:opacity-50"
                                                            title={slot.is_booked ? '已預約的時段無法選擇' : '選擇此時段'}
                                                        />
                                                    </td>
                                                )}
                                                {isStaff && (
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="text-sm font-medium text-gray-900">
                                                            {slot.teacher_name || '-'}
                                                        </div>
                                                        {slot.teacher_no && (
                                                            <div className="text-sm text-gray-500">
                                                                {slot.teacher_no}
                                                            </div>
                                                        )}
                                                    </td>
                                                )}
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="text-sm font-medium text-gray-900">
                                                        {slot.slot_date}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="flex items-center text-sm text-gray-900">
                                                        <Clock className="w-4 h-4 mr-1 text-gray-400" />
                                                        {formatTime(slot.start_time)} - {formatTime(slot.end_time)}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    {slot.is_available ? (
                                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                            <CheckCircle className="w-3 h-3 mr-1" />
                                                            可預約
                                                        </span>
                                                    ) : (
                                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                                            <XCircle className="w-3 h-3 mr-1" />
                                                            不可預約
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    {slot.is_booked ? (
                                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                                            <AlertCircle className="w-3 h-3 mr-1" />
                                                            預約已滿
                                                        </span>
                                                    ) : (
                                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                                            尚有空位
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="text-sm text-gray-500 max-w-xs truncate">
                                                        {slot.notes || '-'}
                                                    </div>
                                                </td>
                                                {canManage && (
                                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                        <button
                                                            onClick={() => openEditModal(slot)}
                                                            className="text-blue-600 hover:text-blue-900 mr-4"
                                                            title="編輯"
                                                        >
                                                            <Pencil className="w-5 h-5" />
                                                        </button>
                                                        <button
                                                            onClick={() => setDeleteConfirm(slot)}
                                                            className={`${slot.is_booked ? 'text-gray-300 cursor-not-allowed' : 'text-red-600 hover:text-red-900'}`}
                                                            title={slot.is_booked ? '已預約的時段無法刪除' : '刪除'}
                                                            disabled={slot.is_booked}
                                                        >
                                                            <Trash2 className="w-5 h-5" />
                                                        </button>
                                                    </td>
                                                )}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div className="mt-6 flex items-center justify-between">
                            <div className="text-sm text-gray-500">
                                顯示 {(page - 1) * perPage + 1} - {Math.min(page * perPage, total)} 共 {total} 項
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setPage(p => Math.max(1, p - 1))}
                                    disabled={page === 1}
                                    className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    上一頁
                                </button>
                                <span className="px-4 py-2 text-gray-600">
                                    {page} / {totalPages}
                                </span>
                                <button
                                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                    disabled={page === totalPages}
                                    className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    下一頁
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Create/Edit Modal */}
                {showModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <h2 className="text-xl font-bold text-gray-900">
                                        {modalMode === 'create' ? '新增時段' :
                                         modalMode === 'batch' ? '批次新增時段' :
                                         modalMode === 'batchDelete' ? '批次刪除時段' :
                                         modalMode === 'batchUpdate' ? '批次修改時段' :
                                         '編輯時段'}
                                    </h2>
                                    <button
                                        onClick={closeModal}
                                        className="text-gray-400 hover:text-gray-600"
                                    >
                                        <X className="w-6 h-6" />
                                    </button>
                                </div>

                                {formError && (
                                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                                        {formError}
                                    </div>
                                )}

                                <form onSubmit={handleSubmit} className="space-y-4">
                                    {/* Teacher select (staff only, not for edit) */}
                                    {isStaff && modalMode !== 'edit' && (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                教師 <span className="text-red-500">*</span>
                                            </label>
                                            <select
                                                value={formTeacher}
                                                onChange={(e) => setFormTeacher(e.target.value)}
                                                className="input-field"
                                                required
                                            >
                                                <option value="">請選擇教師</option>
                                                {teacherOptions.map(t => (
                                                    <option key={t.id} value={t.id}>{t.name} ({t.teacher_no})</option>
                                                ))}
                                            </select>
                                        </div>
                                    )}

                                    {/* Teacher display for edit */}
                                    {modalMode === 'edit' && editingSlot && (
                                        <div className="bg-gray-50 p-4 rounded-lg">
                                            <p><span className="font-medium">教師:</span> {editingSlot.teacher_name}</p>
                                            {editingSlot.is_booked && (
                                                <p className="text-yellow-600 text-sm mt-2">
                                                    此時段已預約，無法修改日期和時間
                                                </p>
                                            )}
                                        </div>
                                    )}

                                    {/* Warning for batch delete */}
                                    {modalMode === 'batchDelete' && (
                                        <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                                            <p className="text-red-700 text-sm">
                                                注意：只會刪除未被預約的時段。已預約的時段將被保留。
                                            </p>
                                        </div>
                                    )}

                                    {/* Warning for batch update */}
                                    {modalMode === 'batchUpdate' && (
                                        <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                                            <p className="text-yellow-700 text-sm">
                                                注意：如果要修改時間，只會更新未被預約的時段。修改可用狀態和備註則會套用到所有符合條件的時段。
                                            </p>
                                        </div>
                                    )}

                                    {/* Contract select - only for create and batch create */}
                                    {(modalMode === 'create' || modalMode === 'batch' || modalMode === 'edit') && (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                教師合約
                                            </label>
                                            <select
                                                value={formContract}
                                                onChange={(e) => setFormContract(e.target.value)}
                                                className="input-field"
                                                disabled={!formTeacher && !editingSlot}
                                            >
                                                <option value="">不指定合約</option>
                                                {contractOptions.map(c => (
                                                    <option key={c.id} value={c.id}>{c.contract_no}</option>
                                                ))}
                                            </select>
                                        </div>
                                    )}

                                    {/* Date fields - different for single vs batch */}
                                    {/* Date fields - different for single vs batch modes */}
                                    {(modalMode === 'batch' || modalMode === 'batchDelete' || modalMode === 'batchUpdate') ? (
                                        <>
                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                        開始日期 <span className="text-red-500">*</span>
                                                    </label>
                                                    <input
                                                        type="date"
                                                        value={formStartDate}
                                                        onChange={(e) => setFormStartDate(e.target.value)}
                                                        className="input-field"
                                                        required
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                        結束日期 <span className="text-red-500">*</span>
                                                    </label>
                                                    <input
                                                        type="date"
                                                        value={formEndDate}
                                                        onChange={(e) => setFormEndDate(e.target.value)}
                                                        className="input-field"
                                                        required
                                                    />
                                                </div>
                                            </div>

                                            {/* Weekday selection */}
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                                    星期 {modalMode === 'batch' && <span className="text-red-500">*</span>}
                                                    {(modalMode === 'batchDelete' || modalMode === 'batchUpdate') && (
                                                        <span className="text-gray-500 font-normal">（不選則全部）</span>
                                                    )}
                                                </label>
                                                <div className="flex flex-wrap gap-2">
                                                    {weekdayLabels.map((label, index) => (
                                                        <button
                                                            key={index}
                                                            type="button"
                                                            onClick={() => toggleWeekday(index)}
                                                            className={`px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
                                                                formWeekdays.includes(index)
                                                                    ? 'bg-blue-600 text-white border-blue-600'
                                                                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                                                            }`}
                                                        >
                                                            {label}
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        </>
                                    ) : (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                日期 <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="date"
                                                value={formDate}
                                                onChange={(e) => setFormDate(e.target.value)}
                                                className="input-field"
                                                required
                                                disabled={modalMode === 'edit' && editingSlot?.is_booked}
                                            />
                                        </div>
                                    )}

                                    {/* Time fields - for create, edit, batch create */}
                                    {(modalMode === 'create' || modalMode === 'edit' || modalMode === 'batch') && (
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    開始時間 <span className="text-red-500">*</span>
                                                </label>
                                                <input
                                                    type="time"
                                                    value={formStartTime}
                                                    onChange={(e) => setFormStartTime(e.target.value)}
                                                    className="input-field"
                                                    required
                                                    disabled={modalMode === 'edit' && editingSlot?.is_booked}
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    結束時間 <span className="text-red-500">*</span>
                                                </label>
                                                <input
                                                    type="time"
                                                    value={formEndTime}
                                                    onChange={(e) => setFormEndTime(e.target.value)}
                                                    className="input-field"
                                                    required
                                                    disabled={modalMode === 'edit' && editingSlot?.is_booked}
                                                />
                                            </div>
                                        </div>
                                    )}

                                    {/* Filter time fields - for batch delete/update */}
                                    {(modalMode === 'batchDelete' || modalMode === 'batchUpdate') && (
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    篩選開始時間 <span className="text-gray-500 font-normal">（可選）</span>
                                                </label>
                                                <input
                                                    type="time"
                                                    value={formStartTime}
                                                    onChange={(e) => setFormStartTime(e.target.value)}
                                                    className="input-field"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    篩選結束時間 <span className="text-gray-500 font-normal">（可選）</span>
                                                </label>
                                                <input
                                                    type="time"
                                                    value={formEndTime}
                                                    onChange={(e) => setFormEndTime(e.target.value)}
                                                    className="input-field"
                                                />
                                            </div>
                                        </div>
                                    )}

                                    {/* New time fields - for batch update only */}
                                    {modalMode === 'batchUpdate' && (
                                        <>
                                            <div className="border-t pt-4 mt-2">
                                                <p className="text-sm font-medium text-gray-700 mb-3">更新內容</p>
                                            </div>
                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                        新開始時間 <span className="text-gray-500 font-normal">（可選）</span>
                                                    </label>
                                                    <input
                                                        type="time"
                                                        value={formNewStartTime}
                                                        onChange={(e) => setFormNewStartTime(e.target.value)}
                                                        className="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                        新結束時間 <span className="text-gray-500 font-normal">（可選）</span>
                                                    </label>
                                                    <input
                                                        type="time"
                                                        value={formNewEndTime}
                                                        onChange={(e) => setFormNewEndTime(e.target.value)}
                                                        className="input-field"
                                                    />
                                                </div>
                                            </div>
                                        </>
                                    )}

                                    {/* Availability toggle (for edit and batch update) */}
                                    {(modalMode === 'edit' || modalMode === 'batchUpdate') && (
                                        <div className="flex items-center gap-3">
                                            <input
                                                type="checkbox"
                                                id="isAvailable"
                                                checked={formIsAvailable}
                                                onChange={(e) => setFormIsAvailable(e.target.checked)}
                                                className="w-4 h-4 text-blue-600 rounded border-gray-300"
                                            />
                                            <label htmlFor="isAvailable" className="text-sm text-gray-700">
                                                可預約
                                            </label>
                                        </div>
                                    )}

                                    {/* Notes - not for batch delete */}
                                    {modalMode !== 'batchDelete' && (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                備註 {modalMode === 'batchUpdate' && <span className="text-gray-500 font-normal">（可選）</span>}
                                            </label>
                                            <textarea
                                                value={formNotes}
                                                onChange={(e) => setFormNotes(e.target.value)}
                                                className="input-field"
                                                placeholder="時段備註..."
                                                rows={3}
                                            />
                                        </div>
                                    )}

                                    <div className="flex gap-3 pt-4">
                                        <button
                                            type="button"
                                            onClick={closeModal}
                                            className="btn-secondary flex-1"
                                            disabled={submitting}
                                        >
                                            取消
                                        </button>
                                        <button
                                            type="submit"
                                            className={`flex-1 ${modalMode === 'batchDelete' ? 'btn-danger' : 'btn-primary'}`}
                                            disabled={submitting}
                                        >
                                            {submitting ? (
                                                <span className="flex items-center justify-center">
                                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                                    處理中...
                                                </span>
                                            ) : modalMode === 'batch' ? '批次建立' :
                                               modalMode === 'batchDelete' ? '批次刪除' :
                                               modalMode === 'batchUpdate' ? '批次更新' :
                                               modalMode === 'create' ? '建立' : '儲存'}
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                )}

                {/* Delete Confirmation Modal */}
                {deleteConfirm && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-2">
                                確認刪除時段
                            </h3>
                            <p className="text-gray-600 mb-6">
                                確定要刪除 <span className="font-medium">{deleteConfirm.slot_date}</span> 的時段（{formatTime(deleteConfirm.start_time)} - {formatTime(deleteConfirm.end_time)}）嗎？
                                此操作無法復原。
                            </p>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setDeleteConfirm(null)}
                                    className="btn-secondary flex-1"
                                    disabled={deleting}
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleDelete}
                                    className="btn-danger flex-1"
                                    disabled={deleting}
                                >
                                    {deleting ? (
                                        <span className="flex items-center justify-center">
                                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                            刪除中...
                                        </span>
                                    ) : '確認刪除'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Selected Items Action Modal */}
                {showSelectedActionModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-4">
                                {selectedActionMode === 'delete' ? '批次刪除選中時段' : '批次修改選中時段'}
                            </h3>

                            {formError && (
                                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                                    {formError}
                                </div>
                            )}

                            {selectedActionMode === 'delete' ? (
                                <div>
                                    <div className="bg-red-50 p-4 rounded-lg border border-red-200 mb-6">
                                        <p className="text-red-700">
                                            確定要刪除選中的 <span className="font-bold">{selectedIds.size}</span> 個時段嗎？此操作無法復原。
                                        </p>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200 mb-4">
                                        <p className="text-yellow-700 text-sm">
                                            將更新選中的 <span className="font-bold">{selectedIds.size}</span> 個時段。
                                            如果要修改時間，已預約的時段將被跳過。
                                        </p>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                新開始時間
                                            </label>
                                            <input
                                                type="time"
                                                value={formNewStartTime}
                                                onChange={(e) => setFormNewStartTime(e.target.value)}
                                                className="input-field"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                新結束時間
                                            </label>
                                            <input
                                                type="time"
                                                value={formNewEndTime}
                                                onChange={(e) => setFormNewEndTime(e.target.value)}
                                                className="input-field"
                                            />
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-3">
                                        <input
                                            type="checkbox"
                                            id="selectedIsAvailable"
                                            checked={formIsAvailable}
                                            onChange={(e) => setFormIsAvailable(e.target.checked)}
                                            className="w-4 h-4 text-blue-600 rounded border-gray-300"
                                        />
                                        <label htmlFor="selectedIsAvailable" className="text-sm text-gray-700">
                                            可預約
                                        </label>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            備註
                                        </label>
                                        <textarea
                                            value={formNotes}
                                            onChange={(e) => setFormNotes(e.target.value)}
                                            className="input-field"
                                            placeholder="時段備註..."
                                            rows={2}
                                        />
                                    </div>
                                </div>
                            )}

                            <div className="flex gap-3 mt-6">
                                <button
                                    onClick={() => setShowSelectedActionModal(false)}
                                    className="btn-secondary flex-1"
                                    disabled={processingSelected}
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleSelectedAction}
                                    className={`flex-1 ${selectedActionMode === 'delete' ? 'btn-danger' : 'btn-primary'}`}
                                    disabled={processingSelected}
                                >
                                    {processingSelected ? (
                                        <span className="flex items-center justify-center">
                                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                            處理中...
                                        </span>
                                    ) : selectedActionMode === 'delete' ? '確認刪除' : '確認更新'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </DashboardLayout>
    )
}
