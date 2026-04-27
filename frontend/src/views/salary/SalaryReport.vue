<template>
  <div class="salary-report">
    <el-card class="mb-20">
      <div class="filters">
        <span class="label">{{ $t('salary.selectMonth') }}:</span>
        <el-date-picker
          v-model="selectedMonth"
          type="month"
          :placeholder="$t('salary.selectMonth')"
          :clearable="false"
        />
        <el-statistic :title="$t('salary.totalPayout')" :value="totalPayout" prefix="$" class="ml-20" />
      </div>
    </el-card>

    <el-alert
      type="info"
      :closable="false"
      class="mb-20"
      show-icon
    >
        <template #title>
            <strong>{{ $t('salary.currentPeriod') }}: {{ formatMonth(selectedMonth) }}</strong>
        </template>
    </el-alert>

    <el-table :data="salaryData" style="width: 100%" v-loading="loading" border show-summary :summary-method="getSummaries">
      <el-table-column prop="teacherName" :label="$t('common.teacher')" />
      <el-table-column prop="contractType" :label="$t('salary.contract')" />
      
      <el-table-column :label="$t('salary.regularClasses')">
         <el-table-column prop="regularCount" :label="$t('salary.regularCount')" />
         <el-table-column prop="regularPay" :label="$t('salary.regularPay')" />
      </el-table-column>
      
      <el-table-column :label="$t('salary.trialClasses')">
         <el-table-column prop="trialCount" :label="$t('salary.trialTotal')" />
         <el-table-column prop="trialConvertedCount" :label="$t('salary.trialConverted')" />
         <el-table-column prop="trialPay" :label="$t('salary.trialPay')" />
      </el-table-column>
      
      <el-table-column prop="totalPay" :label="$t('salary.totalSalary')" sortable>
         <template #default="{ row }">
           <strong>${{ row.totalPay.toLocaleString() }}</strong>
         </template>
      </el-table-column>

      <el-table-column :label="$t('common.actions')">
        <template #default="{ row }">
          <el-button size="small" @click="openDetails(row)">{{ $t('common.details') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Details Drawer -->
    <el-drawer v-model="drawerVisible" :title="$t('salary.breakdown')" size="700px">
      <h3>{{ selectedTeacher?.teacherName }} - {{ formatMonth(selectedMonth) }}</h3>
      
      <div class="summary-box">
          <div>{{ $t('salary.basePay') }}: ${{ selectedTeacher?.baseSalary || 0 }}</div>
          <div>{{ $t('salary.classPay') }}: ${{ selectedTeacher?.totalPay - (selectedTeacher?.baseSalary || 0) }}</div>
      </div>

      <el-table :data="selectedDetails" height="500" stripe style="width: 100%">
         <!-- 1. Date/Time -->
         <el-table-column :label="$t('salary.dateTime')" min-width="140">
             <template #default="{ row }">{{ formatDateTime(row.time) }}</template>
         </el-table-column>
         <!-- 2. Course -->
         <el-table-column prop="courseName" :label="$t('common.course')" min-width="120" />
         <!-- 3. Student -->
         <el-table-column :label="$t('common.student')" min-width="140">
            <template #default="{ row }">
                <span>{{ row.studentName }}</span>
                <el-tag size="small" class="ml-1" effect="plain">{{ row.studentType }}</el-tag>
            </template>
         </el-table-column>
         <!-- 4. Class Type -->
         <el-table-column :label="$t('salary.classType')" width="100">
             <template #default="{ row }">
                 <el-tag :type="row.type === 'Trial' ? 'warning' : ''" effect="dark">{{ row.type }}</el-tag>
             </template>
         </el-table-column>
         <!-- 5. Base Rate -->
         <el-table-column property="rate" :label="$t('salary.baseRate')" width="100">
             <template #default="{ row }">${{ row.rate }}</template>
         </el-table-column>
         <!-- 6. Bonus -->
         <el-table-column :label="$t('salary.bonus')" width="80" align="center">
            <template #default="{ row }">
                <span v-if="row.multiplier > 1" class="text-bonus">x{{ row.multiplier }}</span>
                <span v-else>--</span>
            </template>
         </el-table-column>
         <!-- 7. Subtotal -->
         <el-table-column :label="$t('salary.subtotal')" width="100">
             <template #default="{ row }">
                 <strong>${{ row.finalPay }}</strong>
             </template>
         </el-table-column>
         <!-- 8. Status -->
         <el-table-column :label="$t('common.status')" width="100" align="center">
             <template #default="{ row }">
                 <el-tag type="success" size="small">{{ row.status }}</el-tag>
             </template>
         </el-table-column>
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import dayjs from 'dayjs';
import { useI18n } from 'vue-i18n';
import { getBookingList, type BookingItem } from '@/api/booking';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { ElMessage } from 'element-plus';

const { t } = useI18n();
const selectedMonth = ref(dayjs().toDate());
const loading = ref(false);
const drawerVisible = ref(false);
const selectedTeacher = ref<any>(null);
const bookings = ref<BookingItem[]>([]);

const formatMonth = (d: Date) => dayjs(d).format('YYYY-MM');
const formatDateTime = (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm');
const getBookingStart = (booking: BookingItem) => `${booking.booking_date} ${booking.start_time}`;
const formatBookingType = (type: string) => (type === 'trial' ? t('salary.trialType') : t('salary.regularType'));

// --- Core Logic ---
const fetchSalaryBookings = async () => {
    loading.value = true;
    try {
        const start = dayjs(selectedMonth.value).startOf('month').format('YYYY-MM-DD');
        const end = dayjs(selectedMonth.value).endOf('month').format('YYYY-MM-DD');
        const res = assertApiSuccess(await getBookingList({
            page: 1,
            per_page: 100,
            booking_status: 'completed',
            date_from: start,
            date_to: end,
        }), t('salary.loadFailed'));
        bookings.value = res.data || [];
    } catch (error) {
        ElMessage.error(getApiErrorMessage(error, t('salary.loadFailed')));
    } finally {
        loading.value = false;
    }
};

const salaryData = computed(() => {
    const reportMap = new Map<string, any>();

    bookings.value.forEach((booking) => {
        const teacherId = booking.teacher_id;
        if (!reportMap.has(teacherId)) {
            reportMap.set(teacherId, {
                teacherId,
                teacherName: booking.teacher_name || teacherId,
                contractType: '-',
                baseSalary: 0,
                regularCount: 0,
                regularPay: 0,
                trialCount: 0,
                trialConvertedCount: 0,
                trialPay: 0,
                totalPay: 0,
                details: [],
            });
        }

        const row = reportMap.get(teacherId);
        const baseRate = Number(booking.teacher_hourly_rate || 0);
        const multiplier = 1;
        const finalPay = baseRate;
        const bookingType = formatBookingType(booking.booking_type);

        if (booking.booking_type === 'trial') {
            row.trialCount += 1;
            if (booking.is_trial_to_formal) {
                row.trialConvertedCount += 1;
            }
            row.trialPay += finalPay;
        } else {
            row.regularCount += 1;
            row.regularPay += finalPay;
        }

        row.totalPay += finalPay;
        row.details.push({
            ...booking,
            time: getBookingStart(booking),
            courseName: booking.course_name || booking.course_id,
            studentName: booking.student_name || booking.student_id,
            studentType: bookingType,
            type: bookingType,
            rate: baseRate,
            multiplier,
            finalPay,
            status: booking.booking_status,
        });
    });

    return Array.from(reportMap.values());
});

const totalPayout = computed(() => salaryData.value.reduce((sum, r) => sum + r.totalPay, 0));

// --- UI ---
const getSummaries = (param: any) => {
    const { columns, data } = param;
    const sums: string[] = [];
    columns.forEach((col: any, index: number) => {
        if (index === 0) { sums[index] = t('salary.totalRow'); return; }
        if (col.property === 'totalPay') {
            const val = data.reduce((prev: number, curr: any) => prev + curr.totalPay, 0);
            sums[index] = '$' + val.toLocaleString();
        } else {
            sums[index] = '';
        }
    });
    return sums;
};

const openDetails = (row: any) => {
    selectedTeacher.value = row;
    drawerVisible.value = true;
};

const selectedDetails = computed(() => selectedTeacher.value ? selectedTeacher.value.details : []);

onMounted(() => {
    fetchSalaryBookings();
});

watch(selectedMonth, () => {
    fetchSalaryBookings();
});

</script>

<style scoped>
.mb-20 { margin-bottom: 20px; }
.filters { display: flex; align-items: center; gap: 10px; }
.ml-20 { margin-left: 20px; }
.highlight-bonus { color: #E6A23C; font-weight: bold; }
.summary-box { 
    margin-bottom: 20px; 
    padding: 10px; 
    background: var(--el-fill-color-light); 
    border-radius: 4px;
}
.text-bonus { color: #E6A23C; font-weight: bold; }
.ml-1 { margin-left: 5px; }
</style>
