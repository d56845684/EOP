export const STUDENT_TYPE = {
    NORMAL: 'normal',
    TRIAL: 'trial'
} as const

export const STUDENT_STATUS = {
    ACTIVE: 'active', //課程中
    TERMINATED: 'terminated', //解約
    TRIAL: 'trial' //試上
} as const