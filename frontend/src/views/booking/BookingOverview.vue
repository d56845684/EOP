<template>
  <div class="booking-overview pl-2 pr-4">
    <section class="flex justify-between items-center px-1 mb-2">
      <h3 class="text-lg my-0">{{ t('menu.booking_overview') }}</h3>
    </section>

    <el-card shadow="never" class="filter-card mb-14px">
      <el-form
        :inline="true"
        :model="filters"
        size="small"
        label-position="top"
        class="filter-form flex items-end"
        @submit.prevent="handleSearch"
      >
        <el-form-item :label="t('bookingOverview.filterStatus')">
          <el-select
            v-model="filters.status"
            clearable
            :placeholder="t('common.all')"
            class="w-140px"
            @clear="handleSearch"
            @change="handleSearch"
          >
            <el-option :label="t('bookingOverview.status.pending')" value="pending" />
            <el-option :label="t('bookingOverview.status.confirmed')" value="confirmed" />
            <el-option :label="t('bookingOverview.status.completed')" value="completed" />
            <el-option :label="t('bookingOverview.status.cancelled')" value="cancelled" />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('common.teacher')">
          <el-select
            v-model="filters.teacher_id"
            clearable
            filterable
            :placeholder="t('common.all')"
            class="w-180px"
            @clear="handleSearch"
            @change="handleSearch"
          >
            <el-option
              v-for="teacher in teacherOptions"
              :key="teacher.id"
              :label="teacher.name"
              :value="teacher.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('common.student')">
          <el-select
            v-model="filters.student_id"
            clearable
            filterable
            :placeholder="t('common.all')"
            class="w-180px"
            @clear="handleSearch"
            @change="handleSearch"
          >
            <el-option
              v-for="student in studentOptions"
              :key="student.id"
              :label="student.name"
              :value="student.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" round class="h-30px!" @click="handleSearch">
            <template #icon>
              <div class="i-hugeicons:search-01" />
            </template>
            {{ t('common.search') }}
          </el-button>
          <el-button round class="h-30px!" @click="resetFilters">
            <template #icon>
              <div class="i-hugeicons:arrow-reload-horizontal" />
            </template>
            {{ t('common.btnReset') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="calendar-panel">
      <template #header>
        <div class="calendar-toolbar">
          <div>
            <span class="calendar-title">{{ calendarTitle }}</span>
            <span class="calendar-subtitle">{{ t('bookingOverview.total', { total: bookings.length }) }}</span>
          </div>
          <div class="flex items-center gap-5">
            <el-button-group>
              <el-button size="small" @click="moveCalendar(-1)">
                <template #icon>
                  <div class="i-hugeicons:arrow-left-01" />
                </template>
              </el-button>
              <el-button size="small" @click="goToday">{{ t('common.today') }}</el-button>
              <el-button size="small" @click="moveCalendar(1)">
                <template #icon>
                  <div class="i-hugeicons:arrow-right-01" />
                </template>
              </el-button>
            </el-button-group>
            <el-button :loading="loading" size="small" round class="h-30px! px-3!" @click="fetchBookings">
              <template #icon>
                <div class="i-hugeicons:refresh" />
              </template>
              {{ t('common.refresh') }}
            </el-button>
          </div>
        </div>
      </template>
      
      <div v-loading="loading" class="qcalendar-shell relative">
        <div class="flex gap-5 absolute color-info top-0 right-4 translate-y--80%">
          <div class="text-10px flex items-center gap-1">
            <div class="w-8px h-8px rounded-full bg-[var(--el-color-warning)] opacity-90"></div>
            {{ t('bookingOverview.status.pending') }}
          </div>
          <div class="text-10px flex items-center gap-1">
            <div class="w-8px h-8px rounded-full bg-[var(--el-color-primary)] opacity-90"></div>
            {{ t('bookingOverview.status.confirmed') }}
          </div>
          <div class="text-10px flex items-center gap-1">
            <div class="w-8px h-8px rounded-full bg-[var(--el-color-success)] opacity-90"></div>
            {{ t('bookingOverview.status.completed') }}
          </div>
          <div class="text-10px flex items-center gap-1">
            <div class="w-8px h-8px rounded-full bg-[var(--el-color-info)] opacity-90"></div>
            {{ t('bookingOverview.status.cancelled') }}
          </div>
        </div>
        <QCalendarMonth
          v-model="calendarDate"
          :locale="calendarLocale"
          animated
          bordered
          hoverable
          no-default-header-btn
          short-weekday-label
          :weekdays="qCalendarWeekdays"
          :day-min-height="152"
        >
          <template #head-day-label="{ scope }">
            {{ Number(scope.timestamp.day) }}
          </template>
          <template #day="{ scope }">
            <div class="qcal-day-events">
              <BookingOverviewEventPopover
                v-for="event in getEventsByDate(scope.timestamp.date).slice(0, 3)"
                :key="event.id"
                :event="event"
              >
                <button class="booking-event" :class="event.booking.booking_status" type="button">
                  <span class="event-time">{{ event.timeLabel }}</span>
                  <span class="event-main">
                    <span class="event-title">{{ event.title }}</span>
                  </span>
                </button>
              </BookingOverviewEventPopover>

              <el-popover
                v-if="getEventsByDate(scope.timestamp.date).length > 3"
                trigger="click"
                placement="right-start"
                width="320"
              >
                <template #reference>
                  <button class="more-event" type="button">
                    +{{ getEventsByDate(scope.timestamp.date).length - 3 }} {{ t('common.more') }}
                  </button>
                </template>
                <div class="more-list">
                  <div class="popover-title">{{ formatDate(scope.timestamp.date) }}</div>
                  <BookingOverviewEventPopover
                    v-for="event in getEventsByDate(scope.timestamp.date)"
                    :key="event.id"
                    :event="event"
                  >
                    <button class="more-item" :class="event.booking.booking_status" type="button">
                      <span>{{ event.timeLabel }}</span>
                      <strong>{{ event.title }}</strong>
                    </button>
                  </BookingOverviewEventPopover>
                </div>
              </el-popover>
            </div>
          </template>
        </QCalendarMonth>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-tw';
import { QCalendarMonth } from '@quasar/quasar-ui-qcalendar';
import '@quasar/quasar-ui-qcalendar/index.css';
import { useI18n } from 'vue-i18n';
import BookingOverviewEventPopover from './components/BookingOverviewEventPopover.vue';
import {
  getBookingList,
  getBookingOptionStudents,
  getBookingOptionTeachers,
  type BookingItem,
  type BookingStatus,
  type BookingStudentOption,
  type BookingTeacherOption,
} from '@/api/booking';
import { assertApiSuccess } from '@/api/response';
import { useApiError } from '@/composables/useApiError';

interface CalendarBookingEvent {
  id: string;
  date: string;
  timeLabel: string;
  title: string;
  booking: BookingItem;
}

const loading = ref(false);
const { showApiError } = useApiError();
const { t, locale } = useI18n();
const calendarDate = ref(dayjs().format('YYYY-MM-DD'));
const bookings = ref<BookingItem[]>([]);
const studentOptions = ref<BookingStudentOption[]>([]);
const teacherOptions = ref<BookingTeacherOption[]>([]);
const qCalendarWeekdays = [1, 2, 3, 4, 5, 6, 0];

const filters = reactive({
  status: '' as BookingStatus | '',
  teacher_id: '',
  student_id: '',
});

const rangeStart = computed(() => dayjs(calendarDate.value).startOf('month'));
const rangeEnd = computed(() => dayjs(calendarDate.value).endOf('month'));
const calendarLocale = computed(() => (locale.value === 'zh-TW' ? 'zh-TW' : 'en-US'));
const calendarTitle = computed(() => {
  return new Intl.DateTimeFormat(calendarLocale.value, {
    year: 'numeric',
    month: 'long',
  }).format(dayjs(calendarDate.value).toDate());
});

const calendarEvents = computed<CalendarBookingEvent[]>(() => bookings.value
  .map((booking) => ({
    id: booking.id,
    date: booking.booking_date,
    timeLabel: `${formatTime(booking.start_time)}-${formatTime(booking.end_time)}`,
    title: [
      booking.teacher_name || t('bookingOverview.unspecifiedTeacher'),
      booking.student_name || t('bookingOverview.unspecifiedStudent'),
      booking.course_name || t('bookingOverview.unspecifiedCourse'),
    ].join(' / '),
    booking,
  }))
  .sort((a, b) => `${a.date} ${a.booking.start_time}`.localeCompare(`${b.date} ${b.booking.start_time}`)));

function formatTime(value?: string | null) {
  return value ? value.slice(0, 5) : '-';
}

function formatDate(value: string) {
  return dayjs(value).format('YYYY/MM/DD');
}

function getEventsByDate(date: string) {
  return calendarEvents.value.filter((event) => event.date === date);
}

async function fetchOptions() {
  try {
    const [studentRes, teacherRes] = await Promise.all([
      getBookingOptionStudents(),
      getBookingOptionTeachers(),
    ]);
    studentOptions.value = assertApiSuccess(studentRes, t('bookingOverview.loadOptionsFailed')).data || [];
    teacherOptions.value = assertApiSuccess(teacherRes, t('bookingOverview.loadOptionsFailed')).data || [];
  } catch (error) {
    showApiError(error, t('bookingOverview.loadOptionsFailed'));
  }
}

async function fetchBookings() {
  loading.value = true;
  try {
    const res = assertApiSuccess(await getBookingList({
      page: 1,
      per_page: 100,
      booking_status: filters.status || undefined,
      teacher_id: filters.teacher_id || undefined,
      student_id: filters.student_id || undefined,
      date_from: rangeStart.value.format('YYYY-MM-DD'),
      date_to: rangeEnd.value.format('YYYY-MM-DD'),
    }), t('bookingOverview.loadFailed'));

    bookings.value = res.data || [];
  } catch (error) {
    showApiError(error, t('bookingOverview.loadFailed'));
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  fetchBookings();
}

function resetFilters() {
  filters.status = '';
  filters.teacher_id = '';
  filters.student_id = '';
  fetchBookings();
}

function moveCalendar(amount: number) {
  calendarDate.value = dayjs(calendarDate.value).add(amount, 'month').format('YYYY-MM-DD');
}

function goToday() {
  calendarDate.value = dayjs().format('YYYY-MM-DD');
}

watch(calendarDate, () => {
  fetchBookings();
});

onMounted(async () => {
  await fetchOptions();
  await fetchBookings();
});
</script>

<style scoped lang="scss">
.booking-overview {

  :deep(.filter-form) {
    gap: 20px;
    .el-form-item {
      margin-right: 0;
      margin-bottom: 5px;
    }
  }

  .calendar-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .calendar-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--el-text-color-primary);
  }

  .calendar-subtitle {
    margin-left: 10px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }

  .qcalendar-shell {
    min-height: 640px;
    padding: 8px;
    background: linear-gradient(180deg, var(--el-fill-color-extra-light) 0%, var(--el-bg-color) 100%);
  }

  :deep(.q-calendar) {
    --calendar-border: 1px solid var(--el-border-color-lighter);
    --calendar-border-section: 1px dashed var(--el-border-color-extra-light);
    --calendar-border-current: 2px solid var(--el-color-primary);
    --calendar-head-font-weight: 700;
    --calendar-active-date-color: var(--el-color-primary);
    --calendar-active-date-background: var(--el-color-primary-light-9);
    --calendar-color: var(--el-text-color-primary);
    --calendar-background: var(--el-bg-color);
    --calendar-current-color: var(--el-color-primary);
    --calendar-current-background: var(--el-color-primary-light-9);
    --calendar-outside-color: var(--el-text-color-placeholder);
    --calendar-outside-background: var(--el-fill-color-extra-light);
    border-radius: 8px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    font-family: inherit;
  }

  :deep(.q-calendar__button) {
    width: 24px;
    height: 24px;
    line-height: 1;
    border-radius: 999px;
    color: var(--el-text-color-regular);
    font-size: 14px;
    font-weight: 700;
  }

  :deep(.q-calendar-month__head) {
    background: var(--el-fill-color-extra-light);
    color: var(--el-text-color-secondary);
  }

  :deep(.q-calendar-month__head--weekday) {
    min-height: 46px;
    justify-content: center;
    font-size: 14px;
  }

  :deep(.q-calendar-month__day) {
    transition: background-color 0.16s ease, box-shadow 0.16s ease;
  }

  :deep(.q-calendar-month__day:hover) {
    background: var(--el-fill-color-extra-light);
  }

  :deep(.q-calendar-month__day.q-current-day) {
    background: linear-gradient(180deg, var(--el-color-primary-light-9), var(--el-bg-color));
  }

  :deep(.q-calendar-month__day.q-current-day .q-calendar__button) {
    color: var(--el-color-white);
    background: var(--el-color-primary);
    border: none;
  }

  :deep(.q-calendar-month__day.q-outside) {
    background: var(--el-fill-color-extra-light);
  }

  :deep(.q-calendar-month__day--label__wrapper) {
    box-sizing: border-box;
    min-height: 34px;
    padding: 4px 6px 0;
  }
}

.qcal-day-events {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: calc(100% - 34px);
  overflow: hidden;
  padding: 0 6px 6px;
}

.booking-event,
.more-event {
  width: 100%;
  min-height: 24px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-bg-color);
  color: var(--el-text-color-regular);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s ease, background-color 0.15s ease, transform 0.15s ease;
}

.booking-event {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;

  &:hover {
    transform: translateY(-1px);
    border-color: var(--el-color-info-light-7);
  }

  &.pending {
    border-left: 3px solid var(--el-color-warning);
    background: #fffaf0;
  }

  &.confirmed {
    border-left: 3px solid var(--el-color-primary);
    background: var(--el-color-primary-light-9);
  }

  &.completed {
    border-left: 3px solid var(--el-color-success);
    background: #f0f9eb;
  }

  &.cancelled {
    border-left: 3px solid var(--el-color-info);
    background: var(--el-fill-color-light);
    opacity: 0.72;
  }
}

.event-time {
  font-size: 10px;
  font-weight: 700;
  color: var(--el-text-color-secondary);
}

.event-main {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.event-dot {
  width: 4px;
  height: 4px;
  border-radius: 999px;
  background: currentColor;
  flex-shrink: 0;
}

.event-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 10px;
}

.more-event {
  padding: 3px 6px;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  font-weight: 500;
}

.more-list {
  .popover-title {
    margin-bottom: 8px;
    font-weight: 700;
  }
}

.more-item {
  display: grid;
  grid-template-columns: 70px minmax(0, 1fr);
  gap: 8px;
  width: 100%;
  padding: 6px 0;
  border: none;
  border-bottom: 1px dashed var(--el-border-color-lighter);
  background: transparent;
  text-align: left;
  cursor: pointer;

  &:last-child {
    border-bottom: none;
  }

  &:hover strong {
    color: var(--el-color-primary);
  }

  span {
    color: var(--el-text-color-secondary);
    font-size: 12px;
  }

  strong {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 12px;
  }
}

@media (max-width: 860px) {
  .booking-overview {
    .page-header,
    .calendar-toolbar {
      align-items: flex-start;
      flex-direction: column;
    }
  }
}
</style>
