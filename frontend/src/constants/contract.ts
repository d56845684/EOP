export const CONTRACT_STATUS = {
    ACTIVE: 'active',
    SUSPENDED: 'suspended',
    EXPIRED: 'expired',
    PENDING: 'pending',
    TERMINATED: 'terminated'
} as const

export const CONTRACT_DETAIL_TYPE = {
    LESSON_PRICE: 'lesson_price',
    DISCOUNT: 'discount',
    COMPENSATION: 'compensation'
} as const

export const STUDENT_CONTRACT_STATUS_MAP: Record<string, string> = {
    [CONTRACT_STATUS.PENDING]: '待生效',
    [CONTRACT_STATUS.ACTIVE]: '生效中',
    [CONTRACT_STATUS.EXPIRED]: '已過期',
    [CONTRACT_STATUS.TERMINATED]: '已終止',
    [CONTRACT_STATUS.SUSPENDED]: '已暫停'
};

export const TEACHER_CONTRACT_STATUS_MAP: Record<string, string> = {
    [CONTRACT_STATUS.PENDING]: '待生效',
    [CONTRACT_STATUS.ACTIVE]: '生效中',
    [CONTRACT_STATUS.EXPIRED]: '已過期',
    [CONTRACT_STATUS.TERMINATED]: '已終止'
};