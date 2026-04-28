<template>
  <div class="booking-list-container">
    <!-- Filter Section (區塊 A) -->
    <el-card class="filter-card mb-20px" shadow="never">
      <el-form :inline="true" size="small" :model="queryParams" label-position="top" class="filter-form flex items-end">
        <el-form-item :label="$t('common.dateRange')" >
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            :range-separator="$t('studentAdmin.to')"
            :start-placeholder="$t('common.startDate')"
            :end-placeholder="$t('common.endDate')"
            value-format="YYYY-MM-DD"
            @change="handleDateRangeChange"
            class="w-220px! h-30px!"
          />
        </el-form-item>
        <el-form-item :label="$t('studentAdmin.bookingStatus')">
          <el-select 
            v-model="queryParams.booking_status" 
            :placeholder="$t('studentAdmin.selectStatus')" 
            clearable 
            class="w-120px"
            @change="handleSearch"
          >
            <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" round @click="handleSearch">
            <template #icon>
              <div class="i-hugeicons:search-list-02" />
            </template>
            {{ $t('common.search') }}
          </el-button>
          <el-button round @click="resetQuery">
            <template #icon>
              <div class="i-hugeicons:arrow-reload-horizontal" />
            </template>
            {{ $t('common.btnReset') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Data Table (區塊 B) -->
    <el-card shadow="never">
      <el-table :data="bookingList" v-loading="loading" stripe class="w-full" size="small">
        <!-- 預約編號 -->
        <el-table-column prop="booking_no" :label="$t('studentAdmin.bookingNo')" min-width="140" />
        
        <!-- 課程名稱 -->
        <el-table-column prop="course_name" :label="$t('studentAdmin.courseName')" min-width="150" show-overflow-tooltip />
        
        <!-- 指導教師 -->
        <el-table-column prop="teacher_name" :label="$t('studentAdmin.instructor')" min-width="120" />
        
        <!-- 上課日期 -->
        <el-table-column prop="booking_date" :label="$t('studentAdmin.classDate')" min-width="110" />
        
        <!-- 上課時間 -->
        <el-table-column :label="$t('studentAdmin.classTime')" min-width="120">
          <template #default="{ row }">
            {{ formatTime(row.start_time) }} - {{ formatTime(row.end_time) }}
          </template>
        </el-table-column>
        
        <!-- 消耗堂數 -->
        <el-table-column prop="lessons_used" :label="$t('studentAdmin.lessonsUsed')" min-width="100" align="center" />
        
        <!-- 狀態 -->
        <el-table-column :label="$t('common.status')" min-width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.booking_status)" effect="light">
              {{ getStatusLabel(row.booking_status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <!-- 備註 -->
        <el-table-column prop="notes" :label="$t('common.note')" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.notes || '-' }}
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination (區塊 C) -->
      <div class="pagination-footer mt-20px flex justify-end">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.per_page"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          small
          @size-change="fetchBookings"
          @current-change="fetchBookings"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { getBookingList, type BookingListParams, type BookingItem } from '@/api/booking';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { useI18n } from 'vue-i18n';

const props = defineProps<{
  studentId: string;
}>();

const { t } = useI18n();

// State
const loading = ref(false);
const bookingList = ref<BookingItem[]>([]);
const total = ref(0);
const dateRange = ref<[string, string] | null>(null);

const statusOptions = computed(() => [
  { value: '', label: t('common.all') },
  { value: 'pending', label: t('display.bookingStatus.pending') },
  { value: 'confirmed', label: t('display.bookingStatus.confirmed') },
  { value: 'completed', label: t('display.bookingStatus.completed') },
  { value: 'cancelled', label: t('display.bookingStatus.cancelled') }
]);

const queryParams = reactive<BookingListParams>({
  page: 1,
  per_page: 10,
  booking_status: '',
  date_from: undefined,
  date_to: undefined,
  student_id: props.studentId
});

// Watch studentId changes in case component isn't re-mounted
watch(() => props.studentId, (newId) => {
  if (newId) {
    queryParams.student_id = newId;
    handleSearch();
  }
});

// Methods
const fetchBookings = async () => {
  if (!queryParams.student_id) return;
  
  loading.value = true;
  try {
    // 建立一份 payload, 移除空字串的值
    const params: BookingListParams = { ...queryParams };
    if (params.booking_status === '') {
      delete params.booking_status;
    }
    
    const res = assertApiSuccess(await getBookingList(params), t('studentAdmin.loadBookingsFailed'));
    bookingList.value = res.data || [];
    total.value = res.total || 0;
  } catch (err: any) {
    console.error('Fetch bookings error:', err);
    ElMessage.error(getApiErrorMessage(err, t('studentAdmin.loadBookingsFailed')));
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  queryParams.page = 1;
  fetchBookings();
};

const resetQuery = () => {
  dateRange.value = null;
  queryParams.date_from = undefined;
  queryParams.date_to = undefined;
  queryParams.booking_status = '';
  queryParams.page = 1;
  fetchBookings();
};

const handleDateRangeChange = (val: [string, string] | null) => {
  if (val && val.length === 2) {
    queryParams.date_from = val[0];
    queryParams.date_to = val[1];
  } else {
    queryParams.date_from = undefined;
    queryParams.date_to = undefined;
  }
  handleSearch();
};

// Utils
const formatTime = (timeStr: string) => {
  if (!timeStr) return '';
  // 假設 API 傳回 "HH:mm:ss" 或 "HH:mm"，我們只取前 5 個字元 "HH:mm"
  return timeStr.slice(0, 5);
};

const getStatusType = (status: string) => {
  switch (status) {
    case 'pending': return 'warning';
    case 'confirmed': return 'primary';
    case 'completed': return 'success';
    case 'cancelled': return 'danger';
    default: return 'info';
  }
};

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'pending': return t('display.bookingStatus.pending');
    case 'confirmed': return t('display.bookingStatus.confirmed');
    case 'completed': return t('display.bookingStatus.completed');
    case 'cancelled': return t('display.bookingStatus.cancelled');
    default: return status;
  }
};

// Lifecycle
onMounted(() => {
  fetchBookings();
});
</script>

<style lang="scss" scoped>
/* .mb-20px {
  margin-bottom: 20px;
}
.mt-20px {
  margin-top: 20px;
} */
:deep(.filter-form ) {
    gap: 15px!important;
}
:deep(.el-drawer__header) {
  margin-bottom: 10px !important;
}
</style>
