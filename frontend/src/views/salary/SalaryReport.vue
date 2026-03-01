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
import { ref, computed } from 'vue';
import { useMockStore, type Teacher } from '../../stores/mockStore';
import dayjs from 'dayjs';

const store = useMockStore();
const selectedMonth = ref(dayjs().toDate());
const loading = ref(false);
const drawerVisible = ref(false);
const selectedTeacher = ref<any>(null);

const formatMonth = (d: Date) => dayjs(d).format('YYYY-MM');
const formatDateTime = (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm');

// Helper to get names (since we are inside map, we can access store direct)
const getStudent = (id: string) => store.students.find(s => s.id === id);
const getCourseName = (id: string) => store.courses.find(c => c.id === id)?.name || id;

// --- Core Logic ---

// Helper: Get Teacher Rate for a Course
const getTeacherRate = (teacher: Teacher, courseId: string): number => {
    // If Part-time, check courseRates
    if (teacher.contractType === 'Part-time') {
        const rateObj = teacher.salaryConfig.courseRates?.find(r => r.courseId === courseId);
        if (rateObj) return rateObj.price;
        // Fallback to hourly if no specific course rate? Or 0?
        // Prompt says "Input Hourly Rate + Dynamic List".
        // Let's assume hourly rate is default if course not found.
        return teacher.salaryConfig.hourlyRate || 0;
    }
    // If Full-time, per-class pay is 0 (covered by base), UNLESS explicit logic.
    // Prompt: "Full-time: 0 (Covered by Base Salary) OR specific logic".
    return 0;
};

const salaryData = computed(() => {
    const monthStart = dayjs(selectedMonth.value).startOf('month');
    const monthEnd = dayjs(selectedMonth.value).endOf('month');

    // 1. Filter Bookings
    const activeBookings = store.bookings.filter(b => {
        const t = dayjs(b.time);
        return b.status === 'Completed' && t.isAfter(monthStart) && t.isBefore(monthEnd);
    });

    // 2. Group by Teacher
    const report = store.teachers.map(teacher => {
        const tBookings = activeBookings.filter(b => b.teacherId === teacher.id);
        
        let regularCount = 0;
        let regularPay = 0;
        let trialCount = 0;
        let trialConvertedCount = 0;
        let trialPay = 0;
        
        const details: any[] = [];

        tBookings.forEach(b => {
            const baseRate = getTeacherRate(teacher, b.courseId);
            let finalPay = 0;
            let multiplier = 1;

            if (b.type === 'Regular') {
                regularCount++;
                finalPay = baseRate; // Regular class pay
                regularPay += finalPay;
            } else if (b.type === 'Trial') {
                trialCount++;
                if (b.isConverted) {
                    trialConvertedCount++;
                    multiplier = teacher.bonusMultiplier;
                    finalPay = baseRate * multiplier;
                } else {
                    finalPay = baseRate; // * 1
                }
                trialPay += finalPay;
            }

            details.push({
                ...b,
                courseName: getCourseName(b.courseId),
                studentName: getStudent(b.studentId)?.name || b.studentId,
                studentType: getStudent(b.studentId)?.type || 'Regular',
                rate: baseRate,
                multiplier,
                finalPay
            });
        });
        
        const baseSalary = teacher.contractType === 'Full-time' ? (teacher.salaryConfig.baseSalary || 0) : 0;
        const totalPay = baseSalary + regularPay + trialPay;

        return {
            teacherId: teacher.id,
            teacherName: teacher.name,
            contractType: teacher.contractType,
            baseSalary,
            regularCount,
            regularPay,
            trialCount,
            trialConvertedCount,
            trialPay,
            totalPay,
            details // Store for drawer
        };
    });

    return report;
});

const totalPayout = computed(() => salaryData.value.reduce((sum, r) => sum + r.totalPay, 0));

// --- UI ---
const getSummaries = (param: any) => {
    const { columns, data } = param;
    const sums: string[] = [];
    columns.forEach((col: any, index: number) => {
        if (index === 0) { sums[index] = 'Total'; return; }
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
