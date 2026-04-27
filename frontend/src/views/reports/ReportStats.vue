<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed, watch } from 'vue';
import { Download } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import dayjs from 'dayjs';
import { useI18n } from 'vue-i18n';
import { getBookingList, type BookingItem } from '@/api/booking';
import { getCourseList, type CourseResponseData } from '@/api/course';
import { getStudentOverviewList, type StudentOverviewListResponse } from '@/api/student';
import { getStudentContracts, type StudentContract } from '@/api/studentContract';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { init, use, type ECharts } from 'echarts/core';
import { BarChart, LineChart, PieChart } from 'echarts/charts';
import {
    GridComponent,
    LegendComponent,
    TitleComponent,
    TooltipComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

use([BarChart, LineChart, PieChart, GridComponent, LegendComponent, TitleComponent, TooltipComponent, CanvasRenderer]);

const { t } = useI18n();

// --- State ---
const dateRange = ref<[Date, Date]>([
    dayjs().startOf('year').toDate(),
    dayjs().endOf('year').toDate()
]);

const activeTab = ref('financial');
const loading = ref(false);
const bookings = ref<BookingItem[]>([]);
const courses = ref<CourseResponseData[]>([]);
const students = ref<StudentOverviewListResponse[]>([]);
const contracts = ref<StudentContract[]>([]);
const financialChartRef = ref<HTMLElement | null>(null);
const courseChartRef = ref<HTMLElement | null>(null);
const studentChartRef = ref<HTMLElement | null>(null);

let financialChart: ECharts | null = null;
let courseChart: ECharts | null = null;
let studentChart: ECharts | null = null;

// --- Helpers ---
const dateFrom = computed(() => dayjs(dateRange.value[0]).startOf('month').format('YYYY-MM-DD'));
const dateTo = computed(() => dayjs(dateRange.value[1]).endOf('month').format('YYYY-MM-DD'));

const isBetween = (dateStr: string) => {
    if (!dateRange.value || !dateStr) return false;
    const d = dayjs(dateStr);
    return d.isAfter(dayjs(dateRange.value[0]).subtract(1, 'day')) && 
           d.isBefore(dayjs(dateRange.value[1]).add(1, 'day'));
};

const getBookingMinutes = (booking: BookingItem) => {
    const start = dayjs(`${booking.booking_date} ${booking.start_time}`);
    const end = dayjs(`${booking.booking_date} ${booking.end_time}`);
    const diff = end.diff(start, 'minute');
    if (diff > 0) return diff;

    return courses.value.find((course) => course.id === booking.course_id)?.duration_minutes || 60;
};

const fetchReportData = async () => {
    loading.value = true;
    try {
        const [bookingRes, contractRes, studentRes, courseRes] = await Promise.all([
            getBookingList({
                page: 1,
                per_page: 100,
                booking_status: 'completed',
                date_from: dateFrom.value,
                date_to: dateTo.value,
            }),
            getStudentContracts({
                page: 1,
                per_page: 100,
            }),
            getStudentOverviewList({
                page: 1,
                per_page: 100,
            }),
            getCourseList({
                page: 1,
                per_page: 100,
            }),
        ]);

        bookings.value = assertApiSuccess(bookingRes, t('report.loadBookingsFailed')).data || [];
        contracts.value = assertApiSuccess(contractRes, t('report.loadContractsFailed')).data || [];
        students.value = assertApiSuccess(studentRes, t('report.loadStudentsFailed')).data || [];
        courses.value = assertApiSuccess(courseRes, t('report.loadCoursesFailed')).data || [];

        await nextTick();
        initCharts();
    } catch (error) {
        ElMessage.error(getApiErrorMessage(error, t('report.loadFailed')));
    } finally {
        loading.value = false;
    }
};

// --- Aggregation Logic ---

// 1. Revenue
const revenueData = computed(() => {
    let total = 0;
    const monthlyData: Record<string, number> = {};
    
    contracts.value.forEach((contract) => {
        const revenueDate = contract.start_date || contract.created_at;
        if (!revenueDate || !isBetween(revenueDate)) return;

        const amount = Number(contract.total_amount || 0);
        total += amount;
        const month = dayjs(revenueDate).format('YYYY-MM');
        monthlyData[month] = (monthlyData[month] || 0) + amount;
    });

    return { total, monthlyData };
});

// 2. Salary
const salaryData = computed(() => {
    let total = 0;
    const monthlyData: Record<string, number> = {};

    bookings.value.forEach((booking) => {
        const date = booking.booking_date;
        if (!isBetween(date)) return;

        const cost = Number(booking.teacher_hourly_rate || 0);
        total += cost;
        const month = dayjs(date).format('YYYY-MM');
        monthlyData[month] = (monthlyData[month] || 0) + cost;
    });

    return { total, monthlyData };
});

// 3. Operation Metrics
const hoursData = computed(() => {
    let totalMins = 0;
    bookings.value.forEach((booking) => {
        if (!isBetween(booking.booking_date)) return;
        totalMins += getBookingMinutes(booking);
    });
    return (totalMins / 60).toFixed(1);
});

const coursePopularity = computed(() => {
    const counts: Record<string, number> = {};
    bookings.value.forEach((booking) => {
        if (!isBetween(booking.booking_date)) return;
        const courseName = booking.course_name
            || courses.value.find((course) => course.id === booking.course_id)?.course_name
            || t('report.unknownCourse');
        counts[courseName] = (counts[courseName] || 0) + 1;
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
});

const studentGrowth = computed(() => {
    const newPerMonth: Record<string, number> = {};
    let newCount = 0;
    
    students.value.forEach((student) => {
        const createdAt = student.created_at;
        if (createdAt && isBetween(createdAt)) {
            const m = dayjs(createdAt).format('YYYY-MM');
            newPerMonth[m] = (newPerMonth[m] || 0) + 1;
            newCount++;
        }
    });
    const active = students.value.filter((student) => student.is_active).length;
    
    return { newPerMonth, newCount, active };
});

// --- Aggregated Data for Table ---
const getMonthsInRange = () => {
    const months = [];
    let cur = dayjs(dateRange.value[0]).startOf('month');
    const end = dayjs(dateRange.value[1]).endOf('month');
    while(cur.isBefore(end)) {
        months.push(cur.format('YYYY-MM'));
        cur = cur.add(1, 'month');
    }
    return months;
};

const financialTableData = computed(() => {
    const months = getMonthsInRange();
    return months.map(m => {
        const rev = revenueData.value.monthlyData[m] || 0;
        const cost = salaryData.value.monthlyData[m] || 0;
        return {
            month: m,
            revenue: rev,
            cost: cost,
            profit: rev - cost
        };
    });
});

// --- Chart Rendering ---
const updateCharts = () => {
    const months = getMonthsInRange();
    
    // Financial Chart
    if (financialChart && activeTab.value === 'financial') {
        financialChart.resize(); // Ensure size
        financialChart.setOption({
            title: { text: t('report.financial') + ' Overview' },
            tooltip: { trigger: 'axis' },
            legend: { top: 'bottom' },
            grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
            xAxis: { type: 'category', data: months },
            yAxis: { type: 'value' },
            color: ['#67C23A', '#F56C6C'],
            series: [
                { name: t('report.revenue'), type: 'bar', stack: 'Total', data: months.map(m => revenueData.value.monthlyData[m] || 0) },
                { name: t('report.cost'), type: 'bar', stack: 'Total', data: months.map(m => salaryData.value.monthlyData[m] || 0) }
            ]
        });
    }
    
    // Operation Charts
    if (activeTab.value === 'operation') {
        if (courseChart) {
            courseChart.resize();
            const data = coursePopularity.value;
            const total = data.reduce((sum, item) => sum + item.value, 0);
            courseChart.setOption({
                 title: { text: t('report.coursePopularity'), subtext: `Total: ${total}`, left: 'center', top: 'center' },
                 tooltip: { trigger: 'item' },
                 legend: { bottom: '0%' },
                 series: [{
                     name: 'Sessions', type: 'pie', radius: ['40%', '70%'], avoidLabelOverlap: false,
                     itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
                     label: { show: false },
                     emphasis: { label: { show: true, fontSize: 20, fontWeight: 'bold' } },
                     data: data
                 }]
            });
        }
        
        if (studentChart) {
            studentChart.resize();
            let activeCount = Math.max(studentGrowth.value.active - studentGrowth.value.newCount, 0);
            const activeSeries = months.map(m => {
                activeCount += (studentGrowth.value.newPerMonth[m] || 0);
                return activeCount;
            });
            studentChart.setOption({
                title: { text: t('report.studentGrowth') },
                tooltip: { trigger: 'axis' },
                xAxis: { type: 'category', boundaryGap: false, data: months },
                yAxis: { type: 'value' },
                grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
                series: [
                    { name: t('report.newStudents'), type: 'line', smooth: true, data: months.map(m => studentGrowth.value.newPerMonth[m] || 0) },
                    { name: t('report.activeStudents'), type: 'line', smooth: true, data: activeSeries }
                ]
            });
        }
    }
};

const initCharts = () => {
    if (activeTab.value === 'financial') {
        if (financialChartRef.value) {
            if (!financialChart) financialChart = init(financialChartRef.value);
            updateCharts();
        }
    } else {
        if (courseChartRef.value) {
            if (!courseChart) courseChart = init(courseChartRef.value);
        }
        if (studentChartRef.value) {
            if (!studentChart) studentChart = init(studentChartRef.value);
        }
        updateCharts(); // Update both
    }
};

onMounted(() => {
    fetchReportData();
    window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
    window.removeEventListener('resize', handleResize);
    financialChart?.dispose();
    courseChart?.dispose();
    studentChart?.dispose();
});

const handleResize = () => {
    financialChart?.resize();
    courseChart?.resize();
    studentChart?.resize();
};

watch(activeTab, () => {
    nextTick(() => {
        initCharts();
    });
});

watch(dateRange, () => {
    fetchReportData();
});

const handleExport = () => {
    ElMessage.success('Exporting report for selected period...');
};

// Computed Metrics
const totalRevenue = computed(() => revenueData.value.total);
const totalSalary = computed(() => salaryData.value.total);
const grossProfit = computed(() => totalRevenue.value - totalSalary.value);
</script>

<template>
  <div class="stats-page">
    <!-- 1. Header Area -->
    <div class="header-bar">
        <div class="left">
            <span class="label">{{ $t('report.filter') }}:</span>
            <el-date-picker
                v-model="dateRange"
                type="monthrange"
                range-separator="To"
                :start-placeholder="$t('report.startMonth')"
                :end-placeholder="$t('report.endMonth')"
                :clearable="false"
                style="width: 300px;"
            />
        </div>
        <div class="right">
            <el-button type="primary" :icon="Download" @click="handleExport">{{ $t('report.export') }}</el-button>
        </div>
    </div>

    <!-- 2. Tabs -->
    <el-tabs v-model="activeTab" type="border-card" class="report-tabs">
        
        <!-- Tab 1: Financial Report -->
        <el-tab-pane :label="$t('report.financial')" name="financial">
            <!-- KPI Cards -->
            <el-row :gutter="20" class="mb-20">
                <el-col :span="8">
                    <el-card shadow="hover" class="metric-card">
                        <template #header>{{ $t('report.totalRevenue') }}</template>
                        <div class="metric-value text-success">${{ totalRevenue.toLocaleString() }}</div>
                    </el-card>
                </el-col>
                <el-col :span="8">
                    <el-card shadow="hover" class="metric-card">
                        <template #header>{{ $t('report.totalSalary') }}</template>
                        <div class="metric-value text-danger">${{ totalSalary.toLocaleString() }}</div>
                    </el-card>
                </el-col>
                 <el-col :span="8">
                    <el-card shadow="hover" class="metric-card">
                        <template #header>{{ $t('report.grossProfit') }}</template>
                        <div class="metric-value text-primary">${{ grossProfit.toLocaleString() }}</div>
                    </el-card>
                </el-col>
            </el-row>

            <el-row :gutter="20">
                <el-col :span="24">
                    <div ref="financialChartRef" class="chart mb-20"></div>
                </el-col>
            </el-row>
            
            <!-- Summary Table -->
            <h3>{{ $t('report.monthlyBreakdown') }}</h3>
            <el-table :data="financialTableData" border stripe style="width: 100%">
                <el-table-column prop="month" :label="$t('report.month')" />
                <el-table-column :label="$t('report.revenue')">
                    <template #default="{ row }">${{ row.revenue.toLocaleString() }}</template>
                </el-table-column>
                <el-table-column :label="$t('report.cost')">
                    <template #default="{ row }">${{ row.cost.toLocaleString() }}</template>
                </el-table-column>
                <el-table-column :label="$t('report.profit')">
                    <template #default="{ row }">
                        <span :class="row.profit >= 0 ? 'text-success' : 'text-danger'">
                            ${{ row.profit.toLocaleString() }}
                        </span>
                    </template>
                </el-table-column>
            </el-table>
        </el-tab-pane>

        <!-- Tab 2: Operation Report -->
        <el-tab-pane :label="$t('report.operation')" name="operation">
            <!-- KPI Cards -->
             <el-row :gutter="20" class="mb-20">
                <el-col :span="8">
                    <el-card shadow="hover" class="metric-card">
                        <template #header>{{ $t('report.classHours') }}</template>
                        <div class="metric-value">{{ hoursData }} hrs</div>
                    </el-card>
                </el-col>
                 <el-col :span="8">
                    <el-card shadow="hover" class="metric-card">
                        <template #header>{{ $t('report.activeStudents') }}</template>
                        <div class="metric-value">{{ studentGrowth.active }}</div>
                    </el-card>
                </el-col>
                 <el-col :span="8">
                    <el-card shadow="hover" class="metric-card">
                        <template #header>{{ $t('report.newStudents') }}</template>
                        <div class="metric-value text-primary">+{{ studentGrowth.newCount }}</div>
                    </el-card>
                </el-col>
            </el-row>
            
            <el-row :gutter="20">
                 <el-col :span="12">
                    <el-card shadow="never" :header="$t('report.coursePopularity')">
                        <div ref="courseChartRef" class="chart"></div>
                    </el-card>
                </el-col>
                <el-col :span="12">
                     <el-card shadow="never" :header="$t('report.studentGrowth')">
                        <div ref="studentChartRef" class="chart"></div>
                    </el-card>
                </el-col>
            </el-row>
        </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.stats-page {
    padding: 20px;
}
.header-bar {
    background: #fff;
    padding: 15px 20px;
    border-radius: 8px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}
.header-bar .left {
    display: flex;
    align-items: center;
    gap: 10px;
}
.label {
    font-weight: bold;
    color: #606266;
}

.report-tabs {
    min-height: 500px;
}

.metric-card .metric-value {
    font-size: 24px;
    font-weight: bold;
}
.mb-20 { margin-bottom: 20px; }

.text-success { color: #67C23A; }
.text-danger { color: #F56C6C; }
.text-primary { color: #409EFF; }

.chart {
    width: 100%;
    height: 350px;
}
</style>
