'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import {
    bookingsApi,
    Booking,
    BookingStatus,
    CreateBookingData,
    UpdateBookingData,
    StudentOption,
    TeacherOption,
    CourseOption,
    StudentContractOption,
    TeacherContractOption,
    TeacherSlotOption,
    BatchUpdateByIdsData,
    BatchDeleteByIdsData,
    BatchUpdateData,
    BatchDeleteData,
    BatchCreateData,
    SlotAvailabilityResponse,
    TimeBlock
} from '@/lib/api/bookings'
import { Plus, Pencil, Trash2, Search, X, Calendar, Clock, CheckCircle, XCircle, AlertCircle, User, GraduationCap, Settings, List, Star } from 'lucide-react'
import DashboardLayout from '@/components/DashboardLayout'
import { studentTeacherPreferencesApi, StudentTeacherPreference, CreatePreferenceData, UpdatePreferenceData } from '@/lib/api/studentTeacherPreferences'

const statusConfig: Record<BookingStatus, { label: string; color: string; bgColor: string }> = {
    pending: { label: '待確認', color: 'text-yellow-800', bgColor: 'bg-yellow-100' },
    confirmed: { label: '已確認', color: 'text-blue-800', bgColor: 'bg-blue-100' },
    completed: { label: '已完成', color: 'text-green-800', bgColor: 'bg-green-100' },
    cancelled: { label: '已取消', color: 'text-gray-800', bgColor: 'bg-gray-100' },
}

export default function BookingsPage() {
    const { user, profile } = useAuth()

    // State
    const [bookings, setBookings] = useState<Booking[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [searchTerm, setSearchTerm] = useState('')
    const [filterStatus, setFilterStatus] = useState<BookingStatus | ''>('')
    const [filterStudentId, setFilterStudentId] = useState('')
    const [filterTeacherId, setFilterTeacherId] = useState('')
    const [filterCourseId, setFilterCourseId] = useState('')
    const [dateFrom, setDateFrom] = useState('')
    const [dateTo, setDateTo] = useState('')

    // Pagination
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [total, setTotal] = useState(0)
    const perPage = 10

    // Options for filters
    const [studentOptions, setStudentOptions] = useState<StudentOption[]>([])
    const [teacherOptions, setTeacherOptions] = useState<TeacherOption[]>([])
    const [courseOptions, setCourseOptions] = useState<CourseOption[]>([])

    // Modal state
    const [showModal, setShowModal] = useState(false)
    const [modalMode, setModalMode] = useState<'create' | 'edit'>('create')
    const [editingBooking, setEditingBooking] = useState<Booking | null>(null)
    const [formError, setFormError] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    // Form data for create
    const [formStudent, setFormStudent] = useState('')
    const [formTeacher, setFormTeacher] = useState('')
    const [formStudentContract, setFormStudentContract] = useState('')
    const [formTeacherContract, setFormTeacherContract] = useState('')
    const [formTeacherSlot, setFormTeacherSlot] = useState('')
    const [formBookingDate, setFormBookingDate] = useState('')
    const [formStartTime, setFormStartTime] = useState('')
    const [formEndTime, setFormEndTime] = useState('')
    const [formNotes, setFormNotes] = useState('')
    const [formCourseId, setFormCourseId] = useState('')  // 課程選擇（交集課程）
    const [formOverlappingCourses, setFormOverlappingCourses] = useState<CourseOption[]>([])
    const [loadingOverlappingCourses, setLoadingOverlappingCourses] = useState(false)
    const [formUseAutoSlot, setFormUseAutoSlot] = useState(true)  // 是否自動尋找時段

    // Form data for edit
    const [formStatus, setFormStatus] = useState<BookingStatus>('pending')
    const [formEditNotes, setFormEditNotes] = useState('')

    // Cascading options for modal
    const [studentContracts, setStudentContracts] = useState<StudentContractOption[]>([])
    const [teacherContracts, setTeacherContracts] = useState<TeacherContractOption[]>([])
    const [teacherSlots, setTeacherSlots] = useState<TeacherSlotOption[]>([])
    const [loadingContracts, setLoadingContracts] = useState(false)
    const [loadingSlots, setLoadingSlots] = useState(false)

    // Slot availability (30-min blocks)
    const [slotAvailability, setSlotAvailability] = useState<SlotAvailabilityResponse | null>(null)
    const [loadingAvailability, setLoadingAvailability] = useState(false)
    const [selectedBlockStart, setSelectedBlockStart] = useState<number | null>(null)
    const [selectedBlockEnd, setSelectedBlockEnd] = useState<number | null>(null)

    // Delete confirmation
    const [deleteConfirm, setDeleteConfirm] = useState<Booking | null>(null)
    const [deleting, setDeleting] = useState(false)

    // Student's own info (for student booking)
    const [myStudentInfo, setMyStudentInfo] = useState<StudentOption | null>(null)

    // Multi-select
    const [selectedIds, setSelectedIds] = useState<string[]>([])
    const [selectAll, setSelectAll] = useState(false)

    // Batch modal state
    const [showBatchModal, setShowBatchModal] = useState<'update' | 'delete' | 'period-create' | 'period-update' | 'period-delete' | null>(null)
    const [batchSubmitting, setBatchSubmitting] = useState(false)
    const [batchError, setBatchError] = useState<string | null>(null)

    // Batch form data (for selected items)
    const [batchStatus, setBatchStatus] = useState<BookingStatus>('confirmed')
    const [batchNotes, setBatchNotes] = useState('')

    // Batch form data (for period operations)
    const [batchStartDate, setBatchStartDate] = useState('')
    const [batchEndDate, setBatchEndDate] = useState('')
    const [batchWeekdays, setBatchWeekdays] = useState<number[]>([])
    const [batchFilterStudentId, setBatchFilterStudentId] = useState('')
    const [batchFilterTeacherId, setBatchFilterTeacherId] = useState('')
    const [batchFilterCourseId, setBatchFilterCourseId] = useState('')
    const [batchFilterStatus, setBatchFilterStatus] = useState<BookingStatus | ''>('')
    const [batchNewStatus, setBatchNewStatus] = useState<BookingStatus>('confirmed')
    const [batchPeriodNotes, setBatchPeriodNotes] = useState('')

    // Batch create form data
    const [batchCreateStudentId, setBatchCreateStudentId] = useState('')
    const [batchCreateStudentContractId, setBatchCreateStudentContractId] = useState('')
    const [batchCreateTeacherId, setBatchCreateTeacherId] = useState('')
    const [batchCreateTeacherContractId, setBatchCreateTeacherContractId] = useState('')
    const [batchCreateStartTime, setBatchCreateStartTime] = useState('')
    const [batchCreateEndTime, setBatchCreateEndTime] = useState('')
    const [batchCreateNotes, setBatchCreateNotes] = useState('')
    const [batchCreateCourseId, setBatchCreateCourseId] = useState('')  // 課程選擇（交集課程）
    const [batchCreateOverlappingCourses, setBatchCreateOverlappingCourses] = useState<CourseOption[]>([])
    const [batchCreateLoadingOverlappingCourses, setBatchCreateLoadingOverlappingCourses] = useState(false)
    const [batchCreateStudentContracts, setBatchCreateStudentContracts] = useState<StudentContractOption[]>([])
    const [batchCreateTeacherContracts, setBatchCreateTeacherContracts] = useState<TeacherContractOption[]>([])
    const [batchCreateLoadingContracts, setBatchCreateLoadingContracts] = useState(false)

    // Preferences panel state
    const [showPrefsPanel, setShowPrefsPanel] = useState(false)
    const [prefsStudentId, setPrefsStudentId] = useState('')
    const [preferences, setPreferences] = useState<StudentTeacherPreference[]>([])
    const [loadingPrefs, setLoadingPrefs] = useState(false)
    const [prefError, setPrefError] = useState<string | null>(null)
    // Pref form
    const [showPrefForm, setShowPrefForm] = useState(false)
    const [editingPref, setEditingPref] = useState<StudentTeacherPreference | null>(null)
    const [prefFormCourseId, setPrefFormCourseId] = useState('')
    const [prefFormMinLevel, setPrefFormMinLevel] = useState(1)
    const [prefFormPrimaryTeacherId, setPrefFormPrimaryTeacherId] = useState('')
    const [prefSubmitting, setPrefSubmitting] = useState(false)
    // All teachers (unfiltered) for pref form dropdown
    const [allTeacherOptions, setAllTeacherOptions] = useState<TeacherOption[]>([])

    const isStaff = profile?.role === 'admin' || profile?.role === 'employee'
    const isStudent = profile?.role === 'student'
    const isTeacher = profile?.role === 'teacher'
    const canCreateBooking = isStaff || isStudent

    // 判斷選中的學生是否為試上學生
    const isTrialStudent = (() => {
        if (isStudent && myStudentInfo) {
            return myStudentInfo.student_type === 'trial'
        }
        if (formStudent) {
            const selected = studentOptions.find(s => s.id === formStudent)
            return selected?.student_type === 'trial'
        }
        return false
    })()

    // 批次建立時判斷選中的學生是否為試上學生
    const isBatchTrialStudent = (() => {
        if (isStudent && myStudentInfo) {
            return myStudentInfo.student_type === 'trial'
        }
        if (batchCreateStudentId) {
            const selected = studentOptions.find(s => s.id === batchCreateStudentId)
            return selected?.student_type === 'trial'
        }
        return false
    })()

    // Load filter options
    useEffect(() => {
        const loadOptions = async () => {
            const [studentsRes, teachersRes, coursesRes] = await Promise.all([
                bookingsApi.getStudentOptions(),
                bookingsApi.getTeacherOptions(),
                bookingsApi.getCourseOptions()
            ])
            if (studentsRes.data) setStudentOptions(studentsRes.data)
            if (teachersRes.data) {
                setTeacherOptions(teachersRes.data)
                setAllTeacherOptions(teachersRes.data)
            }
            if (coursesRes.data) setCourseOptions(coursesRes.data)
        }
        loadOptions()
    }, [])

    // Load student's own info (for student booking)
    useEffect(() => {
        const loadMyInfo = async () => {
            if (isStudent) {
                const res = await bookingsApi.getMyStudentInfo()
                if (res.data) {
                    setMyStudentInfo(res.data)
                }
            }
        }
        if (profile) {
            loadMyInfo()
        }
    }, [profile, isStudent])

    // Fetch bookings
    const fetchBookings = useCallback(async () => {
        setLoading(true)
        setError(null)

        const { data, error } = await bookingsApi.list({
            page,
            per_page: perPage,
            search: searchTerm || undefined,
            booking_status: filterStatus || undefined,
            student_id: filterStudentId || undefined,
            teacher_id: filterTeacherId || undefined,
            course_id: filterCourseId || undefined,
            date_from: dateFrom || undefined,
            date_to: dateTo || undefined,
        })

        if (error) {
            setError(error.message)
        } else if (data) {
            setBookings(data.data)
            setTotalPages(data.total_pages)
            setTotal(data.total)
        }

        setLoading(false)
    }, [page, searchTerm, filterStatus, filterStudentId, filterTeacherId, filterCourseId, dateFrom, dateTo])

    useEffect(() => {
        if (user) {
            fetchBookings()
        }
    }, [user, fetchBookings])

    // Search with debounce
    useEffect(() => {
        const timer = setTimeout(() => {
            setPage(1)
        }, 300)
        return () => clearTimeout(timer)
    }, [searchTerm])

    // Load student contracts when student selected, filter by course if selected
    useEffect(() => {
        const loadContracts = async () => {
            let contracts: StudentContractOption[] = []
            if (isStudent && myStudentInfo) {
                setLoadingContracts(true)
                const res = await bookingsApi.getMyContracts()
                contracts = res.data || []
                setLoadingContracts(false)
            } else if (formStudent) {
                setLoadingContracts(true)
                const res = await bookingsApi.getStudentContractOptions(formStudent)
                contracts = res.data || []
                setLoadingContracts(false)
            } else {
                setStudentContracts([])
                setFormStudentContract('')
                return
            }
            // Filter contracts by selected course (use course_ids array if available)
            const filtered = formCourseId
                ? contracts.filter(c => c.course_ids ? c.course_ids.includes(formCourseId) : c.course_id === formCourseId)
                : contracts
            setStudentContracts(filtered)
            // 自動選取最新 active 合約
            if (filtered.length > 0) {
                setFormStudentContract(filtered[0].id)
            } else {
                setFormStudentContract('')
            }
        }
        loadContracts()
    }, [formStudent, formCourseId, isStudent, myStudentInfo])

    // Load overlapping courses when student + teacher are both selected
    useEffect(() => {
        const studentId = isStudent && myStudentInfo ? myStudentInfo.id : formStudent
        if (!studentId || !formTeacher) {
            setFormOverlappingCourses([])
            setFormCourseId('')
            return
        }
        setLoadingOverlappingCourses(true)
        bookingsApi.getOverlappingCourseOptions(studentId, formTeacher).then(res => {
            const courses = res.data || []
            setFormOverlappingCourses(courses)
            setLoadingOverlappingCourses(false)
            // 自動選取（若只有一個課程）
            if (courses.length === 1) {
                setFormCourseId(courses[0].id)
            } else {
                setFormCourseId('')
            }
            // Reset dependent fields
            setFormStudentContract('')
        })
    }, [formStudent, formTeacher, isStudent, myStudentInfo])

    // Refetch teacher options filtered by student preference when student changes
    useEffect(() => {
        const studentId = isStudent && myStudentInfo ? myStudentInfo.id : formStudent
        if (!studentId) return

        bookingsApi.getTeacherOptions({ student_id: studentId }).then(res => {
            if (res.data) {
                setTeacherOptions(res.data)
                // Reset teacher selection if current teacher is no longer in filtered list
                if (formTeacher && !res.data.find(t => t.id === formTeacher)) {
                    setFormTeacher('')
                }
            }
        })
    }, [formStudent, isStudent, myStudentInfo])

    // Load teacher contracts when teacher selected
    useEffect(() => {
        if (formTeacher) {
            setLoadingContracts(true)
            bookingsApi.getTeacherContractOptions(formTeacher).then(res => {
                const contracts = res.data || []
                setTeacherContracts(contracts)
                setLoadingContracts(false)
                // 自動選取最新 active 合約
                if (contracts.length > 0) {
                    setFormTeacherContract(contracts[0].id)
                } else {
                    setFormTeacherContract('')
                }
            })
        } else {
            setTeacherContracts([])
            setFormTeacherContract('')
        }
        setTeacherSlots([])
        setFormTeacherSlot('')
    }, [formTeacher])

    // Load teacher slots when teacher selected
    useEffect(() => {
        if (formTeacher) {
            setLoadingSlots(true)
            const today = new Date().toISOString().split('T')[0]
            bookingsApi.getTeacherSlotOptions(formTeacher, today).then(res => {
                setTeacherSlots(res.data || [])
                setLoadingSlots(false)
            })
        } else {
            setTeacherSlots([])
        }
        setFormTeacherSlot('')
    }, [formTeacher])

    // Load slot availability when a slot is selected (manual mode)
    useEffect(() => {
        if (formTeacherSlot) {
            setLoadingAvailability(true)
            setSlotAvailability(null)
            setSelectedBlockStart(null)
            setSelectedBlockEnd(null)
            setFormStartTime('')
            setFormEndTime('')
            setFormBookingDate('')
            bookingsApi.getSlotAvailability(formTeacherSlot).then(res => {
                if (res.data) {
                    setSlotAvailability(res.data)
                    setFormBookingDate(res.data.slot_date)
                }
                setLoadingAvailability(false)
            })
        } else {
            setSlotAvailability(null)
            setSelectedBlockStart(null)
            setSelectedBlockEnd(null)
        }
    }, [formTeacherSlot])

    // Handle block click for 30-min block selection
    const handleBlockClick = (blockIndex: number) => {
        if (!slotAvailability) return
        const block = slotAvailability.blocks[blockIndex]
        if (!block.is_available) return

        if (selectedBlockStart === null) {
            // First click: set start
            setSelectedBlockStart(blockIndex)
            setSelectedBlockEnd(blockIndex)
            setFormStartTime(block.start_time.substring(0, 5))
            setFormEndTime(block.end_time.substring(0, 5))
        } else if (selectedBlockEnd === blockIndex && selectedBlockStart === blockIndex) {
            // Click same block again: deselect
            setSelectedBlockStart(null)
            setSelectedBlockEnd(null)
            setFormStartTime('')
            setFormEndTime('')
        } else {
            // Second click: set end (expand range)
            const start = Math.min(selectedBlockStart, blockIndex)
            const end = Math.max(selectedBlockStart, blockIndex)

            // Check all blocks in range are available
            let allAvailable = true
            for (let i = start; i <= end; i++) {
                if (!slotAvailability.blocks[i].is_available) {
                    allAvailable = false
                    break
                }
            }

            if (allAvailable) {
                setSelectedBlockStart(start)
                setSelectedBlockEnd(end)
                setFormStartTime(slotAvailability.blocks[start].start_time.substring(0, 5))
                setFormEndTime(slotAvailability.blocks[end].end_time.substring(0, 5))
            }
        }
    }

    // Modal handlers
    const openCreateModal = () => {
        setModalMode('create')
        setEditingBooking(null)
        // If student, auto-set their student ID
        setFormStudent(isStudent && myStudentInfo ? myStudentInfo.id : '')
        setFormTeacher('')
        setFormStudentContract('')
        setFormTeacherContract('')
        setFormTeacherSlot('')
        setFormBookingDate('')
        setFormStartTime('')
        setFormEndTime('')
        setFormNotes('')
        setFormCourseId('')
        setFormOverlappingCourses([])
        setFormUseAutoSlot(true)
        setSlotAvailability(null)
        setSelectedBlockStart(null)
        setSelectedBlockEnd(null)
        if (!isStudent) {
            setStudentContracts([])
        }
        setTeacherContracts([])
        setTeacherSlots([])
        setFormError(null)
        setShowModal(true)
    }

    const openEditModal = (booking: Booking) => {
        setModalMode('edit')
        setEditingBooking(booking)
        setFormStatus(booking.booking_status)
        setFormEditNotes(booking.notes || '')
        setFormError(null)
        setShowModal(true)
    }

    const closeModal = () => {
        setShowModal(false)
        setEditingBooking(null)
        setFormError(null)
        // Reset teacher options to unfiltered
        setTeacherOptions(allTeacherOptions)
    }

    // 教師確認預約
    const handleTeacherConfirm = async (booking: Booking) => {
        const { data, error } = await bookingsApi.update(booking.id, { booking_status: 'confirmed' as BookingStatus })
        if (error) {
            setError(error.message)
        } else {
            fetchBookings()
        }
    }

    // Form submit
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setFormError(null)
        setSubmitting(true)

        try {
            if (modalMode === 'create') {
                // 課程 ID 從交集課程下拉取得
                if (!formCourseId) {
                    setFormError('請選擇課程')
                    setSubmitting(false)
                    return
                }
                const courseId = formCourseId

                // 非試上學生必須選合約
                if (!isTrialStudent && !formStudentContract) {
                    setFormError('請選擇學生合約')
                    setSubmitting(false)
                    return
                }

                let createData: CreateBookingData

                if (formUseAutoSlot) {
                    // 自動尋找時段模式：用戶輸入日期和時間
                    if (!formBookingDate) {
                        setFormError('請選擇預約日期')
                        setSubmitting(false)
                        return
                    }
                    if (!formStartTime || !formEndTime) {
                        setFormError('請輸入開始和結束時間')
                        setSubmitting(false)
                        return
                    }

                    createData = {
                        student_id: formStudent,
                        teacher_id: formTeacher,
                        course_id: courseId,
                        student_contract_id: formStudentContract || undefined,
                        teacher_contract_id: formTeacherContract || undefined,
                        // 不提供 teacher_slot_id，讓後端自動尋找
                        booking_date: formBookingDate,
                        start_time: formStartTime,
                        end_time: formEndTime,
                        notes: formNotes || undefined,
                    }
                } else {
                    // 手動選擇時段模式
                    if (!formTeacherSlot) {
                        setFormError('請選擇教師時段')
                        setSubmitting(false)
                        return
                    }
                    if (!formStartTime || !formEndTime) {
                        setFormError('請選擇時間區塊')
                        setSubmitting(false)
                        return
                    }

                    createData = {
                        student_id: formStudent,
                        teacher_id: formTeacher,
                        course_id: courseId,
                        student_contract_id: formStudentContract || undefined,
                        teacher_contract_id: formTeacherContract || undefined,
                        teacher_slot_id: formTeacherSlot,
                        booking_date: formBookingDate,
                        start_time: formStartTime,
                        end_time: formEndTime,
                        notes: formNotes || undefined,
                    }
                }

                const { data, error } = await bookingsApi.create(createData)
                if (error) {
                    setFormError(error.message)
                } else {
                    closeModal()
                    fetchBookings()
                }
            } else if (editingBooking) {
                const updateData: UpdateBookingData = {}
                if (formStatus !== editingBooking.booking_status) updateData.booking_status = formStatus
                if (formEditNotes !== editingBooking.notes) updateData.notes = formEditNotes

                const { data, error } = await bookingsApi.update(editingBooking.id, updateData)
                if (error) {
                    setFormError(error.message)
                } else {
                    closeModal()
                    fetchBookings()
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

        const { success, error } = await bookingsApi.delete(deleteConfirm.id)

        if (error) {
            setError(error.message)
        } else {
            setDeleteConfirm(null)
            fetchBookings()
        }

        setDeleting(false)
    }

    const formatTime = (time: string) => {
        return time.substring(0, 5)
    }

    // Multi-select handlers
    const handleSelectAll = () => {
        if (selectAll) {
            setSelectedIds([])
        } else {
            setSelectedIds(bookings.map(b => b.id))
        }
        setSelectAll(!selectAll)
    }

    const handleSelectOne = (id: string) => {
        if (selectedIds.includes(id)) {
            setSelectedIds(selectedIds.filter(i => i !== id))
        } else {
            setSelectedIds([...selectedIds, id])
        }
    }

    // Clear selection when page/filters change
    useEffect(() => {
        setSelectedIds([])
        setSelectAll(false)
    }, [page, filterStatus, filterStudentId, filterTeacherId, filterCourseId, dateFrom, dateTo])

    // Batch modal handlers
    const openBatchModal = (type: 'update' | 'delete' | 'period-create' | 'period-update' | 'period-delete') => {
        setBatchError(null)
        if (type === 'update' || type === 'delete') {
            setBatchStatus('confirmed')
            setBatchNotes('')
        } else if (type === 'period-create') {
            setBatchStartDate('')
            setBatchEndDate('')
            setBatchWeekdays([])
            setBatchCreateStudentId(isStudent && myStudentInfo ? myStudentInfo.id : '')
            setBatchCreateStudentContractId('')
            setBatchCreateTeacherId('')
            setBatchCreateTeacherContractId('')
            setBatchCreateStartTime('')
            setBatchCreateEndTime('')
            setBatchCreateNotes('')
            setBatchCreateStudentContracts([])
            setBatchCreateTeacherContracts([])
        } else {
            setBatchStartDate('')
            setBatchEndDate('')
            setBatchWeekdays([])
            setBatchFilterStudentId('')
            setBatchFilterTeacherId('')
            setBatchFilterCourseId('')
            setBatchFilterStatus('')
            setBatchNewStatus('confirmed')
            setBatchPeriodNotes('')
        }
        setShowBatchModal(type)
    }

    const closeBatchModal = () => {
        setShowBatchModal(null)
        setBatchError(null)
        setBatchCreateCourseId('')
        setBatchCreateOverlappingCourses([])
        // Reset teacher options to unfiltered
        setTeacherOptions(allTeacherOptions)
    }

    const handleBatchUpdate = async () => {
        if (selectedIds.length === 0) return
        setBatchSubmitting(true)
        setBatchError(null)

        const { success, message, error } = await bookingsApi.updateByIds({
            booking_ids: selectedIds,
            booking_status: batchStatus,
            notes: batchNotes || undefined
        })

        if (error) {
            setBatchError(error.message)
        } else {
            closeBatchModal()
            setSelectedIds([])
            setSelectAll(false)
            fetchBookings()
        }

        setBatchSubmitting(false)
    }

    const handleBatchDelete = async () => {
        if (selectedIds.length === 0) return
        setBatchSubmitting(true)
        setBatchError(null)

        const { success, message, error } = await bookingsApi.deleteByIds({
            booking_ids: selectedIds
        })

        if (error) {
            setBatchError(error.message)
        } else {
            closeBatchModal()
            setSelectedIds([])
            setSelectAll(false)
            fetchBookings()
        }

        setBatchSubmitting(false)
    }

    const handleBatchPeriodUpdate = async () => {
        if (!batchStartDate || !batchEndDate) {
            setBatchError('請選擇日期範圍')
            return
        }
        setBatchSubmitting(true)
        setBatchError(null)

        const { success, message, error } = await bookingsApi.updateBatch({
            start_date: batchStartDate,
            end_date: batchEndDate,
            weekdays: batchWeekdays.length > 0 ? batchWeekdays : undefined,
            student_id: batchFilterStudentId || undefined,
            teacher_id: batchFilterTeacherId || undefined,
            course_id: batchFilterCourseId || undefined,
            filter_status: batchFilterStatus || undefined,
            new_status: batchNewStatus,
            notes: batchPeriodNotes || undefined
        })

        if (error) {
            setBatchError(error.message)
        } else {
            closeBatchModal()
            fetchBookings()
        }

        setBatchSubmitting(false)
    }

    const handleBatchPeriodDelete = async () => {
        if (!batchStartDate || !batchEndDate) {
            setBatchError('請選擇日期範圍')
            return
        }
        setBatchSubmitting(true)
        setBatchError(null)

        const { success, message, error } = await bookingsApi.deleteBatch({
            start_date: batchStartDate,
            end_date: batchEndDate,
            weekdays: batchWeekdays.length > 0 ? batchWeekdays : undefined,
            student_id: batchFilterStudentId || undefined,
            teacher_id: batchFilterTeacherId || undefined,
            course_id: batchFilterCourseId || undefined,
            filter_status: batchFilterStatus || undefined
        })

        if (error) {
            setBatchError(error.message)
        } else {
            closeBatchModal()
            fetchBookings()
        }

        setBatchSubmitting(false)
    }

    const toggleWeekday = (day: number) => {
        if (batchWeekdays.includes(day)) {
            setBatchWeekdays(batchWeekdays.filter(d => d !== day))
        } else {
            setBatchWeekdays([...batchWeekdays, day])
        }
    }

    const weekdayLabels = ['一', '二', '三', '四', '五', '六', '日']

    // Load overlapping courses for batch create when student + teacher selected
    useEffect(() => {
        if (showBatchModal !== 'period-create') return
        const studentId = isStudent && myStudentInfo ? myStudentInfo.id : batchCreateStudentId
        if (!studentId || !batchCreateTeacherId) {
            setBatchCreateOverlappingCourses([])
            setBatchCreateCourseId('')
            return
        }
        setBatchCreateLoadingOverlappingCourses(true)
        bookingsApi.getOverlappingCourseOptions(studentId, batchCreateTeacherId).then(res => {
            const courses = res.data || []
            setBatchCreateOverlappingCourses(courses)
            setBatchCreateLoadingOverlappingCourses(false)
            if (courses.length === 1) {
                setBatchCreateCourseId(courses[0].id)
            } else {
                setBatchCreateCourseId('')
            }
            setBatchCreateStudentContractId('')
        })
    }, [showBatchModal, batchCreateStudentId, batchCreateTeacherId, isStudent, myStudentInfo])

    // Load student contracts for batch create modal, filtered by course
    useEffect(() => {
        const loadBatchCreateStudentContracts = async () => {
            if (showBatchModal === 'period-create' && batchCreateStudentId) {
                setBatchCreateLoadingContracts(true)
                let contracts: StudentContractOption[] = []
                if (isStudent && myStudentInfo) {
                    const res = await bookingsApi.getMyContracts()
                    contracts = res.data || []
                } else {
                    const res = await bookingsApi.getStudentContractOptions(batchCreateStudentId)
                    contracts = res.data || []
                }
                // Filter by selected course (use course_ids array if available)
                const filtered = batchCreateCourseId
                    ? contracts.filter(c => c.course_ids ? c.course_ids.includes(batchCreateCourseId) : c.course_id === batchCreateCourseId)
                    : contracts
                setBatchCreateStudentContracts(filtered)
                setBatchCreateLoadingContracts(false)
                if (filtered.length > 0) {
                    setBatchCreateStudentContractId(filtered[0].id)
                } else {
                    setBatchCreateStudentContractId('')
                }
            }
        }
        loadBatchCreateStudentContracts()
    }, [showBatchModal, batchCreateStudentId, batchCreateCourseId, isStudent, myStudentInfo])

    // Load teacher contracts for batch create modal
    useEffect(() => {
        const loadBatchCreateTeacherContracts = async () => {
            if (showBatchModal === 'period-create' && batchCreateTeacherId) {
                setBatchCreateLoadingContracts(true)
                const res = await bookingsApi.getTeacherContractOptions(batchCreateTeacherId)
                const contracts = res.data || []
                setBatchCreateTeacherContracts(contracts)
                setBatchCreateLoadingContracts(false)
                if (contracts.length > 0) {
                    setBatchCreateTeacherContractId(contracts[0].id)
                } else {
                    setBatchCreateTeacherContractId('')
                }
            }
        }
        loadBatchCreateTeacherContracts()
    }, [showBatchModal, batchCreateTeacherId])

    // Refetch teacher options for batch create when student changes
    useEffect(() => {
        if (showBatchModal !== 'period-create') return
        const studentId = isStudent && myStudentInfo ? myStudentInfo.id : batchCreateStudentId
        if (!studentId) return

        bookingsApi.getTeacherOptions({ student_id: studentId }).then(res => {
            if (res.data) {
                setTeacherOptions(res.data)
                if (batchCreateTeacherId && !res.data.find(t => t.id === batchCreateTeacherId)) {
                    setBatchCreateTeacherId('')
                }
            }
        })
    }, [showBatchModal, batchCreateStudentId, isStudent, myStudentInfo])

    // Handle batch create
    const handleBatchCreate = async () => {
        if (!batchStartDate || !batchEndDate) {
            setBatchError('請選擇日期範圍')
            return
        }
        if (batchWeekdays.length === 0) {
            setBatchError('請選擇至少一個星期幾')
            return
        }
        if (!batchCreateStudentId) {
            setBatchError('請選擇學生')
            return
        }
        if (!batchCreateTeacherId) {
            setBatchError('請選擇教師')
            return
        }
        if (!batchCreateCourseId) {
            setBatchError('請選擇課程')
            return
        }
        if (!batchCreateStudentContractId && !isBatchTrialStudent) {
            setBatchError('請選擇學生合約')
            return
        }

        setBatchSubmitting(true)
        setBatchError(null)

        const { success, message, error } = await bookingsApi.createBatch({
            student_id: batchCreateStudentId,
            student_contract_id: batchCreateStudentContractId || undefined,
            course_id: batchCreateCourseId,
            teacher_id: batchCreateTeacherId,
            teacher_contract_id: batchCreateTeacherContractId || undefined,
            start_date: batchStartDate,
            end_date: batchEndDate,
            weekdays: batchWeekdays,
            start_time: batchCreateStartTime || undefined,
            end_time: batchCreateEndTime || undefined,
            notes: batchCreateNotes || undefined
        })

        if (error) {
            setBatchError(error.message)
        } else {
            closeBatchModal()
            fetchBookings()
        }

        setBatchSubmitting(false)
    }

    // === Preferences Panel Functions ===
    const loadPreferences = async (studentId: string) => {
        setLoadingPrefs(true)
        setPrefError(null)
        const { data, error } = await studentTeacherPreferencesApi.list(studentId)
        if (error) {
            setPrefError(error.message)
        } else {
            setPreferences(data || [])
        }
        setLoadingPrefs(false)
    }

    useEffect(() => {
        if (showPrefsPanel && prefsStudentId) {
            loadPreferences(prefsStudentId)
        }
    }, [showPrefsPanel, prefsStudentId])

    const openPrefCreate = () => {
        setEditingPref(null)
        setPrefFormCourseId('')
        setPrefFormMinLevel(1)
        setPrefFormPrimaryTeacherId('')
        setPrefError(null)
        setShowPrefForm(true)
    }

    const openPrefEdit = (pref: StudentTeacherPreference) => {
        setEditingPref(pref)
        setPrefFormCourseId(pref.course_id || '')
        setPrefFormMinLevel(pref.min_teacher_level)
        setPrefFormPrimaryTeacherId(pref.primary_teacher_id || '')
        setPrefError(null)
        setShowPrefForm(true)
    }

    const handlePrefSubmit = async () => {
        setPrefSubmitting(true)
        setPrefError(null)

        if (editingPref) {
            const updateData: UpdatePreferenceData = {
                min_teacher_level: prefFormMinLevel,
                primary_teacher_id: prefFormPrimaryTeacherId || null,
            }
            const { error } = await studentTeacherPreferencesApi.update(editingPref.id, updateData)
            if (error) {
                setPrefError(error.message)
            } else {
                setShowPrefForm(false)
                loadPreferences(prefsStudentId)
            }
        } else {
            const createData: CreatePreferenceData = {
                student_id: prefsStudentId,
                course_id: prefFormCourseId || null,
                min_teacher_level: prefFormMinLevel,
                primary_teacher_id: prefFormPrimaryTeacherId || null,
            }
            const { error } = await studentTeacherPreferencesApi.create(createData)
            if (error) {
                setPrefError(error.message)
            } else {
                setShowPrefForm(false)
                loadPreferences(prefsStudentId)
            }
        }

        setPrefSubmitting(false)
    }

    const handlePrefDelete = async (prefId: string) => {
        const { error } = await studentTeacherPreferencesApi.delete(prefId)
        if (error) {
            setPrefError(error.message)
        } else {
            loadPreferences(prefsStudentId)
        }
    }

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
                                    預約管理
                                </h1>
                                <p className="mt-2 text-gray-600">
                                    共 {total} 筆預約
                                </p>
                            </div>
                            <div className="flex items-center gap-3">
                                {isStaff && (
                                    <>
                                        <button
                                            onClick={() => setShowPrefsPanel(true)}
                                            className="btn-secondary flex items-center gap-2"
                                        >
                                            <Star className="w-5 h-5" />
                                            偏好設定
                                        </button>
                                        <button
                                            onClick={() => openBatchModal('period-update')}
                                            className="btn-secondary flex items-center gap-2"
                                        >
                                            <Settings className="w-5 h-5" />
                                            批次更新
                                        </button>
                                        <button
                                            onClick={() => openBatchModal('period-delete')}
                                            className="btn-secondary flex items-center gap-2 text-red-600 hover:text-red-700"
                                        >
                                            <Trash2 className="w-5 h-5" />
                                            批次刪除
                                        </button>
                                    </>
                                )}
                                {canCreateBooking && (
                                    <>
                                        <button
                                            onClick={() => openBatchModal('period-create')}
                                            className="btn-secondary flex items-center gap-2"
                                        >
                                            <List className="w-5 h-5" />
                                            批次新增
                                        </button>
                                        <button
                                            onClick={openCreateModal}
                                            className="btn-primary flex items-center gap-2"
                                        >
                                            <Plus className="w-5 h-5" />
                                            {isStudent ? '預約課程' : '新增預約'}
                                        </button>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Selection Action Bar */}
                    {isStaff && selectedIds.length > 0 && (
                        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
                            <span className="text-blue-800">
                                已選擇 {selectedIds.length} 筆預約
                            </span>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => openBatchModal('update')}
                                    className="btn-secondary flex items-center gap-2 text-sm"
                                >
                                    <Settings className="w-4 h-4" />
                                    批次更新狀態
                                </button>
                                <button
                                    onClick={() => openBatchModal('delete')}
                                    className="btn-secondary flex items-center gap-2 text-sm text-red-600 hover:text-red-700"
                                >
                                    <Trash2 className="w-4 h-4" />
                                    批次刪除
                                </button>
                                <button
                                    onClick={() => {
                                        setSelectedIds([])
                                        setSelectAll(false)
                                    }}
                                    className="btn-secondary text-sm"
                                >
                                    取消選擇
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Filters */}
                    <div className="card mb-6">
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                            {/* Search */}
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                <input
                                    type="text"
                                    placeholder="搜尋預約編號..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="input-field pl-10"
                                />
                                {searchTerm && (
                                    <button
                                        onClick={() => setSearchTerm('')}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                    >
                                        <X className="w-5 h-5" />
                                    </button>
                                )}
                            </div>

                            {/* Status filter */}
                            <select
                                value={filterStatus}
                                onChange={(e) => {
                                    setFilterStatus(e.target.value as BookingStatus | '')
                                    setPage(1)
                                }}
                                className="input-field"
                            >
                                <option value="">全部狀態</option>
                                <option value="pending">待確認</option>
                                <option value="confirmed">已確認</option>
                                <option value="completed">已完成</option>
                                <option value="cancelled">已取消</option>
                            </select>

                            {/* Student filter */}
                            <select
                                value={filterStudentId}
                                onChange={(e) => {
                                    setFilterStudentId(e.target.value)
                                    setPage(1)
                                }}
                                className="input-field"
                            >
                                <option value="">全部學生</option>
                                {studentOptions.map(s => (
                                    <option key={s.id} value={s.id}>{s.name} ({s.student_no})</option>
                                ))}
                            </select>

                            {/* Teacher filter */}
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

                            {/* Course filter */}
                            <select
                                value={filterCourseId}
                                onChange={(e) => {
                                    setFilterCourseId(e.target.value)
                                    setPage(1)
                                }}
                                className="input-field"
                            >
                                <option value="">全部課程</option>
                                {courseOptions.map(c => (
                                    <option key={c.id} value={c.id}>{c.course_name}</option>
                                ))}
                            </select>

                            {/* Date from */}
                            <div>
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
                            </div>

                            {/* Date to */}
                            <div>
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
                            </div>

                            {/* Clear filters */}
                            {(filterStatus || filterStudentId || filterTeacherId || filterCourseId || dateFrom || dateTo) && (
                                <button
                                    onClick={() => {
                                        setFilterStatus('')
                                        setFilterStudentId('')
                                        setFilterTeacherId('')
                                        setFilterCourseId('')
                                        setDateFrom('')
                                        setDateTo('')
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

                    {/* Booking List */}
                    {loading ? (
                        <div className="flex justify-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        </div>
                    ) : bookings.length === 0 ? (
                        <div className="card text-center py-12">
                            <Calendar className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 mb-2">沒有找到預約</h3>
                            <p className="text-gray-500">
                                {searchTerm || filterStatus || filterStudentId || filterTeacherId
                                    ? '請嘗試其他搜尋條件'
                                    : '點擊「新增預約」建立第一筆預約'}
                            </p>
                        </div>
                    ) : (
                        <div className="card overflow-hidden">
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            {isStaff && (
                                                <th className="px-4 py-3 text-left">
                                                    <input
                                                        type="checkbox"
                                                        checked={selectAll}
                                                        onChange={handleSelectAll}
                                                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                                    />
                                                </th>
                                            )}
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                預約編號
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                學生
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                教師
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                課程
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                日期時間
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                狀態
                                            </th>
                                            {(isStaff || isTeacher) && (
                                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    操作
                                                </th>
                                            )}
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {bookings.map((booking) => {
                                            const status = statusConfig[booking.booking_status]
                                            const isSelected = selectedIds.includes(booking.id)
                                            return (
                                                <tr key={booking.id} className={`hover:bg-gray-50 ${isSelected ? 'bg-blue-50' : ''}`}>
                                                    {isStaff && (
                                                        <td className="px-4 py-4 whitespace-nowrap">
                                                            <input
                                                                type="checkbox"
                                                                checked={isSelected}
                                                                onChange={() => handleSelectOne(booking.id)}
                                                                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                                            />
                                                        </td>
                                                    )}
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">
                                                            {booking.booking_no}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="flex items-center">
                                                            <User className="w-4 h-4 mr-2 text-gray-400" />
                                                            {booking.student_name || '-'}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="flex items-center">
                                                            <GraduationCap className="w-4 h-4 mr-2 text-gray-400" />
                                                            {booking.teacher_name || '-'}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        {booking.course_name || '-'}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div>
                                                            <div className="text-sm font-medium text-gray-900">
                                                                {booking.booking_date}
                                                            </div>
                                                            <div className="flex items-center text-sm text-gray-500">
                                                                <Clock className="w-3 h-3 mr-1" />
                                                                {formatTime(booking.start_time)} - {formatTime(booking.end_time)}
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${status.bgColor} ${status.color}`}>
                                                            {booking.booking_status === 'pending' && <AlertCircle className="w-3 h-3 mr-1" />}
                                                            {booking.booking_status === 'confirmed' && <CheckCircle className="w-3 h-3 mr-1" />}
                                                            {booking.booking_status === 'completed' && <CheckCircle className="w-3 h-3 mr-1" />}
                                                            {booking.booking_status === 'cancelled' && <XCircle className="w-3 h-3 mr-1" />}
                                                            {status.label}
                                                        </span>
                                                    </td>
                                                    {isStaff && (
                                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                            <button
                                                                onClick={() => openEditModal(booking)}
                                                                className="text-blue-600 hover:text-blue-900 mr-4"
                                                                title="編輯"
                                                            >
                                                                <Pencil className="w-5 h-5" />
                                                            </button>
                                                            <button
                                                                onClick={() => setDeleteConfirm(booking)}
                                                                className="text-red-600 hover:text-red-900"
                                                                title="刪除"
                                                            >
                                                                <Trash2 className="w-5 h-5" />
                                                            </button>
                                                        </td>
                                                    )}
                                                    {isTeacher && (
                                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                            {booking.booking_status === 'pending' ? (
                                                                <button
                                                                    onClick={() => handleTeacherConfirm(booking)}
                                                                    className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md"
                                                                    title="確認預約"
                                                                >
                                                                    <CheckCircle className="w-4 h-4 mr-1" />
                                                                    確認
                                                                </button>
                                                            ) : (
                                                                <span className="text-sm text-gray-400">-</span>
                                                            )}
                                                        </td>
                                                    )}
                                                </tr>
                                            )
                                        })}
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
                                        {modalMode === 'create' ? '新增預約' : '編輯預約'}
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
                                    {modalMode === 'create' ? (
                                        <>
                                            {/* Student select - hidden for students, they can only book for themselves */}
                                            {isStudent ? (
                                                <div className="bg-gray-50 p-4 rounded-lg">
                                                    <p className="text-sm text-gray-600">
                                                        <span className="font-medium">學生:</span> {myStudentInfo?.name} ({myStudentInfo?.student_no})
                                                    </p>
                                                </div>
                                            ) : (
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                        學生 <span className="text-red-500">*</span>
                                                    </label>
                                                    <select
                                                        value={formStudent}
                                                        onChange={(e) => setFormStudent(e.target.value)}
                                                        className="input-field"
                                                        required
                                                    >
                                                        <option value="">請選擇學生</option>
                                                        {studentOptions.map(s => (
                                                            <option key={s.id} value={s.id}>{s.name} ({s.student_no}){s.student_type === 'trial' ? ' [試上]' : ''}</option>
                                                        ))}
                                                    </select>
                                                </div>
                                            )}

                                            {/* Teacher select */}
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    教師 <span className="text-red-500">*</span>
                                                </label>
                                                <select
                                                    value={formTeacher}
                                                    onChange={(e) => setFormTeacher(e.target.value)}
                                                    className="input-field"
                                                    required
                                                    disabled={!formStudent && !isStudent}
                                                >
                                                    <option value="">請選擇教師</option>
                                                    {teacherOptions.map(t => (
                                                        <option key={t.id} value={t.id}>
                                                            {t.is_primary ? '★ ' : ''}{t.name} ({t.teacher_no}){t.teacher_level ? ` Lv.${t.teacher_level}` : ''}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>

                                            {/* Course select - overlapping courses (intersection of student courses & teacher teachable courses) */}
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    課程 <span className="text-red-500">*</span>
                                                </label>
                                                <select
                                                    value={formCourseId}
                                                    onChange={(e) => setFormCourseId(e.target.value)}
                                                    className="input-field"
                                                    required
                                                    disabled={loadingOverlappingCourses || !formTeacher || (!formStudent && !isStudent)}
                                                >
                                                    <option value="">{loadingOverlappingCourses ? '載入中...' : '請選擇課程'}</option>
                                                    {formOverlappingCourses.map(c => (
                                                        <option key={c.id} value={c.id}>{c.course_name} ({c.course_code})</option>
                                                    ))}
                                                </select>
                                                {(formStudent || isStudent) && formTeacher && formOverlappingCourses.length === 0 && !loadingOverlappingCourses && (
                                                    <p className="mt-1 text-sm text-yellow-600">
                                                        此學生與教師無共同可選課程
                                                    </p>
                                                )}
                                            </div>

                                            {/* Student contract select - filtered by selected course */}
                                            {!isTrialStudent && (
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                        學生合約 <span className="text-red-500">*</span>
                                                    </label>
                                                    <select
                                                        value={formStudentContract}
                                                        onChange={(e) => setFormStudentContract(e.target.value)}
                                                        className="input-field"
                                                        required
                                                        disabled={!formCourseId || loadingContracts}
                                                    >
                                                        <option value="">{loadingContracts ? '載入中...' : '請選擇合約'}</option>
                                                        {studentContracts.map(c => (
                                                            <option key={c.id} value={c.id}>
                                                                {c.contract_no} - {c.course_name} (剩餘 {c.remaining_lessons} 堂)
                                                            </option>
                                                        ))}
                                                    </select>
                                                    {formCourseId && studentContracts.length === 0 && !loadingContracts && (
                                                        <p className="mt-1 text-sm text-yellow-600">
                                                            {isStudent ? '您沒有此課程的有效合約' : '此學生沒有此課程的有效合約'}
                                                        </p>
                                                    )}
                                                </div>
                                            )}
                                            {isTrialStudent && (
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                        學生合約
                                                        <span className="text-gray-400 text-xs ml-1">（試上學生可不選）</span>
                                                    </label>
                                                    <select
                                                        value={formStudentContract}
                                                        onChange={(e) => setFormStudentContract(e.target.value)}
                                                        className="input-field"
                                                        disabled={!formCourseId || loadingContracts}
                                                    >
                                                        <option value="">{loadingContracts ? '載入中...' : '不選擇合約（試上）'}</option>
                                                        {studentContracts.map(c => (
                                                            <option key={c.id} value={c.id}>
                                                                {c.contract_no} - {c.course_name} (剩餘 {c.remaining_lessons} 堂)
                                                            </option>
                                                        ))}
                                                    </select>
                                                </div>
                                            )}

                                            {/* Teacher contract select */}
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    教師合約
                                                </label>
                                                <select
                                                    value={formTeacherContract}
                                                    onChange={(e) => setFormTeacherContract(e.target.value)}
                                                    className="input-field"
                                                    disabled={!formTeacher || loadingContracts}
                                                >
                                                    <option value="">{loadingContracts ? '載入中...' : '請選擇合約（可選）'}</option>
                                                    {teacherContracts.map(c => (
                                                        <option key={c.id} value={c.id}>{c.contract_no}</option>
                                                    ))}
                                                </select>
                                            </div>

                                            {/* 時段選擇模式切換 */}
                                            <div className="border rounded-lg p-4 bg-gray-50">
                                                <div className="flex items-center gap-4 mb-4">
                                                    <label className="flex items-center gap-2 cursor-pointer">
                                                        <input
                                                            type="radio"
                                                            name="slotMode"
                                                            checked={formUseAutoSlot}
                                                            onChange={() => setFormUseAutoSlot(true)}
                                                            className="w-4 h-4 text-blue-600"
                                                        />
                                                        <span className="text-sm font-medium text-gray-700">自訂時間</span>
                                                    </label>
                                                    <label className="flex items-center gap-2 cursor-pointer">
                                                        <input
                                                            type="radio"
                                                            name="slotMode"
                                                            checked={!formUseAutoSlot}
                                                            onChange={() => setFormUseAutoSlot(false)}
                                                            className="w-4 h-4 text-blue-600"
                                                        />
                                                        <span className="text-sm font-medium text-gray-700">選擇時段</span>
                                                    </label>
                                                </div>

                                                {formUseAutoSlot ? (
                                                    /* 自動尋找時段模式：用戶輸入日期和時間 */
                                                    <div className="space-y-3">
                                                        <p className="text-xs text-gray-500 mb-2">
                                                            系統將自動尋找包含此時間區間的教師可用時段
                                                        </p>
                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                                預約日期 <span className="text-red-500">*</span>
                                                            </label>
                                                            <input
                                                                type="date"
                                                                value={formBookingDate}
                                                                onChange={(e) => setFormBookingDate(e.target.value)}
                                                                className="input-field"
                                                                required={formUseAutoSlot}
                                                                disabled={!formTeacher}
                                                            />
                                                        </div>
                                                        <div className="grid grid-cols-2 gap-3">
                                                            <div>
                                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                                    開始時間 <span className="text-red-500">*</span>
                                                                </label>
                                                                <input
                                                                    type="time"
                                                                    value={formStartTime}
                                                                    onChange={(e) => setFormStartTime(e.target.value)}
                                                                    className="input-field"
                                                                    required={formUseAutoSlot}
                                                                    disabled={!formTeacher}
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
                                                                    required={formUseAutoSlot}
                                                                    disabled={!formTeacher}
                                                                />
                                                            </div>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    /* 手動選擇時段模式 */
                                                    <div className="space-y-3">
                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                                教師時段 <span className="text-red-500">*</span>
                                                            </label>
                                                            <select
                                                                value={formTeacherSlot}
                                                                onChange={(e) => setFormTeacherSlot(e.target.value)}
                                                                className="input-field"
                                                                required={!formUseAutoSlot}
                                                                disabled={!formTeacher || loadingSlots}
                                                            >
                                                                <option value="">{loadingSlots ? '載入中...' : '請選擇時段'}</option>
                                                                {teacherSlots.map(slot => (
                                                                    <option key={slot.id} value={slot.id}>
                                                                        {slot.slot_date} {formatTime(slot.start_time)} - {formatTime(slot.end_time)}{slot.is_booked ? '（已滿）' : ''}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                            {formTeacher && teacherSlots.length === 0 && !loadingSlots && (
                                                                <p className="mt-1 text-sm text-yellow-600">此教師沒有可用時段</p>
                                                            )}
                                                        </div>

                                                        {/* 30 分鐘區塊選擇 */}
                                                        {loadingAvailability && (
                                                            <p className="text-sm text-gray-500">載入時段區塊中...</p>
                                                        )}
                                                        {slotAvailability && slotAvailability.blocks.length > 0 && (
                                                            <div>
                                                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                                                    選擇時間區塊 <span className="text-red-500">*</span>
                                                                    <span className="text-xs text-gray-500 ml-2">（點選起始區塊，再點結束區塊）</span>
                                                                </label>
                                                                <div className="grid grid-cols-4 gap-1.5">
                                                                    {slotAvailability.blocks.map((block, idx) => {
                                                                        const isSelected = selectedBlockStart !== null && selectedBlockEnd !== null &&
                                                                            idx >= selectedBlockStart && idx <= selectedBlockEnd
                                                                        const isBooked = !block.is_available

                                                                        return (
                                                                            <button
                                                                                key={idx}
                                                                                type="button"
                                                                                onClick={() => handleBlockClick(idx)}
                                                                                disabled={isBooked}
                                                                                className={`px-2 py-1.5 text-xs rounded border text-center transition-colors ${
                                                                                    isBooked
                                                                                        ? 'bg-gray-200 text-gray-400 border-gray-200 cursor-not-allowed'
                                                                                        : isSelected
                                                                                        ? 'bg-blue-500 text-white border-blue-500'
                                                                                        : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400 hover:bg-blue-50 cursor-pointer'
                                                                                }`}
                                                                            >
                                                                                {block.start_time.substring(0, 5)}
                                                                                <br />
                                                                                <span className="text-[10px]">{isBooked ? '已預約' : '可用'}</span>
                                                                            </button>
                                                                        )
                                                                    })}
                                                                </div>
                                                                {formStartTime && formEndTime && (
                                                                    <p className="mt-2 text-sm text-blue-600 font-medium">
                                                                        已選擇: {formStartTime} - {formEndTime}
                                                                    </p>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>

                                            {/* Notes */}
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    備註
                                                </label>
                                                <textarea
                                                    value={formNotes}
                                                    onChange={(e) => setFormNotes(e.target.value)}
                                                    className="input-field"
                                                    placeholder="預約備註..."
                                                    rows={3}
                                                />
                                            </div>
                                        </>
                                    ) : (
                                        <>
                                            {/* Edit mode - show booking info */}
                                            <div className="bg-gray-50 p-4 rounded-lg space-y-2">
                                                <p><span className="font-medium">預約編號:</span> {editingBooking?.booking_no}</p>
                                                <p><span className="font-medium">學生:</span> {editingBooking?.student_name}</p>
                                                <p><span className="font-medium">教師:</span> {editingBooking?.teacher_name}</p>
                                                <p><span className="font-medium">課程:</span> {editingBooking?.course_name}</p>
                                                <p><span className="font-medium">日期時間:</span> {editingBooking?.booking_date} {formatTime(editingBooking?.start_time || '')} - {formatTime(editingBooking?.end_time || '')}</p>
                                            </div>

                                            {/* Status select */}
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    狀態 <span className="text-red-500">*</span>
                                                </label>
                                                <select
                                                    value={formStatus}
                                                    onChange={(e) => setFormStatus(e.target.value as BookingStatus)}
                                                    className="input-field"
                                                    required
                                                >
                                                    <option value="pending">待確認</option>
                                                    <option value="confirmed">已確認</option>
                                                    <option value="completed">已完成</option>
                                                    <option value="cancelled">已取消</option>
                                                </select>
                                            </div>

                                            {/* Notes */}
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    備註
                                                </label>
                                                <textarea
                                                    value={formEditNotes}
                                                    onChange={(e) => setFormEditNotes(e.target.value)}
                                                    className="input-field"
                                                    placeholder="預約備註..."
                                                    rows={3}
                                                />
                                            </div>
                                        </>
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
                                            className="btn-primary flex-1"
                                            disabled={submitting}
                                        >
                                            {submitting ? (
                                                <span className="flex items-center justify-center">
                                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                                    處理中...
                                                </span>
                                            ) : modalMode === 'create' ? '建立' : '儲存'}
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
                                確認刪除預約
                            </h3>
                            <p className="text-gray-600 mb-6">
                                確定要刪除預約「<span className="font-medium">{deleteConfirm.booking_no}</span>」嗎？
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

                {/* Batch Update Selected Modal */}
                {showBatchModal === 'update' && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
                            <div className="flex items-center justify-between mb-6">
                                <h3 className="text-lg font-bold text-gray-900">
                                    批次更新 {selectedIds.length} 筆預約
                                </h3>
                                <button onClick={closeBatchModal} className="text-gray-400 hover:text-gray-600">
                                    <X className="w-6 h-6" />
                                </button>
                            </div>

                            {batchError && (
                                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                                    {batchError}
                                </div>
                            )}

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        新狀態 <span className="text-red-500">*</span>
                                    </label>
                                    <select
                                        value={batchStatus}
                                        onChange={(e) => setBatchStatus(e.target.value as BookingStatus)}
                                        className="input-field"
                                    >
                                        <option value="pending">待確認</option>
                                        <option value="confirmed">已確認</option>
                                        <option value="completed">已完成</option>
                                        <option value="cancelled">已取消</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        備註
                                    </label>
                                    <textarea
                                        value={batchNotes}
                                        onChange={(e) => setBatchNotes(e.target.value)}
                                        className="input-field"
                                        placeholder="批次更新備註..."
                                        rows={3}
                                    />
                                </div>
                            </div>

                            <div className="flex gap-3 mt-6">
                                <button
                                    onClick={closeBatchModal}
                                    className="btn-secondary flex-1"
                                    disabled={batchSubmitting}
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleBatchUpdate}
                                    className="btn-primary flex-1"
                                    disabled={batchSubmitting}
                                >
                                    {batchSubmitting ? (
                                        <span className="flex items-center justify-center">
                                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                            處理中...
                                        </span>
                                    ) : '確認更新'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Batch Delete Selected Modal */}
                {showBatchModal === 'delete' && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-2">
                                確認批次刪除
                            </h3>
                            <p className="text-gray-600 mb-6">
                                確定要刪除選中的 <span className="font-medium text-red-600">{selectedIds.length}</span> 筆預約嗎？
                                此操作無法復原。
                            </p>

                            {batchError && (
                                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                                    {batchError}
                                </div>
                            )}

                            <div className="flex gap-3">
                                <button
                                    onClick={closeBatchModal}
                                    className="btn-secondary flex-1"
                                    disabled={batchSubmitting}
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleBatchDelete}
                                    className="btn-danger flex-1"
                                    disabled={batchSubmitting}
                                >
                                    {batchSubmitting ? (
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

                {/* Batch Period Update Modal */}
                {showBatchModal === 'period-update' && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <h3 className="text-xl font-bold text-gray-900">
                                        批次更新預約（週期性）
                                    </h3>
                                    <button onClick={closeBatchModal} className="text-gray-400 hover:text-gray-600">
                                        <X className="w-6 h-6" />
                                    </button>
                                </div>

                                {batchError && (
                                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                                        {batchError}
                                    </div>
                                )}

                                <div className="space-y-4">
                                    <h4 className="font-medium text-gray-900 border-b pb-2">篩選條件</h4>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                開始日期 <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="date"
                                                value={batchStartDate}
                                                onChange={(e) => setBatchStartDate(e.target.value)}
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
                                                value={batchEndDate}
                                                onChange={(e) => setBatchEndDate(e.target.value)}
                                                className="input-field"
                                                required
                                            />
                                        </div>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            星期幾（不選則全部）
                                        </label>
                                        <div className="flex gap-2">
                                            {weekdayLabels.map((label, index) => (
                                                <button
                                                    key={index}
                                                    type="button"
                                                    onClick={() => toggleWeekday(index)}
                                                    className={`w-10 h-10 rounded-full border-2 text-sm font-medium transition-colors ${
                                                        batchWeekdays.includes(index)
                                                            ? 'bg-blue-600 border-blue-600 text-white'
                                                            : 'border-gray-300 text-gray-600 hover:border-blue-400'
                                                    }`}
                                                >
                                                    {label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                篩選學生
                                            </label>
                                            <select
                                                value={batchFilterStudentId}
                                                onChange={(e) => setBatchFilterStudentId(e.target.value)}
                                                className="input-field"
                                            >
                                                <option value="">全部學生</option>
                                                {studentOptions.map(s => (
                                                    <option key={s.id} value={s.id}>{s.name} ({s.student_no})</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                篩選教師
                                            </label>
                                            <select
                                                value={batchFilterTeacherId}
                                                onChange={(e) => setBatchFilterTeacherId(e.target.value)}
                                                className="input-field"
                                            >
                                                <option value="">全部教師</option>
                                                {teacherOptions.map(t => (
                                                    <option key={t.id} value={t.id}>{t.name} ({t.teacher_no})</option>
                                                ))}
                                            </select>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                篩選課程
                                            </label>
                                            <select
                                                value={batchFilterCourseId}
                                                onChange={(e) => setBatchFilterCourseId(e.target.value)}
                                                className="input-field"
                                            >
                                                <option value="">全部課程</option>
                                                {courseOptions.map(c => (
                                                    <option key={c.id} value={c.id}>{c.course_name}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                篩選狀態
                                            </label>
                                            <select
                                                value={batchFilterStatus}
                                                onChange={(e) => setBatchFilterStatus(e.target.value as BookingStatus | '')}
                                                className="input-field"
                                            >
                                                <option value="">全部狀態</option>
                                                <option value="pending">待確認</option>
                                                <option value="confirmed">已確認</option>
                                                <option value="completed">已完成</option>
                                                <option value="cancelled">已取消</option>
                                            </select>
                                        </div>
                                    </div>

                                    <h4 className="font-medium text-gray-900 border-b pb-2 mt-6">更新內容</h4>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            新狀態 <span className="text-red-500">*</span>
                                        </label>
                                        <select
                                            value={batchNewStatus}
                                            onChange={(e) => setBatchNewStatus(e.target.value as BookingStatus)}
                                            className="input-field"
                                        >
                                            <option value="pending">待確認</option>
                                            <option value="confirmed">已確認</option>
                                            <option value="completed">已完成</option>
                                            <option value="cancelled">已取消</option>
                                        </select>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            備註
                                        </label>
                                        <textarea
                                            value={batchPeriodNotes}
                                            onChange={(e) => setBatchPeriodNotes(e.target.value)}
                                            className="input-field"
                                            placeholder="批次更新備註..."
                                            rows={3}
                                        />
                                    </div>
                                </div>

                                <div className="flex gap-3 mt-6">
                                    <button
                                        onClick={closeBatchModal}
                                        className="btn-secondary flex-1"
                                        disabled={batchSubmitting}
                                    >
                                        取消
                                    </button>
                                    <button
                                        onClick={handleBatchPeriodUpdate}
                                        className="btn-primary flex-1"
                                        disabled={batchSubmitting}
                                    >
                                        {batchSubmitting ? (
                                            <span className="flex items-center justify-center">
                                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                                處理中...
                                            </span>
                                        ) : '確認批次更新'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Batch Period Delete Modal */}
                {showBatchModal === 'period-delete' && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <h3 className="text-xl font-bold text-gray-900">
                                        批次刪除預約（週期性）
                                    </h3>
                                    <button onClick={closeBatchModal} className="text-gray-400 hover:text-gray-600">
                                        <X className="w-6 h-6" />
                                    </button>
                                </div>

                                {batchError && (
                                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                                        {batchError}
                                    </div>
                                )}

                                <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800 text-sm">
                                    此操作將刪除符合條件的所有預約，請謹慎操作。
                                </div>

                                <div className="space-y-4">
                                    <h4 className="font-medium text-gray-900 border-b pb-2">篩選條件</h4>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                開始日期 <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="date"
                                                value={batchStartDate}
                                                onChange={(e) => setBatchStartDate(e.target.value)}
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
                                                value={batchEndDate}
                                                onChange={(e) => setBatchEndDate(e.target.value)}
                                                className="input-field"
                                                required
                                            />
                                        </div>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            星期幾（不選則全部）
                                        </label>
                                        <div className="flex gap-2">
                                            {weekdayLabels.map((label, index) => (
                                                <button
                                                    key={index}
                                                    type="button"
                                                    onClick={() => toggleWeekday(index)}
                                                    className={`w-10 h-10 rounded-full border-2 text-sm font-medium transition-colors ${
                                                        batchWeekdays.includes(index)
                                                            ? 'bg-blue-600 border-blue-600 text-white'
                                                            : 'border-gray-300 text-gray-600 hover:border-blue-400'
                                                    }`}
                                                >
                                                    {label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                篩選學生
                                            </label>
                                            <select
                                                value={batchFilterStudentId}
                                                onChange={(e) => setBatchFilterStudentId(e.target.value)}
                                                className="input-field"
                                            >
                                                <option value="">全部學生</option>
                                                {studentOptions.map(s => (
                                                    <option key={s.id} value={s.id}>{s.name} ({s.student_no})</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                篩選教師
                                            </label>
                                            <select
                                                value={batchFilterTeacherId}
                                                onChange={(e) => setBatchFilterTeacherId(e.target.value)}
                                                className="input-field"
                                            >
                                                <option value="">全部教師</option>
                                                {teacherOptions.map(t => (
                                                    <option key={t.id} value={t.id}>{t.name} ({t.teacher_no})</option>
                                                ))}
                                            </select>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                篩選課程
                                            </label>
                                            <select
                                                value={batchFilterCourseId}
                                                onChange={(e) => setBatchFilterCourseId(e.target.value)}
                                                className="input-field"
                                            >
                                                <option value="">全部課程</option>
                                                {courseOptions.map(c => (
                                                    <option key={c.id} value={c.id}>{c.course_name}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                篩選狀態
                                            </label>
                                            <select
                                                value={batchFilterStatus}
                                                onChange={(e) => setBatchFilterStatus(e.target.value as BookingStatus | '')}
                                                className="input-field"
                                            >
                                                <option value="">全部狀態</option>
                                                <option value="pending">待確認</option>
                                                <option value="confirmed">已確認</option>
                                                <option value="completed">已完成</option>
                                                <option value="cancelled">已取消</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex gap-3 mt-6">
                                    <button
                                        onClick={closeBatchModal}
                                        className="btn-secondary flex-1"
                                        disabled={batchSubmitting}
                                    >
                                        取消
                                    </button>
                                    <button
                                        onClick={handleBatchPeriodDelete}
                                        className="btn-danger flex-1"
                                        disabled={batchSubmitting}
                                    >
                                        {batchSubmitting ? (
                                            <span className="flex items-center justify-center">
                                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                                刪除中...
                                            </span>
                                        ) : '確認批次刪除'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Batch Period Create Modal */}
                {showBatchModal === 'period-create' && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <h3 className="text-xl font-bold text-gray-900">
                                        批次新增預約（週期性）
                                    </h3>
                                    <button onClick={closeBatchModal} className="text-gray-400 hover:text-gray-600">
                                        <X className="w-6 h-6" />
                                    </button>
                                </div>

                                {batchError && (
                                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                                        {batchError}
                                    </div>
                                )}

                                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-800 text-sm">
                                    系統將自動尋找教師在指定日期範圍內的可用時段並建立預約。
                                </div>

                                <div className="space-y-4">
                                    <h4 className="font-medium text-gray-900 border-b pb-2">預約資訊</h4>

                                    {/* Student select - hidden for students */}
                                    {isStudent ? (
                                        <div className="bg-gray-50 p-4 rounded-lg">
                                            <p className="text-sm text-gray-600">
                                                <span className="font-medium">學生:</span> {myStudentInfo?.name} ({myStudentInfo?.student_no})
                                            </p>
                                        </div>
                                    ) : (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                學生 <span className="text-red-500">*</span>
                                            </label>
                                            <select
                                                value={batchCreateStudentId}
                                                onChange={(e) => {
                                                    setBatchCreateStudentId(e.target.value)
                                                    setBatchCreateStudentContractId('')
                                                }}
                                                className="input-field"
                                                required
                                            >
                                                <option value="">請選擇學生</option>
                                                {studentOptions.map(s => (
                                                    <option key={s.id} value={s.id}>{s.name} ({s.student_no}){s.student_type === 'trial' ? ' [試上]' : ''}</option>
                                                ))}
                                            </select>
                                        </div>
                                    )}

                                    {/* Teacher select */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            教師 <span className="text-red-500">*</span>
                                        </label>
                                        <select
                                            value={batchCreateTeacherId}
                                            onChange={(e) => {
                                                setBatchCreateTeacherId(e.target.value)
                                                setBatchCreateTeacherContractId('')
                                            }}
                                            className="input-field"
                                            required
                                            disabled={!batchCreateStudentId && !isStudent}
                                        >
                                            <option value="">請選擇教師</option>
                                            {teacherOptions.map(t => (
                                                <option key={t.id} value={t.id}>
                                                    {t.is_primary ? '★ ' : ''}{t.name} ({t.teacher_no}){t.teacher_level ? ` Lv.${t.teacher_level}` : ''}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    {/* Course select - overlapping courses */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            課程 <span className="text-red-500">*</span>
                                        </label>
                                        <select
                                            value={batchCreateCourseId}
                                            onChange={(e) => setBatchCreateCourseId(e.target.value)}
                                            className="input-field"
                                            required
                                            disabled={batchCreateLoadingOverlappingCourses || !batchCreateTeacherId || (!batchCreateStudentId && !isStudent)}
                                        >
                                            <option value="">{batchCreateLoadingOverlappingCourses ? '載入中...' : '請選擇課程'}</option>
                                            {batchCreateOverlappingCourses.map(c => (
                                                <option key={c.id} value={c.id}>{c.course_name} ({c.course_code})</option>
                                            ))}
                                        </select>
                                        {(batchCreateStudentId || isStudent) && batchCreateTeacherId && batchCreateOverlappingCourses.length === 0 && !batchCreateLoadingOverlappingCourses && (
                                            <p className="mt-1 text-sm text-yellow-600">
                                                此學生與教師無共同可選課程
                                            </p>
                                        )}
                                    </div>

                                    {/* Student contract select - filtered by course */}
                                    {!isBatchTrialStudent && (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                學生合約 <span className="text-red-500">*</span>
                                            </label>
                                            <select
                                                value={batchCreateStudentContractId}
                                                onChange={(e) => setBatchCreateStudentContractId(e.target.value)}
                                                className="input-field"
                                                required
                                                disabled={!batchCreateCourseId || batchCreateLoadingContracts}
                                            >
                                                <option value="">{batchCreateLoadingContracts ? '載入中...' : '請選擇合約'}</option>
                                                {batchCreateStudentContracts.map(c => (
                                                    <option key={c.id} value={c.id}>
                                                        {c.contract_no} - {c.course_name} (剩餘 {c.remaining_lessons} 堂)
                                                    </option>
                                                ))}
                                            </select>
                                            {batchCreateCourseId && batchCreateStudentContracts.length === 0 && !batchCreateLoadingContracts && (
                                                <p className="mt-1 text-sm text-yellow-600">
                                                    {isStudent ? '您沒有此課程的有效合約' : '此學生沒有此課程的有效合約'}
                                                </p>
                                            )}
                                        </div>
                                    )}
                                    {isBatchTrialStudent && (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                學生合約
                                                <span className="text-gray-400 text-xs ml-1">（試上學生可不選）</span>
                                            </label>
                                            <select
                                                value={batchCreateStudentContractId}
                                                onChange={(e) => setBatchCreateStudentContractId(e.target.value)}
                                                className="input-field"
                                                disabled={!batchCreateCourseId || batchCreateLoadingContracts}
                                            >
                                                <option value="">{batchCreateLoadingContracts ? '載入中...' : '不選擇合約（試上）'}</option>
                                                {batchCreateStudentContracts.map(c => (
                                                    <option key={c.id} value={c.id}>
                                                        {c.contract_no} - {c.course_name} (剩餘 {c.remaining_lessons} 堂)
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                    )}

                                    {/* Teacher contract select */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            教師合約
                                        </label>
                                        <select
                                            value={batchCreateTeacherContractId}
                                            onChange={(e) => setBatchCreateTeacherContractId(e.target.value)}
                                            className="input-field"
                                            disabled={!batchCreateTeacherId || batchCreateLoadingContracts}
                                        >
                                            <option value="">{batchCreateLoadingContracts ? '載入中...' : '請選擇合約（可選）'}</option>
                                            {batchCreateTeacherContracts.map(c => (
                                                <option key={c.id} value={c.id}>{c.contract_no}</option>
                                            ))}
                                        </select>
                                    </div>

                                    <h4 className="font-medium text-gray-900 border-b pb-2 mt-6">週期設定</h4>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                開始日期 <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="date"
                                                value={batchStartDate}
                                                onChange={(e) => setBatchStartDate(e.target.value)}
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
                                                value={batchEndDate}
                                                onChange={(e) => setBatchEndDate(e.target.value)}
                                                className="input-field"
                                                required
                                            />
                                        </div>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            星期幾 <span className="text-red-500">*</span>
                                        </label>
                                        <div className="flex gap-2">
                                            {weekdayLabels.map((label, index) => (
                                                <button
                                                    key={index}
                                                    type="button"
                                                    onClick={() => toggleWeekday(index)}
                                                    className={`w-10 h-10 rounded-full border-2 text-sm font-medium transition-colors ${
                                                        batchWeekdays.includes(index)
                                                            ? 'bg-blue-600 border-blue-600 text-white'
                                                            : 'border-gray-300 text-gray-600 hover:border-blue-400'
                                                    }`}
                                                >
                                                    {label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                篩選開始時間
                                            </label>
                                            <input
                                                type="time"
                                                value={batchCreateStartTime}
                                                onChange={(e) => setBatchCreateStartTime(e.target.value)}
                                                className="input-field"
                                                placeholder="只匹配此開始時間的時段"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                篩選結束時間
                                            </label>
                                            <input
                                                type="time"
                                                value={batchCreateEndTime}
                                                onChange={(e) => setBatchCreateEndTime(e.target.value)}
                                                className="input-field"
                                                placeholder="只匹配此結束時間的時段"
                                            />
                                        </div>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            備註
                                        </label>
                                        <textarea
                                            value={batchCreateNotes}
                                            onChange={(e) => setBatchCreateNotes(e.target.value)}
                                            className="input-field"
                                            placeholder="批次預約備註..."
                                            rows={3}
                                        />
                                    </div>
                                </div>

                                <div className="flex gap-3 mt-6">
                                    <button
                                        onClick={closeBatchModal}
                                        className="btn-secondary flex-1"
                                        disabled={batchSubmitting}
                                    >
                                        取消
                                    </button>
                                    <button
                                        onClick={handleBatchCreate}
                                        className="btn-primary flex-1"
                                        disabled={batchSubmitting}
                                    >
                                        {batchSubmitting ? (
                                            <span className="flex items-center justify-center">
                                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                                處理中...
                                            </span>
                                        ) : '確認批次新增'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Student Teacher Preferences Panel */}
                {showPrefsPanel && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                                        <Star className="w-5 h-5 text-yellow-500" />
                                        學生教師偏好設定
                                    </h3>
                                    <button onClick={() => { setShowPrefsPanel(false); setShowPrefForm(false) }} className="text-gray-400 hover:text-gray-600">
                                        <X className="w-6 h-6" />
                                    </button>
                                </div>

                                {/* Student selector */}
                                <div className="mb-4">
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        選擇學生
                                    </label>
                                    <select
                                        value={prefsStudentId}
                                        onChange={(e) => { setPrefsStudentId(e.target.value); setShowPrefForm(false) }}
                                        className="input-field"
                                    >
                                        <option value="">請選擇學生</option>
                                        {studentOptions.map(s => (
                                            <option key={s.id} value={s.id}>{s.name} ({s.student_no}){s.student_type === 'trial' ? ' [試上]' : ''}</option>
                                        ))}
                                    </select>
                                </div>

                                {prefError && (
                                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                                        {prefError}
                                    </div>
                                )}

                                {prefsStudentId && (
                                    <>
                                        {/* Preference list */}
                                        {loadingPrefs ? (
                                            <p className="text-gray-500 text-sm">載入中...</p>
                                        ) : (
                                            <div className="space-y-3">
                                                {preferences.length === 0 ? (
                                                    <p className="text-gray-400 text-sm">此學生尚無偏好設定</p>
                                                ) : (
                                                    preferences.map(pref => (
                                                        <div key={pref.id} className="border rounded-lg p-3 flex items-center justify-between">
                                                            <div>
                                                                <p className="text-sm font-medium text-gray-900">
                                                                    {pref.course_name || '全域預設'}
                                                                </p>
                                                                <p className="text-xs text-gray-500">
                                                                    最低等級: Lv.{pref.min_teacher_level}
                                                                    {pref.primary_teacher_name && ` | 主要教師: ${pref.primary_teacher_name}`}
                                                                </p>
                                                            </div>
                                                            <div className="flex items-center gap-2">
                                                                <button
                                                                    onClick={() => openPrefEdit(pref)}
                                                                    className="p-1 text-gray-400 hover:text-blue-600"
                                                                    title="編輯"
                                                                >
                                                                    <Pencil className="w-4 h-4" />
                                                                </button>
                                                                <button
                                                                    onClick={() => handlePrefDelete(pref.id)}
                                                                    className="p-1 text-gray-400 hover:text-red-600"
                                                                    title="刪除"
                                                                >
                                                                    <Trash2 className="w-4 h-4" />
                                                                </button>
                                                            </div>
                                                        </div>
                                                    ))
                                                )}

                                                {!showPrefForm && (
                                                    <button
                                                        onClick={openPrefCreate}
                                                        className="btn-secondary flex items-center gap-2 w-full justify-center"
                                                    >
                                                        <Plus className="w-4 h-4" />
                                                        新增偏好
                                                    </button>
                                                )}
                                            </div>
                                        )}

                                        {/* Preference form */}
                                        {showPrefForm && (
                                            <div className="mt-4 border rounded-lg p-4 bg-gray-50 space-y-3">
                                                <h4 className="font-medium text-gray-900">
                                                    {editingPref ? '編輯偏好' : '新增偏好'}
                                                </h4>

                                                {!editingPref && (
                                                    <div>
                                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                                            課程（不選 = 全域預設）
                                                        </label>
                                                        <select
                                                            value={prefFormCourseId}
                                                            onChange={(e) => setPrefFormCourseId(e.target.value)}
                                                            className="input-field"
                                                        >
                                                            <option value="">全域預設</option>
                                                            {courseOptions.map(c => (
                                                                <option key={c.id} value={c.id}>{c.course_name} ({c.course_code})</option>
                                                            ))}
                                                        </select>
                                                    </div>
                                                )}

                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                        最低教師等級
                                                    </label>
                                                    <input
                                                        type="number"
                                                        min={1}
                                                        value={prefFormMinLevel}
                                                        onChange={(e) => setPrefFormMinLevel(parseInt(e.target.value) || 1)}
                                                        className="input-field"
                                                    />
                                                </div>

                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                        主要教師
                                                    </label>
                                                    <select
                                                        value={prefFormPrimaryTeacherId}
                                                        onChange={(e) => setPrefFormPrimaryTeacherId(e.target.value)}
                                                        className="input-field"
                                                    >
                                                        <option value="">不指定</option>
                                                        {allTeacherOptions.map(t => (
                                                            <option key={t.id} value={t.id}>
                                                                {t.name} ({t.teacher_no}){t.teacher_level ? ` Lv.${t.teacher_level}` : ''}
                                                            </option>
                                                        ))}
                                                    </select>
                                                </div>

                                                <div className="flex gap-3 pt-2">
                                                    <button
                                                        onClick={() => setShowPrefForm(false)}
                                                        className="btn-secondary flex-1"
                                                        disabled={prefSubmitting}
                                                    >
                                                        取消
                                                    </button>
                                                    <button
                                                        onClick={handlePrefSubmit}
                                                        className="btn-primary flex-1"
                                                        disabled={prefSubmitting}
                                                    >
                                                        {prefSubmitting ? '儲存中...' : '儲存'}
                                                    </button>
                                                </div>
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </DashboardLayout>
    )
}
