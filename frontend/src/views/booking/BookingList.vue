<template>
  <div class="booking-list">
    <!-- Search / Filter Bar -->
    <el-card class="mb-20">
      <div class="filter-row">
        <!-- 1. Date Range -->
        <el-date-picker
          v-model="filters.dateRange"
          type="daterange"
          range-separator="To"
          :start-placeholder="$t('common.startDate')"
          :end-placeholder="$t('common.endDate')"
          style="width: 260px"
          clearable
          @change="handleFilterChange"
        />
        <!-- 2. Teacher -->
        <el-select v-model="filters.teacherId" :placeholder="$t('common.teacher')" clearable style="width: 150px" filterable @change="handleFilterChange">
          <el-option v-for="t in teachers" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
        <!-- 3. Student -->
        <el-select v-model="filters.studentId" :placeholder="$t('common.student')" clearable style="width: 150px" filterable @change="handleFilterChange">
          <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <!-- 4. Status -->
        <el-select v-model="filters.status" :placeholder="$t('common.status')" clearable style="width: 120px" @change="handleFilterChange">
          <el-option label="All Status" value="" />
          <el-option label="Pending" value="pending" />
          <el-option label="Confirmed" value="confirmed" />
          <el-option label="Completed" value="completed" />
          <el-option label="Cancelled" value="cancelled" />
        </el-select>
        <!-- 5. Course Type -->
        <el-select v-model="filters.type" :placeholder="$t('common.type')" clearable style="width: 120px" @change="handleFilterChange">
           <el-option label="All Types" value="" />
           <el-option label="Regular" value="Regular" />
           <el-option label="Trial" value="Trial" />
        </el-select>

        <div class="spacer"></div>
        <el-button type="primary" :icon="Plus" @click="openDrawer(null)">{{ $t('booking.add') }}</el-button>
      </div>
    </el-card>

    <!-- Table -->
    <el-card>
      <el-table :data="tableData" style="width: 100%" v-loading="loading" stripe>
        <!-- Col 1: Date -->
        <el-table-column :label="$t('salary.dateTime')" width="120">
            <template #default="{ row }">{{ row.booking_date }}</template>
        </el-table-column>
        <!-- Col 2: Time -->
        <el-table-column label="Time" width="140">
            <template #default="{ row }">
                {{ row.start_time ? row.start_time.substring(0, 5) : '' }} - {{ row.end_time ? row.end_time.substring(0, 5) : '' }}
            </template>
        </el-table-column>
        <!-- Col 3: Teacher -->
        <el-table-column :label="$t('common.teacher')" min-width="180">
             <template #default="{ row }">{{ row.teacher_name || getTeacherName(row.teacher_id) }}</template>
        </el-table-column>
        <!-- Col 4: Student -->
        <el-table-column :label="$t('common.student')" min-width="180">
             <template #default="{ row }">
                 <span>{{ row.student_name || getStudentName(row.student_id) }}</span>
                 <el-tag size="small" :type="getStudentType(row.student_id) === 'Regular' ? 'success' : 'warning'" effect="plain" class="ml-2">
                     {{ getStudentType(row.student_id) }}
                 </el-tag>
             </template>
        </el-table-column>
        <!-- Col 5: Course -->
        <el-table-column :label="$t('common.course')" min-width="150">
             <template #default="{ row }">{{ row.course_name || getCourseName(row.course_id) }}</template>
        </el-table-column>
        <!-- Col 6: Type -->
        <el-table-column :label="$t('common.type')" width="100">
             <template #default="{ row }">
                 <el-tag :type="row.type === 'Trial' ? 'warning' : ''" effect="dark">{{ row.type || 'Regular' }}</el-tag>
             </template>
        </el-table-column>
        <!-- Col 7: Status -->
        <el-table-column :label="$t('common.status')" width="110">
             <template #default="{ row }">
                 <el-tag :type="getStatusColor(row.booking_status)">{{ row.booking_status }}</el-tag>
             </template>
        </el-table-column>
        <!-- Col 8: Trial Verify -->
        <el-table-column :label="$t('booking.trialVerify')" width="120" align="center">
            <template #default="{ row }">
                <span>--</span>
            </template>
        </el-table-column>
        <!-- Col 9: Actions -->
        <el-table-column :label="$t('common.actions')" width="180" fixed="right">
            <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openDrawer(row)">{{ $t('common.edit') }}</el-button>
                <el-button 
                    v-if="row.booking_status === 'pending' || row.booking_status === 'confirmed'" 
                    link 
                    type="warning" 
                    size="small" 
                    @click="handleCancel(row)"
                >
                    {{ $t('common.cancel') }}
                </el-button>
                <el-button 
                    v-if="row.booking_status === 'cancelled'" 
                    link 
                    type="danger" 
                    size="small" 
                    @click="handleDelete(row)"
                >
                    {{ $t('common.delete') }}
                </el-button>
            </template>
        </el-table-column>
      </el-table>

      <div class="pagination-footer">
        <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="total"
            @current-change="handlePaginationChange"
            @size-change="handleFilterChange"
        />
      </div>
    </el-card>

    <!-- Drawer -->
    <el-drawer v-model="drawerVisible" :title="form.id ? $t('booking.editTitle') : $t('booking.add')" size="550px">
        <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
            
            <!-- 1. Student -->
            <el-form-item :label="$t('common.student')" prop="studentId">
                <el-select v-model="form.studentId" filterable placeholder="Select Student" @change="handleStudentChange" style="width: 100%">
                    <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
                </el-select>
                <div v-if="selectedStudentCredits !== null" class="info-text">
                    Current Credits: {{ selectedStudentCredits }}
                </div>
            </el-form-item>

            <!-- 2. Course Type -->
            <el-form-item :label="$t('salary.classType')" prop="type">
                <el-radio-group v-model="form.type" @change="handleTypeChange">
                    <el-radio label="Regular">Regular</el-radio>
                    <el-radio label="Trial">Trial</el-radio>
                </el-radio-group>
            </el-form-item>

            <!-- 3. Course -->
            <el-form-item :label="$t('common.course')" prop="courseId">
                <el-select v-model="form.courseId" filterable placeholder="Select Course" @change="handleCourseChange" style="width: 100%">
                    <el-option v-for="c in availableCourses" :key="c.id" :label="c.name" :value="c.id" />
                </el-select>
            </el-form-item>

            <!-- 4. Teacher -->
            <el-form-item :label="$t('common.teacher')" prop="teacherId">
                <el-select v-model="form.teacherId" filterable placeholder="Select Teacher" @change="clearConflictError" style="width: 100%">
                    <el-option v-for="t in availableTeachers" :key="t.id" :label="t.name" :value="t.id" />
                </el-select>
            </el-form-item>

            <!-- 5. Date -->
            <el-form-item label="Date" prop="date">
                 <el-date-picker v-model="formDate" type="date" placeholder="Select Date" style="width: 100%" @change="clearConflictError" />
            </el-form-item>

            <!-- 6. Time -->
            <el-form-item label="Time" prop="timeStr">
                 <el-time-select
                    v-model="formTimeStr"
                    start="08:00"
                    step="00:30"
                    end="22:00"
                    placeholder="Select Time"
                    style="width: 100%"
                    @change="clearConflictError"
                 />
            </el-form-item>

            <!-- 7. Duration -->
            <el-form-item :label="$t('course.duration')">
                <div class="info-text" v-if="selectedCourseDuration">
                  {{ selectedCourseDuration }} mins (Fixed by Course)
                </div>
                <div v-else class="info-text">Select a course first</div>
            </el-form-item>

            <!-- 8. Meeting Link -->
            <el-form-item :label="$t('booking.meetingLink')" prop="link">
                <el-input v-model="form.link" placeholder="Zoom/Google Meet Link" />
            </el-form-item>

            <!-- 9. Note -->
            <el-form-item :label="$t('common.note')" prop="note">
                <el-input v-model="form.note" type="textarea" />
            </el-form-item>

            <!-- Error Display -->
            <el-alert v-if="conflictError" :title="conflictError" type="error" show-icon :closable="false" class="mt-10" />

        </el-form>
        <template #footer>
            <el-button @click="drawerVisible = false">{{ $t('common.cancel') }}</el-button>
            <el-button type="primary" @click="handleSave" :loading="saving">{{ $t('common.save') }}</el-button>
        </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick, onMounted } from 'vue';
import { useMockStore, type Course } from '../../stores/mockStore';
import dayjs from 'dayjs';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { Plus, Check } from '@element-plus/icons-vue';
import { getBookingList, type BookingItem, type BookingListParams } from '@/api/booking';

const store = useMockStore();
const loading = ref(false);
const saving = ref(false);

const teachers = computed(() => store.teachers);
const students = computed(() => store.students);
const courses = computed(() => store.courses);

const tableData = ref<BookingItem[]>([]);
const total = ref(0);

// --- Filters ---
const filters = reactive({
    dateRange: [] as [string, string] | [],
    teacherId: '',
    studentId: '',
    status: '',
    type: ''
});

// --- Pagination ---
const currentPage = ref(1);
const pageSize = ref(10);

const fetchData = async () => {
    loading.value = true;
    try {
        const params: BookingListParams = {
            page: currentPage.value,
            per_page: pageSize.value,
            teacher_id: filters.teacherId || undefined,
            student_id: filters.studentId || undefined,
            booking_status: filters.status ? (filters.status.toLowerCase() as any) : undefined,
        };
        if (filters.dateRange && filters.dateRange.length === 2 && filters.dateRange[0]) {
            params.date_from = dayjs(filters.dateRange[0]).format('YYYY-MM-DD');
            params.date_to = dayjs(filters.dateRange[1]).format('YYYY-MM-DD');
        }
        
        const res = await getBookingList(params);
        tableData.value = res.data;
        total.value = res.total;
    } catch (e: any) {
        console.error(e);
        ElMessage.error(e.response?.data?.message || 'Failed to fetch bookings');
    } finally {
        loading.value = false;
    }
};

onMounted(() => {
    fetchData();
});

const handleFilterChange = () => {
    currentPage.value = 1;
    fetchData();
};

const handlePaginationChange = () => {
    fetchData();
};

// --- Drawer State ---
const drawerVisible = ref(false);
const formRef = ref<FormInstance>();
const conflictError = ref('');

// Form Booking Interface for Drawer
interface FormBooking {
    id: string;
    studentId: string;
    type: string;
    courseId: string;
    teacherId: string;
    time: string;
    duration?: number;
    link: string;
    note: string;
    status: string;
    isConverted: boolean;
}

const form = reactive<Partial<FormBooking>>({
    id: '',
    studentId: '',
    type: 'Regular',
    courseId: '',
    teacherId: '',
    time: '',
    link: '',
    note: '',
    status: 'Scheduled',
    isConverted: false
});

const formDate = ref('');
const formTimeStr = ref('');

const rules = reactive<FormRules>({
    studentId: [{ required: true, message: 'Required' }],
    type: [{ required: true, message: 'Required' }],
    courseId: [{ required: true, message: 'Required' }],
    teacherId: [{ required: true, message: 'Required' }],
    date: [{ required: true, message: 'Required', trigger: 'change', validator: (r,v,c) => formDate.value ? c() : c(new Error('Required')) }],
    timeStr: [{ required: true, message: 'Required', trigger: 'change', validator: (r,v,c) => formTimeStr.value ? c() : c(new Error('Required')) }]
});

// --- Drawer Logic & Computed ---
const selectedStudentCredits = computed(() => {
    if (!form.studentId) return null;
    const s = students.value.find(x => x.id === form.studentId);
    return s ? s.credits : 0;
});

const selectedCourseDuration = computed(() => {
    if (!form.courseId) return 0;
    const c = courses.value.find(x => x.id === form.courseId);
    return c ? c.duration : 0;
});

const availableCourses = computed(() => {
    if (!form.studentId) return [];
    if (form.type === 'Trial') {
        return courses.value;
    } else {
        const s = students.value.find(x => x.id === form.studentId);
        if (!s || !s.purchasedCourses) return [];
        return s.purchasedCourses.map(pc => courses.value.find(c => c.id === pc.courseId)).filter(Boolean) as Course[];
    }
});

const availableTeachers = computed(() => {
    if (!form.courseId) return [];
    return teachers.value.filter(t => t.courseIds?.includes(form.courseId!));
});

// --- Handlers ---
const openDrawer = (row: any | null) => {
    conflictError.value = '';
    if (row) {
        Object.assign(form, JSON.parse(JSON.stringify({
            id: row.id,
            studentId: row.student_id,
            type: row.type || 'Regular',
            courseId: row.course_id,
            teacherId: row.teacher_id,
            time: row.booking_date + 'T' + row.start_time,
            duration: 50,
            link: row.notes || '',
            note: row.notes || '',
            status: row.booking_status,
            isConverted: false
        })));
        const d = dayjs(form.time);
        formDate.value = d.format('YYYY-MM-DD');
        formTimeStr.value = row.start_time ? row.start_time.substring(0, 5) : d.format('HH:mm');
    } else {
        Object.assign(form, {
            id: '',
            studentId: '',
            type: 'Regular',
            courseId: '',
            teacherId: '',
            time: '',
            duration: 50,
            link: '',
            note: '',
            status: 'Scheduled',
            isConverted: false
        });
        formDate.value = '';
        formTimeStr.value = '';
    }
    drawerVisible.value = true;
    nextTick(() => {
        formRef.value?.clearValidate();
    });
};

const handleStudentChange = () => { form.courseId = ''; form.teacherId = ''; };
const handleTypeChange = () => { form.courseId = ''; form.teacherId = ''; };
const handleCourseChange = () => { form.teacherId = ''; };

watch(() => form.teacherId, (newVal) => {
    if (newVal) {
        const t = teachers.value.find(x => x.id === newVal);
        if (t && t.zoomLink) { form.link = t.zoomLink; }
    }
});

const clearConflictError = () => { conflictError.value = ''; };

const handleSave = async () => {
    drawerVisible.value = false;
    ElMessage.success('Saved locally for prototype (API save not implemented array)');
    fetchData();
};

const handleCancel = (row: BookingItem) => {
    ElMessageBox.confirm('Are you sure you want to cancel this class?', 'Cancel Booking', {
        confirmButtonText: 'Yes, Cancel',
        cancelButtonText: 'No',
        type: 'warning'
    }).then(() => {
        ElMessage.warning('Cancel API not yet implemented in this step');
    });
};

const handleDelete = (row: BookingItem) => {
     ElMessageBox.confirm('Delete this record permanently?', 'Delete', {
         type: 'error'
     }).then(() => {
         ElMessage.warning('Delete API not yet implemented in this step');
     });
};

// --- Helpers ---
const getTeacherName = (id: string) => teachers.value.find(t => t.id === id)?.name || id;
const getStudentName = (id: string) => students.value.find(s => s.id === id)?.name || id;
const getStudentType = (id: string) => students.value.find(s => s.id === id)?.type || 'Regular';
const getCourseName = (id: string) => courses.value.find(c => c.id === id)?.name || id;
const getStatusColor = (status: string) => {
    switch (status) {
        case 'completed': return 'success';
        case 'cancelled': return 'info';
        case 'confirmed': return 'primary';
        case 'pending': return 'warning';
        default: return '';
    }
};

</script>

<style scoped>
.booking-list { padding: 20px; }
.mb-20 { margin-bottom: 20px; }
.filter-row { display: flex; gap: 10px; flex-wrap: wrap; }
.spacer { flex: 1; }
.pagination-footer { margin-top: 20px; display: flex; justify-content: flex-end; }
.text-success { color: #67C23A; }
.ml-2 { margin-left: 8px; }
.mt-10 { margin-top: 10px; }
.info-text { font-size: 12px; color: #909399; margin-top: 5px; }
</style>
