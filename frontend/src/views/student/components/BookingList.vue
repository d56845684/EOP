<template>
  <div class="booking-list-container">
    <!-- Filter Section (區塊 A) -->
    <el-card class="filter-card mb-20px" shadow="never">
      <el-form :inline="true" size="small" :model="queryParams" label-position="top" class="filter-form flex items-end">
        <el-form-item label="日期區間" >
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="-"
            start-placeholder="開始日期"
            end-placeholder="結束日期"
            value-format="YYYY-MM-DD"
            @change="handleDateRangeChange"
            style="width: 260px"
          />
        </el-form-item>
        <el-form-item label="預約狀態">
          <el-select 
            v-model="queryParams.booking_status" 
            placeholder="請選擇狀態" 
            clearable 
            style="width: 120px;"
            @change="handleSearch"
          >
            <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <template #icon>
              <div class="i-hugeicons:search-list-02" />
            </template>
            搜尋
          </el-button>
          <el-button @click="resetQuery">
            <template #icon>
              <div class="i-hugeicons:arrow-reload-horizontal" />
            </template>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Data Table (區塊 B) -->
    <el-card shadow="never">
      <el-table :data="bookingList" v-loading="loading" stripe class="w-full">
        <!-- 預約編號 -->
        <el-table-column prop="booking_no" label="預約編號" min-width="140" />
        
        <!-- 課程名稱 -->
        <el-table-column prop="course_name" label="課程名稱" min-width="150" show-overflow-tooltip />
        
        <!-- 指導教師 -->
        <el-table-column prop="teacher_name" label="指導教師" min-width="120" />
        
        <!-- 上課日期 -->
        <el-table-column prop="booking_date" label="上課日期" min-width="110" />
        
        <!-- 上課時間 -->
        <el-table-column label="上課時間" min-width="120">
          <template #default="{ row }">
            {{ formatTime(row.start_time) }} - {{ formatTime(row.end_time) }}
          </template>
        </el-table-column>
        
        <!-- 消耗堂數 -->
        <el-table-column prop="lessons_used" label="消耗堂數" min-width="90" align="center" />
        
        <!-- 狀態 -->
        <el-table-column label="狀態" min-width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.booking_status)" effect="light">
              {{ getStatusLabel(row.booking_status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <!-- 備註 -->
        <el-table-column prop="notes" label="備註" min-width="160" show-overflow-tooltip>
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
          @size-change="fetchBookings"
          @current-change="fetchBookings"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { getBookingList, type BookingListParams, type BookingItem } from '@/api/booking';

const props = defineProps<{
  studentId: string;
}>();

// State
const loading = ref(false);
const bookingList = ref<BookingItem[]>([]);
const total = ref(0);
const dateRange = ref<[string, string] | null>(null);

const statusOptions = [
  { value: '', label: '全部' },
  { value: 'pending', label: '待確認' },
  { value: 'confirmed', label: '已確認' },
  { value: 'completed', label: '已完成' },
  { value: 'cancelled', label: '已取消' }
];

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
    
    // axios request
    const res: any = await getBookingList(params);
    
    if (res.success || res.data) {
       // Support typical axios res wrapper or direct data return
       const responseData = typeof res.data !== 'undefined' && Array.isArray(res.data) ? res : (res.data || res);
       bookingList.value = responseData.data || [];
       total.value = responseData.total || 0;
    } else {
       bookingList.value = [];
       total.value = 0;
    }
  } catch (err: any) {
    console.error('Fetch bookings error:', err);
    ElMessage.error(err?.response?.data?.message || '載入上課紀錄失敗');
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
    case 'pending': return '待確認';
    case 'confirmed': return '已確認';
    case 'completed': return '已完成';
    case 'cancelled': return '已取消';
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
