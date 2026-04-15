<template>
  <div class="class-booking">
    <div class="page-title">{{ $t('studentBooking.title') }}</div>

    <!-- 1. Booking Card -->
    <el-card class="booking-card">
        <el-form label-position="top" class="booking-form" :inline="false">
             <el-row :gutter="20">
                <el-col :span="6">
                    <el-form-item :label="$t('studentBooking.labelCourse')">
                         <el-select v-model="bookingForm.courseId" @change="handleCourseChange" style="width: 100%">
                            <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
                         </el-select>
                    </el-form-item>
                </el-col>
                <el-col :span="6">
                     <el-form-item :label="$t('studentBooking.labelTeacher')">
                         <el-select v-model="bookingForm.teacherId" :disabled="!bookingForm.courseId" @change="handleTeacherChange" style="width: 100%">
                            <el-option v-for="t in availableTeachers" :key="t.id" :label="t.name" :value="t.id" />
                         </el-select>
                    </el-form-item>
                </el-col>
                <el-col :span="6">
                    <el-form-item :label="$t('studentBooking.labelDate')">
                         <el-date-picker 
                            v-model="bookingForm.date" 
                            type="date" 
                            :disabled="!bookingForm.teacherId"
                            :disabled-date="disabledDate"
                            @change="handleDateChange"
                            style="width: 100%"
                            value-format="YYYY-MM-DD"
                         />
                    </el-form-item>
                </el-col>
                <el-col :span="6">
                     <el-form-item :label="$t('studentBooking.labelTime')">
                         <el-select v-model="bookingForm.time" :disabled="!bookingForm.date" style="width: 100%">
                             <el-option v-for="t in availableTimes" :key="t" :label="t" :value="t" />
                         </el-select>
                    </el-form-item>
                </el-col>
             </el-row>
             <div class="form-actions">
                 <el-button type="primary" :disabled="!isFormValid" @click="submitBooking">
                    {{ $t('studentBooking.btnBook') }}
                 </el-button>
             </div>
        </el-form>
    </el-card>

    <!-- 2. Upcoming Classes -->
    <div class="section-title">{{ $t('studentBooking.sectionUpcoming') }}</div>
    <el-table :data="upcomingList" style="width: 100%" class="mb-4" stripe>
         <el-table-column :label="$t('teacherRecords.colDate')" width="160">
            <template #default="{ row }">
                {{ formatDateTime(row.time) }}
            </template>
        </el-table-column>
        <el-table-column :label="$t('teacherRecords.colCourse')">
             <template #default="{ row }">
                 {{ getCourseName(row.courseId) }}
             </template>
        </el-table-column>
        <el-table-column :label="$t('teacherRecords.colTeacher')">
            <template #default="{ row }">
                 {{ getTeacherName(row.teacherId) }}
                 <el-tooltip v-if="row.isTeacherChanged" :content="$t('studentBooking.msgTeacherChanged')" placement="top">
                    <el-icon color="orange" style="margin-left: 5px; vertical-align: middle;"><Warning /></el-icon>
                 </el-tooltip>
            </template>
        </el-table-column>
        <el-table-column :label="$t('studentBooking.colZoom')" width="120">
             <template #default="{ row }">
                 <el-link v-if="row.link" :href="row.link" target="_blank" type="primary">Link</el-link>
             </template>
        </el-table-column>
        <el-table-column :label="$t('studentBooking.colMaterial')" width="120">
             <template #default="{ row }">
                 <el-link v-if="row.materialUrl" :href="row.materialUrl" target="_blank" type="primary">Link</el-link>
             </template>
        </el-table-column>
         <el-table-column :label="$t('teacherRecords.colActions')" width="150" align="right">
            <template #default="{ row }">
                 <el-button type="danger" plain size="small" @click="handleCancel(row)">
                    {{ $t('studentBooking.btnCancel') }}
                 </el-button>
            </template>
        </el-table-column>
    </el-table>

    <!-- 3. History -->
    <div class="section-title">{{ $t('studentBooking.sectionHistory') }}</div>
    <el-table :data="historyPaged" style="width: 100%" stripe>
        <el-table-column :label="$t('teacherRecords.colDate')" width="160">
            <template #default="{ row }">
                {{ formatDateTime(row.time) }}
            </template>
        </el-table-column>
        <el-table-column :label="$t('teacherRecords.colCourse')">
             <template #default="{ row }">
                 {{ getCourseName(row.courseId) }}
             </template>
        </el-table-column>
        <el-table-column :label="$t('teacherRecords.colTeacher')">
            <template #default="{ row }">
                 {{ getTeacherName(row.teacherId) }}
            </template>
        </el-table-column>
        <el-table-column :label="$t('studentBooking.colRecord')" width="100">
             <template #default="{ row }">
                 <el-link v-if="row.noteUrl" :href="row.noteUrl" target="_blank" type="primary">
                    <el-icon><VideoPlay /></el-icon>
                 </el-link>
                 <span v-else>-</span>
             </template>
        </el-table-column>
        <el-table-column label="Status" width="120">
             <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
             </template>
        </el-table-column>
    </el-table>

    <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="historyList.length"
          layout="total, prev, pager, next"
        />
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMockStore, type Booking, type Teacher } from '../../stores/mockStore';
import dayjs from 'dayjs';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Warning, VideoPlay } from '@element-plus/icons-vue';

const { t } = useI18n();
const store = useMockStore();

// --- State ---
const upcomingList = ref<Booking[]>([]);
const historyList = ref<Booking[]>([]);
const currentPage = ref(1);
const pageSize = ref(10);

const bookingForm = reactive({
    courseId: '',
    teacherId: '',
    date: '',
    time: ''
});

const availableTeachers = ref<Teacher[]>([]);
const availableTimes = ref<string[]>([]);

// --- Helpers ---
const currentUser = computed(() => store.currentUser);
const currentStudent = computed(() => store.students.find(s => s.id === currentUser.value?.id) || store.students[0]); // fallback for safety
const courses = computed(() => store.courses);

const formatDateTime = (iso: string) => dayjs(iso).format('YYYY-MM-DD HH:mm');
const getCourseName = (id: string) => store.courses.find(c => c.id === id)?.name || id;
const getTeacherName = (id: string) => store.teachers.find(tr => tr.id === id)?.name || id;
const getStatusType = (status: string) => {
    switch(status) {
        case 'Completed': return 'success';
        case 'Cancelled': return 'info';
        case 'Scheduled': return 'primary';
        default: return 'info';
    }
};

// --- Initial Data ---
onMounted(() => {
    generateMockData();
});

const generateMockData = () => {
    // Generate:
    // 2 Upcoming (1 near, 1 far)
    // 1 Upcoming with isTeacherChanged
    // 5 Past
    
    if (!currentUser.value) return;
    
    const now = dayjs();
    const studentId = currentUser.value.id; // Corrected: use current user id
    // Assuming currentUser is s1 for this mock context, or whoever is logged in.
    
    const mockUpcoming: any[] = [
        {
            id: 'u1-near',
            time: now.add(2, 'hour').toISOString(), // Near (<24h, >30m)
            studentId, teacherId: 't1', courseId: 'c1', type: 'Regular', status: 'Scheduled',
            link: 'https://zoom.us/j/123456', materialUrl: 'https://materials.com/1'
        },
        {
            id: 'u2-far',
            time: now.add(3, 'day').hour(10).minute(0).toISOString(), // Far (>24h)
            studentId, teacherId: 't2', courseId: 'c2', type: 'Regular', status: 'Scheduled',
            link: 'https://zoom.us/j/789012', 
        },
        {
            id: 'u3-changed',
            time: now.add(5, 'day').hour(14).minute(0).toISOString(),
            studentId, teacherId: 't1', courseId: 'c1', type: 'Regular', status: 'Scheduled',
            isTeacherChanged: true
        }
    ];
    
    const mockHistory: Booking[] = Array.from({ length: 5 }).map((_, i) => ({
        id: `h-${i}`,
        time: now.subtract(i + 1, 'day').hour(10).toISOString(),
        studentId, teacherId: 't1', courseId: 'c1', type: 'Regular', status: 'Completed',
        noteUrl: i % 2 === 0 ? 'https://video.com/rec' : undefined
    }));

    upcomingList.value = mockUpcoming;
    historyList.value = mockHistory;
};

// --- Computed ---
const historyPaged = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value;
    return historyList.value.slice(start, start + pageSize.value);
});

// --- Booking Logic ---
const handleCourseChange = () => {
    bookingForm.teacherId = '';
    bookingForm.date = '';
    bookingForm.time = '';
    
    // Filter teachers who teach this course (mock: enabled for all or filtered)
    // Mock: All teachers teach all courses for simplicity, or random subset
    availableTeachers.value = store.teachers;
};

const handleTeacherChange = () => {
    bookingForm.date = '';
    bookingForm.time = '';
    // Enable Date Picker
};

const handleDateChange = () => {
    bookingForm.time = '';
    // Generate slots
    const slots = ['10:00', '11:00', '14:00', '15:00', '16:00', '19:00', '20:00'];
    // Filter out if past
    availableTimes.value = slots;
};

const disabledDate = (time: Date) => {
    const d = dayjs(time);
    return d.isBefore(dayjs(), 'day') || d.isAfter(dayjs().add(14, 'day'));
};

const isFormValid = computed(() => {
    return bookingForm.courseId && bookingForm.teacherId && bookingForm.date && bookingForm.time;
});

const submitBooking = () => {
    if (isFormValid.value && currentUser.value) {
        // Validation: Credit?
        const student = currentStudent.value;
        if (student && student.credits <= 0) {
            ElMessage.error('Insufficient credits');
            return;
        }

        // Add to Upcoming
        const newBooking: any = {
            id: `new-${Date.now()}`,
            time: `${bookingForm.date}T${bookingForm.time}:00`,
            studentId: currentUser.value.id,
            teacherId: bookingForm.teacherId,
            courseId: bookingForm.courseId,
            type: 'Regular',
            status: 'Scheduled',
            createdAt: dayjs().toISOString()
        };
        
        upcomingList.value.push(newBooking);
        upcomingList.value.sort((a,b) => dayjs(a.time).diff(dayjs(b.time)));
        
        // Deduct Credit (Mock)
        if (student) student.credits--;
        
        ElMessage.success(t('studentBooking.msgBookSuccess'));
        
        // Reset
        bookingForm.courseId = '';
        bookingForm.teacherId = '';
        bookingForm.date = '';
        bookingForm.time = '';
    }
};

// --- Cancellation Logic ---
const handleCancel = (row: any) => {
    const classTime = dayjs(row.time);
    const now = dayjs();
    const diffMins = classTime.diff(now, 'minute');
    const student = currentStudent.value;
    
    // Rule 1: < 30 mins
    if (diffMins < 30) {
        ElMessage.error(t('studentBooking.errorTooLate'));
        return;
    }
    
    // Rule 2: 30m <= diff < 24h (Late Cancel)
    if (diffMins >= 30 && diffMins < 1440) {
        if (!student) return;
        
        if (student.lateCancelCount >= student.maxLateCancel) {
             ElMessageBox.alert(t('studentBooking.errorLimitExceeded'), 'Error', {
                confirmButtonText: 'OK',
                type: 'error'
             });
             return;
        }
        
        ElMessageBox.confirm(
            t('studentBooking.confirmLateCancel'),
            'Confirm Late Cancellation',
            {
                confirmButtonText: t('common.confirm'),
                cancelButtonText: t('common.cancel'),
                type: 'warning'
            }
        ).then(() => {
            // Execute Late Cancel
            performCancel(row, true);
        });
    }
    // Rule 3: >= 24h (Regular Cancel)
    else {
        ElMessageBox.confirm(
            t('studentBooking.confirmCancel'),
            'Confirm Cancellation',
            {
                confirmButtonText: t('common.confirm'),
                cancelButtonText: t('common.cancel'),
                type: 'info'
            }
        ).then(() => {
            performCancel(row, false);
        });
    }
};

const performCancel = (row: any, isLate: boolean) => {
    // 1. Remove from Upcoming
    upcomingList.value = upcomingList.value.filter(b => b.id !== row.id);
    
    // 2. Add to History
    row.status = 'Cancelled';
    historyList.value.unshift(row);
    
    // 3. Update Student Limits/Credits
    const student = currentStudent.value;
    if (student) {
        if (isLate) {
            student.lateCancelCount++;
        } else {
            student.credits++; // Return credit
        }
    }
    
    ElMessage.success(t('studentBooking.msgCancelSuccess'));
};

</script>

<style scoped lang="scss">
.class-booking {
    padding: 20px;
}

.page-title {
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 20px;
}

.section-title {
    font-size: 18px;
    font-weight: bold;
    margin: 30px 0 15px;
    border-left: 4px solid var(--el-color-primary);
    padding-left: 10px;
}

.booking-card {
    margin-bottom: 20px;
}

.form-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 20px;
}

.pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
}

.mb-4 {
    margin-bottom: 16px;
}
</style>
