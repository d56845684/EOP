export const BOOKING_STATUS = {
    PENDING: 'pending',
    CONFIRMED: 'confirmed',
    COMPLETED: 'completed',
    CANCELLED: 'cancelled'
} as const

export const BOOING_TYPE = {
    REGULAR: 'regular',
    TRIAL: 'trial',
} as const

export const BOOKING_STATUS_MAP: Record<string, string> = {
    [BOOKING_STATUS.PENDING]: '待確認',
    [BOOKING_STATUS.CONFIRMED]: '已確認',
    [BOOKING_STATUS.COMPLETED]: '已完成',
    [BOOKING_STATUS.CANCELLED]: '已取消'
}

export const BOOKING_TYPE_MAP: Record<string, string> = {
    [BOOING_TYPE.REGULAR]: '正式課',
    [BOOING_TYPE.TRIAL]: '試上課'
}