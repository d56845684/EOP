<template>
  <div class="booking-list px-5 py-5">
    <!-- Filter Bar -->
    <el-card shadow="never" class="mb-4">
      <el-form :inline="true" :model="filters" size="small" label-position="top" class="flex flex-wrap items-end gap-x-3">
        <!-- 關鍵字 -->
        <el-form-item label="關鍵字">
          <el-input
            v-model="filters.search"
            placeholder="搜尋編號、姓名"
            clearable
            class="h-30px! w-200px!"
            @clear="handleFilterChange"
            @keyup.enter="handleFilterChange"
          >
            <template #prefix><div class="i-hugeicons:search-01" /></template>
          </el-input>
        </el-form-item>
        <!-- 日期範圍 -->
        <el-form-item :label="$t('common.dateRange')">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="~"
            :start-placeholder="$t('common.startDate')"
            :end-placeholder="$t('common.endDate')"
            class="w-240px! h-30px!"
            clearable
            @change="handleFilterChange"
          />
        </el-form-item>
        <!-- 教師 -->
        <el-form-item :label="$t('common.teacher')">
          <el-select
            v-model="filters.teacherId"
            :placeholder="$t('common.all')"
            clearable
            filterable
            class="w-140px!"
            @change="handleFilterChange"
          >
            <el-option v-for="t in teacherOptions" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <!-- 學生 -->
        <el-form-item :label="$t('common.student')">
          <el-select
            v-model="filters.studentId"
            :placeholder="$t('common.all')"
            clearable
            filterable
            class="w-140px!"
            @change="handleFilterChange"
          >
            <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <!-- 狀態 -->
        <el-form-item :label="$t('common.status')">
          <el-select v-model="filters.status" :placeholder="$t('common.all')" clearable class="w-110px!" @change="handleFilterChange">
            <el-option label="Pending" value="pending" />
            <el-option label="Confirmed" value="confirmed" />
            <el-option label="Completed" value="completed" />
            <el-option label="Cancelled" value="cancelled" />
          </el-select>
        </el-form-item>
        <!-- 課程 -->
        <el-form-item label="課程">
          <el-select v-model="filters.courseId" placeholder="全部" clearable filterable class="w-160px!" @change="handleFilterChange">
            <el-option v-for="c in courseOptions" :key="c.id" :label="c.course_name" :value="c.id" />
          </el-select>
        </el-form-item>

        <el-form-item label=" " class="ml-auto">
          <el-button type="primary" round size="small" class="py-3!" @click="handleFilterChange">
            <template #icon><div class="i-hugeicons:search-01" /></template>
            搜尋
          </el-button>
          <el-button round size="small" class="py-3!" @click="handleReset">
            <template #icon><div class="i-hugeicons:arrow-reload-horizontal" /></template>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Table -->
    <el-card shadow="never">
      <el-table :data="tableData" style="width: 100%" v-loading="loading" stripe size="small">
        <!-- 日期 -->
        <el-table-column :label="$t('salary.dateTime')" width="105">
          <template #default="{ row }">{{ row.booking_date }}</template>
        </el-table-column>
        <!-- 時段 -->
        <el-table-column label="時段" width="120">
          <template #default="{ row }">
            {{ row.start_time ? row.start_time.substring(0, 5) : '' }} - {{ row.end_time ? row.end_time.substring(0, 5) : '' }}
          </template>
        </el-table-column>
        <!-- 教師 -->
        <el-table-column :label="$t('common.teacher')" min-width="120">
          <template #default="{ row }">{{ row.teacher_name || '-' }}</template>
        </el-table-column>
        <!-- 學生 -->
        <el-table-column :label="$t('common.student')" min-width="120">
          <template #default="{ row }">{{ row.student_name || '-' }}</template>
        </el-table-column>
        <!-- 課程 -->
        <el-table-column :label="$t('common.course')" min-width="140">
          <template #default="{ row }">{{ row.course_name || '-' }}</template>
        </el-table-column>
        <!-- 類型 -->
        <el-table-column :label="$t('common.type')" width="90">
          <template #default="{ row }">
            <el-tag :type="row.booking_type === 'trial' ? 'warning' : ''" effect="plain" size="small">
              {{ row.booking_type || 'regular' }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 狀態 -->
        <el-table-column :label="$t('common.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusColor(row.booking_status)" size="small">{{ row.booking_status }}</el-tag>
          </template>
        </el-table-column>
        <!-- Zoom -->
        <el-table-column label="Zoom" width="150" align="center">
          <template #default="{ row }">
            <div class="flex flex-col items-center gap-1">
              <!-- 加入會議 -->
              <el-button
                size="small"
                type="primary"
                plain
                round
                :loading="zoomLoadingMap[row.id]"
                class="text-10px! h-22px! px-2!"
                @click="handleJoinMeeting(row.id)"
              >
                <template #icon><div class="i-hugeicons:video-01" /></template>
                加入會議
              </el-button>
              <span v-if="zoomPasscodeMap[row.id]" class="text-10px color-gray-400">
                密碼：{{ zoomPasscodeMap[row.id] }}
              </span>
              <!-- 取得錄影 -->
              <el-button
                size="small"
                plain
                round
                :loading="recordingLoadingMap[row.id]"
                class="text-10px! h-22px! px-2!"
                @click="handleFetchRecording(row.id)"
              >
                <template #icon><div class="i-hugeicons:play-circle" /></template>
                取得錄影
              </el-button>
            </div>
          </template>
        </el-table-column>
        <!-- 操作 -->
        <el-table-column :label="$t('common.actions')" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDrawer(row)">{{ $t('common.edit') }}</el-button>
            <el-button
              v-if="row.booking_status === 'pending' || row.booking_status === 'confirmed'"
              link type="warning" size="small"
              @click="handleCancel(row)"
            >
              {{ $t('common.cancel') }}
            </el-button>
            <el-button
              v-if="row.booking_status === 'cancelled'"
              link type="danger" size="small"
              @click="handleDelete(row)"
            >
              {{ $t('common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="flex justify-end mt-4">
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
        <el-form-item :label="$t('common.student')" prop="studentId">
          <el-select v-model="form.studentId" filterable placeholder="Select Student" @change="handleStudentChange" style="width: 100%">
            <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('salary.classType')" prop="type">
          <el-radio-group v-model="form.type" @change="handleTypeChange">
            <el-radio label="Regular">Regular</el-radio>
            <el-radio label="Trial">Trial</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('common.course')" prop="courseId">
          <el-select v-model="form.courseId" filterable placeholder="Select Course" @change="handleCourseChange" style="width: 100%">
            <el-option v-for="c in availableCourses" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('common.teacher')" prop="teacherId">
          <el-select v-model="form.teacherId" filterable placeholder="Select Teacher" @change="clearConflictError" style="width: 100%">
            <el-option v-for="t in availableTeachers" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Date" prop="date">
          <el-date-picker v-model="formDate" type="date" placeholder="Select Date" style="width: 100%" @change="clearConflictError" />
        </el-form-item>
        <el-form-item label="Time" prop="timeStr">
          <el-time-select v-model="formTimeStr" start="08:00" step="00:30" end="22:00" placeholder="Select Time" style="width: 100%" @change="clearConflictError" />
        </el-form-item>
        <el-form-item :label="$t('course.duration')">
          <div class="info-text" v-if="selectedCourseDuration">{{ selectedCourseDuration }} mins</div>
          <div v-else class="info-text">Select a course first</div>
        </el-form-item>
        <el-form-item :label="$t('booking.meetingLink')" prop="link">
          <el-input v-model="form.link" placeholder="Zoom/Google Meet Link" />
        </el-form-item>
        <el-form-item :label="$t('common.note')" prop="note">
          <el-input v-model="form.note" type="textarea" />
        </el-form-item>
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
import { getBookingList, getBookingCourseOptions, type BookingItem, type BookingListParams, type BookingCourseOption } from '@/api/booking';
import { getBookingTeacherOptions, type BookingTeacherOption } from '@/api/booking';
import { getZoomMeetingByBooking, fetchZoomRecording } from '@/api/zoom';

const store = useMockStore();
const loading = ref(false);
const saving = ref(false);

const students = computed(() => store.students);
const courses = computed(() => store.courses);

const tableData = ref<BookingItem[]>([]);
const total = ref(0);

// --- Options ---
const teacherOptions = ref<BookingTeacherOption[]>([]);
const courseOptions = ref<BookingCourseOption[]>([]);

const loadOptions = async () => {
  try {
    const [tRes, cRes] = await Promise.all([
      getBookingTeacherOptions(),
      getBookingCourseOptions(),
    ]);
    teacherOptions.value = tRes.data || [];
    courseOptions.value = cRes.data || [];
  } catch (e) {
    console.error('Failed to load filter options', e);
  }
};

// --- Filters ---
const filters = reactive({
  search: '',
  dateRange: [] as [string, string] | [],
  teacherId: '',
  studentId: '',
  status: '',
  courseId: '',
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
      search: filters.search || undefined,
      teacher_id: filters.teacherId || undefined,
      student_id: filters.studentId || undefined,
      course_id: filters.courseId || undefined,
      booking_status: filters.status ? (filters.status as any) : undefined,
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
    ElMessage.error(e.response?.data?.message || '載入預約列表失敗');
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadOptions();
  fetchData();
});

const handleFilterChange = () => {
  currentPage.value = 1;
  fetchData();
};

const handleReset = () => {
  filters.search = '';
  filters.dateRange = [];
  filters.teacherId = '';
  filters.studentId = '';
  filters.status = '';
  filters.courseId = '';
  handleFilterChange();
};

const handlePaginationChange = () => { fetchData(); };

// --- Zoom ---
const zoomLoadingMap = reactive<Record<string, boolean>>({});
const recordingLoadingMap = reactive<Record<string, boolean>>({});
const zoomPasscodeMap = reactive<Record<string, string>>({});

const handleJoinMeeting = async (bookingId: string) => {
  zoomLoadingMap[bookingId] = true;
  try {
    const res = await getZoomMeetingByBooking(bookingId);
    const meeting = res.data;
    if (meeting?.join_url) {
      zoomPasscodeMap[bookingId] = meeting.passcode || '';
      window.open(meeting.join_url, '_blank');
    } else {
      ElMessage.warning('尚無 Zoom 會議連結');
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '取得 Zoom 會議失敗');
  } finally {
    zoomLoadingMap[bookingId] = false;
  }
};

const handleFetchRecording = async (bookingId: string) => {
  recordingLoadingMap[bookingId] = true;
  try {
    const res = await fetchZoomRecording(bookingId);
    const meeting = res.data;
    if (meeting?.recording_download_url) {
      window.open(meeting.recording_download_url, '_blank');
    } else if (meeting?.drive_view_link) {
      window.open(meeting.drive_view_link, '_blank');
    } else {
      ElMessage.info('尚無錄影資料，已送出取得錄影請求');
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '取得錄影失敗');
  } finally {
    recordingLoadingMap[bookingId] = false;
  }
};

// --- Drawer State ---
const drawerVisible = ref(false);
const formRef = ref<FormInstance>();
const conflictError = ref('');

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
  id: '', studentId: '', type: 'Regular', courseId: '', teacherId: '',
  time: '', link: '', note: '', status: 'Scheduled', isConverted: false
});

const formDate = ref('');
const formTimeStr = ref('');

const rules = reactive<FormRules>({
  studentId: [{ required: true, message: 'Required' }],
  type: [{ required: true, message: 'Required' }],
  courseId: [{ required: true, message: 'Required' }],
  teacherId: [{ required: true, message: 'Required' }],
  date: [{ required: true, message: 'Required', trigger: 'change', validator: (r, v, c) => formDate.value ? c() : c(new Error('Required')) }],
  timeStr: [{ required: true, message: 'Required', trigger: 'change', validator: (r, v, c) => formTimeStr.value ? c() : c(new Error('Required')) }]
});

const selectedCourseDuration = computed(() => {
  if (!form.courseId) return 0;
  const c = courses.value.find(x => x.id === form.courseId);
  return c ? c.duration : 0;
});

const availableCourses = computed(() => {
  if (!form.studentId) return [];
  if (form.type === 'Trial') return courses.value;
  const s = students.value.find(x => x.id === form.studentId);
  if (!s || !s.purchasedCourses) return [];
  return s.purchasedCourses.map(pc => courses.value.find(c => c.id === pc.courseId)).filter(Boolean) as Course[];
});

const availableTeachers = computed(() => {
  if (!form.courseId) return [];
  return teacherOptions.value.filter((t: any) => !t.courseIds || t.courseIds.includes(form.courseId!));
});

const openDrawer = (row: any | null) => {
  conflictError.value = '';
  if (row) {
    Object.assign(form, {
      id: row.id,
      studentId: row.student_id,
      type: row.booking_type || 'Regular',
      courseId: row.course_id,
      teacherId: row.teacher_id,
      time: row.booking_date + 'T' + row.start_time,
      duration: 50,
      link: row.notes || '',
      note: row.notes || '',
      status: row.booking_status,
      isConverted: false,
    });
    const d = dayjs(form.time);
    formDate.value = d.format('YYYY-MM-DD');
    formTimeStr.value = row.start_time ? row.start_time.substring(0, 5) : d.format('HH:mm');
  } else {
    Object.assign(form, { id: '', studentId: '', type: 'Regular', courseId: '', teacherId: '', time: '', duration: 50, link: '', note: '', status: 'Scheduled', isConverted: false });
    formDate.value = '';
    formTimeStr.value = '';
  }
  drawerVisible.value = true;
  nextTick(() => { formRef.value?.clearValidate(); });
};

const handleStudentChange = () => { form.courseId = ''; form.teacherId = ''; };
const handleTypeChange = () => { form.courseId = ''; form.teacherId = ''; };
const handleCourseChange = () => { form.teacherId = ''; };
const clearConflictError = () => { conflictError.value = ''; };

const handleSave = async () => {
  drawerVisible.value = false;
  ElMessage.success('已儲存（API 尚未串接）');
  fetchData();
};

const handleCancel = (row: BookingItem) => {
  ElMessageBox.confirm('確定要取消這堂課嗎？', '取消預約', {
    confirmButtonText: '確定取消', cancelButtonText: '返回', type: 'warning'
  }).then(() => {
    ElMessage.warning('取消 API 尚未實作');
  });
};

const handleDelete = (row: BookingItem) => {
  ElMessageBox.confirm('確定要永久刪除此筆記錄？', '刪除', { type: 'error' }).then(() => {
    ElMessage.warning('刪除 API 尚未實作');
  });
};

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
.info-text { font-size: 12px; color: #909399; margin-top: 5px; }
</style>
