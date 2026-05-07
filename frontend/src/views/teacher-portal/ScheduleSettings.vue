<template>
  <div class="schedule-settings">
    <section class="page-header">
      <div>
        <h2>{{ $t('teacherSchedule.title') }}</h2>
      </div>
      <div class="header-actions">
        <el-button type="danger" size="small" round plain class="h-30px px-2" :disabled="!canManageSlots" @click="openBatchDialog('delete')">
          <template #icon><div class="i-hugeicons:delete-02" /></template>
          {{ $t('teacherSchedulePortal.batchDelete') }}
        </el-button>
        <el-button type="warning" size="small" round plain class="h-30px px-2" :disabled="!canManageSlots" @click="openBatchDialog('update')">
          <template #icon><div class="i-hugeicons:edit-02" /></template>
          {{ $t('teacherSchedulePortal.batchUpdate') }}
        </el-button>
        <el-button type="success" size="small" round plain class="h-30px px-2" :disabled="!canManageSlots" @click="openBatchCreateDialog">
          <template #icon><div class="i-hugeicons:layers-01" /></template>
          {{ $t('teacherSchedulePortal.batchCreate') }}
        </el-button>
        <el-button type="primary" size="small" round class="h-30px px-2" :disabled="!canManageSlots" @click="openCreateDialog()">
          <template #icon><div class="i-hugeicons:plus-sign-square" /></template>
          {{ $t('teacherSchedule.addTimeBtn') }}
        </el-button>
      </div>
    </section>

    <el-card shadow="never">
      <el-form
        :inline="true"
        :model="filters"
        label-position="top"
        size="small"
        class="filter-form flex items-end">
        <el-form-item :label="$t('common.dateRange')">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="~"
            :start-placeholder="$t('common.startDate')"
            :end-placeholder="$t('common.endDate')"
            :disabled-date="disabledScheduleRangeDate"
            class="w-200px! h-30px!"
            clearable
            @change="handleDateRangeChange"
          />
        </el-form-item>
        <el-form-item :label="$t('common.status')">
          <el-select
            v-model="filters.status"
            :placeholder="$t('common.all')"
            clearable
            class="w-150px! h-30px!"
            @change="handleFilterChange"
          >
            <el-option :label="$t('teacherSchedulePortal.statusAvailable')" value="available" />
            <el-option :label="$t('teacherSchedulePortal.statusPartiallyBooked')" value="partially_booked" />
            <el-option :label="$t('teacherSchedulePortal.statusBooked')" value="booked" />
            <el-option :label="$t('teacherSchedulePortal.statusClosed')" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" round class="px-4! h-30px!" @click="handleFilterChange">
            <template #icon><div class="i-hugeicons:search-01" /></template>
            {{ $t('common.search') }}
          </el-button>
          <el-button round class="px-4! h-30px!" @click="resetFilters">
            <template #icon><div class="i-hugeicons:arrow-reload-horizontal" /></template>
            {{ $t('common.btnReset') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="calendar-panel">
      <template #header>
        <div class="calendar-toolbar">
          <div>
            <span class="calendar-title">{{ calendarTitle }}</span>
            <span class="calendar-subtitle">{{ $t('teacherSchedulePortal.total', { total: visibleFilteredSlots.length }) }}</span>
          </div>
          <div class="calendar-actions">
            <el-segmented v-model="calendarView" :options="calendarViewOptions" size="small" />
            <el-button-group>
              <el-button size="small" @click="moveCalendar(-1)">
                <template #icon><div class="i-hugeicons:arrow-left-01" /></template>
              </el-button>
              <el-button size="small" @click="goToday">{{ $t('common.today') }}</el-button>
              <el-button size="small" @click="moveCalendar(1)">
                <template #icon><div class="i-hugeicons:arrow-right-01" /></template>
              </el-button>
            </el-button-group>
            <el-button :loading="loading" size="small" round class="h-30px px-2" @click="fetchSlots">
              <template #icon><div class="i-hugeicons:refresh" /></template>
              {{ $t('common.refresh') }}
            </el-button>
          </div>
        </div>
      </template>

      <div v-loading="loading || contractLoading" class="qcalendar-shell">
        <QCalendarMonth
          v-if="calendarView === 'month'"
          v-model="calendarDate"
          locale="zh-TW"
          animated
          bordered
          hoverable
          no-default-header-btn
          short-weekday-label
          :weekdays="qCalendarWeekdays"
          :day-min-height="132"
          @click-day="handleQCalendarDayClick"
        >
          <template #head-day-label="{ scope }">
            {{ Number(scope.timestamp.day) }}
          </template>
          <template #day="{ scope }">
            <div class="qcal-day-events">
              <button
                v-for="event in getCalendarEventsByDate(scope.timestamp.date).slice(0, 3)"
                :key="event.id"
                class="qcal-event"
                :class="event.status"
                type="button"
                :disabled="!canManageSlots"
                @click.stop="openEditDialog(event.slot)"
              >
                <span class="qcal-event-time">{{ event.timeLabel }}</span>
                <span class="qcal-event-status">
                  <span class="qcal-event-dot" />
                  <span class="qcal-event-title">{{ event.title }}</span>
                </span>
              </button>
              <button
                v-if="getCalendarEventsByDate(scope.timestamp.date).length > 3"
                class="qcal-more"
                type="button"
                :disabled="!canManageSlots"
                @click.stop="handleDateClick(scope.timestamp.date)"
              >
                +{{ getCalendarEventsByDate(scope.timestamp.date).length - 3 }} {{ $t('common.more') }}
              </button>
            </div>
          </template>
        </QCalendarMonth>

        <QCalendarAgenda
          v-else
          v-model="calendarDate"
          view="week"
          locale="zh-TW"
          animated
          bordered
          hoverable
          no-default-header-btn
          short-weekday-label
          :weekdays="qCalendarWeekdays"
          :day-min-height="112"
          @click-day="handleQCalendarDayClick"
        >
          <template #head-day="{ scope }">
            <button
              class="agenda-head-day"
              :class="{ 'is-today': scope.timestamp.current }"
              type="button"
              @click.stop="handleDateClick(scope.timestamp.date)"
            >
              <span class="agenda-head-weekday">{{ formatAgendaWeekday(scope.timestamp.date) }}</span>
              <span class="agenda-head-date">{{ formatAgendaHeaderDate(scope.timestamp.date) }}</span>
            </button>
          </template>

          <template #day="{ scope }">
            <div class="agenda-day">
              <button
                v-for="event in getCalendarEventsByDate(scope.timestamp.date)"
                :key="event.id"
                class="agenda-event"
                :class="event.status"
                type="button"
                :disabled="!canManageSlots"
                @click.stop="openEditDialog(event.slot)"
              >
                <span class="agenda-event-time">{{ event.timeLabel }}</span>
                <span class="agenda-event-content">
                  <strong>
                    <span class="agenda-event-marker" />
                    {{ event.title }}
                  </strong>
                </span>
              </button>
              <button
                v-if="getCalendarEventsByDate(scope.timestamp.date).length === 0 && canCreateSlotOnDate(scope.timestamp.date)"
                class="agenda-empty"
                type="button"
                @click.stop="openCreateDialog(scope.timestamp.date)"
              >
                <div class="inline-flex items-center gap-1.5">
                  <div class="i-hugeicons:calendar-add-01" />
                  <span>{{ $t('teacherSchedulePortal.addSlot') }}</span>
                </div>
              </button>
            </div>
          </template>
        </QCalendarAgenda>
      </div>
    </el-card>

    <el-drawer
      v-model="drawerVisible"
      :title="$t('teacherSchedule.drawerHeader', { date: formattedSelectedDate })"
      direction="rtl"
      size="420px"
    >
      <div class="drawer-actions">
        <el-button v-if="canCreateSlotOnDate(selectedDate)" type="primary" size="small" @click="openCreateDialog(selectedDate)">
          <template #icon><div class="i-hugeicons:plus-sign-square" /></template>
          {{ $t('teacherSchedulePortal.addDailySlot') }}
        </el-button>
      </div>

      <div class="daily-schedule">
        <article
          v-for="slot in dailySlots"
          :key="slot.id"
          class="slot-row"
          :class="getSlotStatus(slot)"
        >
          <div>
            <div class="slot-time">{{ formatSlotTime(slot) }}</div>
            <div class="slot-meta">
              {{ getStatusLabel(slot) }}
              <span v-if="slot.teacher_contract_no"> - {{ slot.teacher_contract_no }}</span>
            </div>
            <p v-if="slot.notes" class="slot-notes">{{ slot.notes }}</p>
          </div>
          <div class="slot-actions">
            <el-button link type="primary" size="small" :disabled="!canManageSlots" @click="openEditDialog(slot)">{{ $t('common.edit') }}</el-button>
            <el-button
              link
              type="danger"
              size="small"
              :disabled="slot.is_booked || !canManageSlots"
              @click="handleDelete(slot)"
            >
              {{ $t('common.delete') }}
            </el-button>
          </div>
        </article>
        <el-empty v-if="dailySlots.length === 0" :description="$t('teacherSchedulePortal.emptyDay')" />
      </div>
    </el-drawer>

    <el-dialog
      v-model="slotDialogVisible"
      :title="slotDialogTitle"
      width="560px"
      destroy-on-close
    >
      <el-form :model="slotForm" label-width="108px">
        <el-form-item :label="createMode === 'batch' ? $t('teacherSchedulePortal.startDate') : $t('teacherSchedule.date')" required>
          <el-date-picker
            v-model="slotForm.date"
            type="date"
            value-format="YYYY-MM-DD"
            :placeholder="$t('teacherSchedulePortal.selectDate')"
            :disabled="isEditingBookedSlot"
            :disabled-date="disabledSlotDate"
            class="w-full"
          />
        </el-form-item>

        <el-form-item :label="$t('teacherSchedule.timeRange')" required>
          <div class="time-row">
            <el-time-picker
              v-model="slotForm.timeRange"
              is-range
              format="HH:mm"
              value-format="HH:mm"
              range-separator="~"
              :start-placeholder="$t('teacherSchedulePortal.startTime')"
              :end-placeholder="$t('teacherSchedulePortal.endTime')"
              :disabled="slotForm.isAllDay || isEditingBookedSlot"
              class="time-picker"
            />
            <el-checkbox v-model="slotForm.isAllDay" :disabled="isEditingBookedSlot">
              {{ $t('teacherSchedule.allDay') }}
            </el-checkbox>
          </div>
        </el-form-item>

        <el-form-item :label="$t('teacherSchedulePortal.bookingOpen')">
          <el-switch
            v-model="slotForm.isAvailable"
            inline-prompt
            :active-text="$t('teacherSchedulePortal.on')"
            :inactive-text="$t('teacherSchedulePortal.off')"
          />
        </el-form-item>

        <el-form-item :label="$t('teacherSchedule.description')">
          <el-input
            v-model="slotForm.notes"
            type="textarea"
            :rows="3"
            maxlength="200"
            show-word-limit
            :placeholder="$t('teacherSchedulePortal.notesPlaceholder')"
          />
        </el-form-item>

        <template v-if="!isEditMode">
          <el-form-item v-if="createMode === 'single'" :label="$t('teacherSchedule.repeat')">
            <el-select v-model="slotForm.repeatType" class="w-full">
              <el-option :label="$t('teacherSchedule.repeatNone')" value="none" />
              <el-option :label="$t('teacherSchedule.repeatCustom')" value="custom" />
            </el-select>
          </el-form-item>

          <template v-if="createMode === 'batch' || slotForm.repeatType === 'custom'">
            <el-form-item :label="$t('teacherSchedule.weekDays')" required>
              <el-checkbox-group v-model="slotForm.weekdays">
                <el-checkbox-button
                  v-for="day in weekdayOptions"
                  :key="day.value"
                  :label="day.value"
                >
                  {{ day.label }}
                </el-checkbox-button>
              </el-checkbox-group>
            </el-form-item>

            <el-form-item :label="$t('teacherSchedule.endCondition')">
              <el-radio-group v-model="slotForm.endType">
                <el-radio label="date">{{ $t('teacherSchedule.endDate') }}</el-radio>
                <el-radio label="count">{{ $t('teacherSchedule.count') }}</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item v-if="slotForm.endType === 'date'" :label="$t('teacherSchedule.endDate')" required>
              <el-date-picker
                v-model="slotForm.endDate"
                type="date"
                value-format="YYYY-MM-DD"
                :placeholder="$t('teacherSchedulePortal.selectEndDate')"
                :disabled-date="disabledBatchEndDate"
                class="w-full"
              />
            </el-form-item>

            <el-form-item v-else :label="$t('teacherSchedule.count')" required>
              <el-input-number v-model="slotForm.repeatCount" :min="1" :max="60" />
              <span class="count-unit">{{ $t('teacherSchedule.times') }}</span>
            </el-form-item>
          </template>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="slotDialogVisible = false">{{ $t('teacherSchedule.cancelBtn') }}</el-button>
        <el-button type="primary" :loading="saving" :disabled="!canManageSlots" @click="saveSlot">
          {{ $t('teacherSchedule.saveBtn') }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="batchDialogVisible"
      :title="batchDialogTitle"
      width="620px"
      destroy-on-close
    >
      <el-alert
        v-if="batchMode === 'delete'"
        :title="$t('teacherSchedulePortal.batchDeleteHint')"
        type="warning"
        :closable="false"
        show-icon
        class="batch-alert"
      />
      <el-alert
        v-else
        :title="$t('teacherSchedulePortal.batchUpdateHint')"
        type="info"
        :closable="false"
        show-icon
        class="batch-alert"
      />

      <el-form :model="batchForm" label-width="118px">
        <el-form-item :label="$t('common.dateRange')" required>
          <el-date-picker
            v-model="batchForm.dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="~"
            :start-placeholder="$t('common.startDate')"
            :end-placeholder="$t('common.endDate')"
            :disabled-date="disabledBatchRangeDate"
            class="w-full"
          />
        </el-form-item>

        <el-form-item :label="$t('teacherSchedulePortal.weekday')">
          <div class="form-hint-row">
            <el-checkbox-group v-model="batchForm.weekdays">
              <el-checkbox-button
                v-for="day in weekdayOptions"
                :key="day.value"
                :label="day.value"
              >
                {{ day.label }}
              </el-checkbox-button>
            </el-checkbox-group>
            <span class="form-hint">{{ $t('teacherSchedulePortal.weekdayAllHint') }}</span>
          </div>
        </el-form-item>

        <el-form-item :label="$t('teacherSchedulePortal.filterTime')">
          <el-time-picker
            v-model="batchForm.filterTimeRange"
            is-range
            format="HH:mm"
            value-format="HH:mm"
            range-separator="~"
            :start-placeholder="$t('teacherSchedulePortal.startTime')"
            :end-placeholder="$t('teacherSchedulePortal.endTime')"
            clearable
            class="w-full"
          />
        </el-form-item>

        <template v-if="batchMode === 'update'">
          <el-divider content-position="left">{{ $t('teacherSchedulePortal.updateContent') }}</el-divider>

          <el-form-item :label="$t('teacherSchedulePortal.newTime')">
            <el-time-picker
              v-model="batchForm.newTimeRange"
              is-range
              format="HH:mm"
              value-format="HH:mm"
              range-separator="~"
              :start-placeholder="$t('teacherSchedulePortal.newStartTime')"
              :end-placeholder="$t('teacherSchedulePortal.newEndTime')"
              clearable
              class="w-full"
            />
          </el-form-item>

          <el-form-item :label="$t('teacherSchedulePortal.bookingOpenStatus')">
            <div class="switch-row">
              <el-checkbox v-model="batchForm.shouldUpdateAvailability">
                {{ $t('teacherSchedulePortal.updateBookingOpenStatus') }}
              </el-checkbox>
              <el-switch
                v-model="batchForm.isAvailable"
                inline-prompt
                :active-text="$t('teacherSchedulePortal.on')"
                :inactive-text="$t('teacherSchedulePortal.off')"
                :disabled="!batchForm.shouldUpdateAvailability"
              />
            </div>
          </el-form-item>

          <el-form-item :label="$t('common.note')">
            <div class="notes-update">
              <el-checkbox v-model="batchForm.shouldUpdateNotes">
                {{ $t('teacherSchedulePortal.updateNotes') }}
              </el-checkbox>
              <el-input
                v-model="batchForm.notes"
                type="textarea"
                :rows="3"
                maxlength="200"
                show-word-limit
                :placeholder="$t('teacherSchedulePortal.batchNotesPlaceholder')"
                :disabled="!batchForm.shouldUpdateNotes"
              />
            </div>
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="batchDialogVisible = false">{{ $t('teacherSchedule.cancelBtn') }}</el-button>
        <el-button
          :type="batchMode === 'delete' ? 'danger' : 'primary'"
          :loading="batchSaving"
          :disabled="!canManageSlots"
          @click="submitBatchAction"
        >
          {{ batchMode === 'delete' ? $t('teacherSchedulePortal.batchDelete') : $t('teacherSchedulePortal.batchUpdate') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import dayjs from 'dayjs';
import { ElMessage, ElMessageBox } from 'element-plus';
import { QCalendarAgenda, QCalendarMonth } from '@quasar/quasar-ui-qcalendar';
import '@quasar/quasar-ui-qcalendar/index.css';
import { useAuthStore } from '@/stores/auth';
import {
  batchDeleteTeacherSlots,
  batchCreateTeacherSlots,
  batchUpdateTeacherSlots,
  createTeacherSlot,
  deleteTeacherSlot,
  getMyTeacherContracts,
  getTeacherSlots,
  updateTeacherSlot,
  type TeacherContractOption,
  type TeacherSlotBatchCreate,
  type TeacherSlotBatchDelete,
  type TeacherSlotBatchUpdate,
  type TeacherSlotCreate,
  type TeacherSlotParams,
  type TeacherSlotResponse,
  type TeacherSlotUpdate,
} from '@/api/teacherSlot';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';

type SlotStatus = 'available' | 'partially_booked' | 'booked' | 'closed';
type SlotStatusFilter = '' | SlotStatus;
type RepeatType = 'none' | 'custom';
type EndType = 'date' | 'count';
type CreateMode = 'single' | 'batch';
type BatchMode = 'update' | 'delete';
type CalendarView = 'month' | 'agenda';

interface CalendarSlotEvent {
  id: string;
  slot: TeacherSlotResponse;
  status: SlotStatus;
  title: string;
  timeLabel: string;
}

const { t } = useI18n();
const authStore = useAuthStore();

const calendarDate = ref(dayjs().format('YYYY-MM-DD'));
const currentDate = computed(() => dayjs(calendarDate.value).toDate());
const selectedDate = ref(dayjs().format('YYYY-MM-DD'));
const drawerVisible = ref(false);
const loading = ref(false);
const saving = ref(false);
const batchSaving = ref(false);
const contractLoading = ref(false);

const slots = ref<TeacherSlotResponse[]>([]);
const teacherContracts = ref<TeacherContractOption[]>([]);
const teacherContractAlertShown = ref(false);
const isDateRangeSyncedToCalendar = ref(true);
const calendarView = ref<CalendarView>('agenda');
const qCalendarWeekdays = [1, 2, 3, 4, 5, 6, 0];
const calendarViewOptions = computed(() => [
  { label: t('teacherSchedulePortal.viewWeek'), value: 'agenda' },
  { label: t('teacherSchedulePortal.viewMonth'), value: 'month' },
]);

const filters = reactive({
  dateRange: getDefaultQueryRange(currentDate.value),
  status: '' as SlotStatusFilter,
});

const slotDialogVisible = ref(false);
const isEditMode = ref(false);
const editingSlot = ref<TeacherSlotResponse | null>(null);
const createMode = ref<CreateMode>('single');
const batchDialogVisible = ref(false);
const batchMode = ref<BatchMode>('update');

const slotForm = reactive({
  date: '',
  timeRange: ['09:00', '10:00'] as string[],
  isAllDay: false,
  isAvailable: true,
  notes: '',
  repeatType: 'none' as RepeatType,
  weekdays: [] as number[],
  endType: 'date' as EndType,
  endDate: '',
  repeatCount: 4,
});

const batchForm = reactive({
  dateRange: getDefaultQueryRange(currentDate.value),
  weekdays: [] as number[],
  filterTimeRange: [] as string[],
  newTimeRange: [] as string[],
  shouldUpdateAvailability: false,
  isAvailable: true,
  shouldUpdateNotes: false,
  notes: '',
});

const currentTeacherId = computed(() => authStore.userInfo?.teacher_id || '');
const currentTeacherContractId = computed(() => teacherContracts.value[0]?.id || '');
const canManageSlots = computed(() => Boolean(currentTeacherId.value && currentTeacherContractId.value));

const weekdayOptions = computed(() => [
  { value: 0, label: t('teacherSchedule.mon') },
  { value: 1, label: t('teacherSchedule.tue') },
  { value: 2, label: t('teacherSchedule.wed') },
  { value: 3, label: t('teacherSchedule.thu') },
  { value: 4, label: t('teacherSchedule.fri') },
  { value: 5, label: t('teacherSchedule.sat') },
  { value: 6, label: t('teacherSchedule.sun') },
]);

const queryRange = computed(() => {
  if (filters.dateRange?.length === 2) {
    const [start, end] = normalizeScheduleRange(filters.dateRange);
    return {
      start,
      end,
    };
  }

  const [start, end] = getDefaultQueryRange(currentDate.value);
  return {
    start,
    end,
  };
});

const filteredSlots = computed(() => {
  const status = filters.status;
  return slots.value.filter((slot) => !status || getSlotStatus(slot) === status);
});

const visibleRange = computed(() => {
  if (calendarView.value === 'month') {
    return normalizeScheduleRange([
      dayjs(calendarDate.value).startOf('month').format('YYYY-MM-DD'),
      dayjs(calendarDate.value).endOf('month').format('YYYY-MM-DD'),
    ]);
  }

  const start = getAgendaWeekStart(calendarDate.value);
  return normalizeScheduleRange([
    start.format('YYYY-MM-DD'),
    start.add(6, 'day').format('YYYY-MM-DD'),
  ]);
});

const visibleFilteredSlots = computed(() => filteredSlots.value.filter(isSlotInVisibleRange));

const calendarTitle = computed(() => {
  if (calendarView.value === 'month') {
    return dayjs(calendarDate.value).format('YYYY 年 MM 月');
  }

  const start = getAgendaWeekStart(calendarDate.value);
  const end = start.add(6, 'day');
  return `${start.format('YYYY/MM/DD')} ~ ${end.format('MM/DD')}`;
});

const calendarEventsByDate = computed(() => {
  return filteredSlots.value.reduce<Record<string, CalendarSlotEvent[]>>((acc, slot) => {
    const status = getSlotStatus(slot);
    const event: CalendarSlotEvent = {
      id: slot.id,
      slot,
      status,
      title: getStatusLabel(slot),
      timeLabel: formatSlotTime(slot),
    };
    const events = acc[slot.slot_date] ?? (acc[slot.slot_date] = []);
    events.push(event);
    return acc;
  }, {});
});

const dailySlots = computed(() => {
  return filteredSlots.value
    .filter((slot) => slot.slot_date === selectedDate.value)
    .sort((a, b) => `${a.slot_date} ${a.start_time}`.localeCompare(`${b.slot_date} ${b.start_time}`));
});

const formattedSelectedDate = computed(() => dayjs(selectedDate.value).format('YYYY/MM/DD dddd'));
const slotDialogTitle = computed(() => {
  if (isEditMode.value) return t('teacherSchedulePortal.editSlotTitle');
  if (createMode.value === 'batch') return t('teacherSchedulePortal.batchCreateTitle');
  return t('teacherSchedule.dialogTitle');
});
const batchDialogTitle = computed(() => (
  batchMode.value === 'delete'
    ? t('teacherSchedulePortal.batchDeleteTitle')
    : t('teacherSchedulePortal.batchUpdateTitle')
));
const isEditingBookedSlot = computed(() => Boolean(isEditMode.value && editingSlot.value?.is_booked));
const calendarMonthKey = computed(() => dayjs(currentDate.value).format('YYYY-MM'));

onMounted(async () => {
  await loadMyTeacherContracts();
  if (canManageSlots.value) {
    await fetchSlots();
  }
});

watch(calendarMonthKey, () => {
  if (isDateRangeSyncedToCalendar.value) {
    filters.dateRange = getDefaultQueryRange(currentDate.value);
    fetchSlots();
  }
});

function getDefaultQueryRange(date: Date) {
  return normalizeScheduleRange([
    dayjs(date).startOf('month').subtract(7, 'day').format('YYYY-MM-DD'),
    dayjs(date).endOf('month').add(7, 'day').format('YYYY-MM-DD'),
  ]);
}

function getAgendaWeekStart(date: dayjs.ConfigType) {
  const value = dayjs(date);
  const daysFromMonday = (value.day() + 6) % 7;
  return value.subtract(daysFromMonday, 'day');
}

function isSlotInVisibleRange(slot: TeacherSlotResponse) {
  const [start, end] = visibleRange.value;
  const date = dayjs(slot.slot_date);
  return !date.isBefore(dayjs(start), 'day') && !date.isAfter(dayjs(end), 'day');
}

function getScheduleMinDate() {
  return dayjs().startOf('day');
}

function getScheduleMaxDate() {
  return dayjs().add(3, 'month').startOf('day');
}

function clampScheduleDate(date: dayjs.ConfigType) {
  const value = dayjs(date);
  if (!value.isValid()) return getScheduleMinDate();
  if (value.isBefore(getScheduleMinDate(), 'day')) return getScheduleMinDate();
  if (value.isAfter(getScheduleMaxDate(), 'day')) return getScheduleMaxDate();
  return value;
}

function normalizeScheduleRange(range: string[]) {
  const start = clampScheduleDate(range[0]);
  const end = clampScheduleDate(range[1]);

  if (end.isBefore(start, 'day')) {
    return [start.format('YYYY-MM-DD'), start.format('YYYY-MM-DD')];
  }

  return [start.format('YYYY-MM-DD'), end.format('YYYY-MM-DD')];
}

function isWithinScheduleRange(date: dayjs.ConfigType) {
  const value = dayjs(date);
  return value.isValid()
    && !value.isBefore(getScheduleMinDate(), 'day')
    && !value.isAfter(getScheduleMaxDate(), 'day');
}

function canCreateSlotOnDate(date: dayjs.ConfigType) {
  return canManageSlots.value && isWithinScheduleRange(date);
}

function disabledScheduleRangeDate(time: Date) {
  return !isWithinScheduleRange(time);
}

function getSlotStatus(slot: TeacherSlotResponse): SlotStatus {
  if (slot.is_booked) return 'booked';
  if ((slot.booking_count || 0) > 0) return 'partially_booked';
  if (!slot.is_available) return 'closed';
  return 'available';
}

function getStatusLabel(slot: TeacherSlotResponse) {
  const status = getSlotStatus(slot);
  if (status === 'booked') return t('teacherSchedulePortal.statusFullyBooked');
  if (status === 'partially_booked') {
    return t('teacherSchedulePortal.statusPartiallyBookedCount', { count: slot.booking_count || 0 });
  }
  if (status === 'closed') return t('teacherSchedulePortal.statusClosed');
  return t('teacherSchedulePortal.statusAvailable');
}

function getCalendarEventsByDate(date: string) {
  return (calendarEventsByDate.value[date] || []).sort((a, b) =>
    `${a.slot.slot_date} ${a.slot.start_time}`.localeCompare(`${b.slot.slot_date} ${b.slot.start_time}`),
  );
}

function formatSlotTime(slot: TeacherSlotResponse) {
  return `${normalizeTime(slot.start_time)} ~ ${normalizeTime(slot.end_time)}`;
}

function formatAgendaWeekday(date: string) {
  const weekdays = [
    t('teacherSchedule.sun'),
    t('teacherSchedule.mon'),
    t('teacherSchedule.tue'),
    t('teacherSchedule.wed'),
    t('teacherSchedule.thu'),
    t('teacherSchedule.fri'),
    t('teacherSchedule.sat'),
  ];
  return weekdays[dayjs(date).day()];
}

function formatAgendaHeaderDate(date: string) {
  return dayjs(date).format('MM/DD');
}

function normalizeTime(value?: string | null) {
  return value ? value.slice(0, 5) : '';
}

function toTimePayload(value: string) {
  return value.length === 5 ? `${value}:00` : value;
}

function resolveTeacherId() {
  return currentTeacherId.value;
}

function resolveTeacherContractId() {
  return currentTeacherContractId.value;
}

async function showMissingContractAlert() {
  if (teacherContractAlertShown.value) return;
  teacherContractAlertShown.value = true;
  await ElMessageBox.alert(
    t('teacherSchedulePortal.missingContractPermission'),
    t('teacherSchedulePortal.missingContractTitle'),
    {
      confirmButtonText: t('common.confirm'),
      type: 'warning',
    },
  );
}

function ensureTeacherContractAccess() {
  if (canManageSlots.value) return true;
  ElMessage.warning(t('teacherSchedulePortal.missingContractPermission'));
  return false;
}

async function loadMyTeacherContracts() {
  contractLoading.value = true;
  try {
    const res = assertApiSuccess(await getMyTeacherContracts(), t('teacherSchedulePortal.loadContractsFailed'));
    teacherContracts.value = res.data || [];

    if (teacherContracts.value.length === 0) {
      slots.value = [];
      await showMissingContractAlert();
    }
  } catch (error) {
    console.error(error);
    teacherContracts.value = [];
    slots.value = [];
    ElMessage.error(getApiErrorMessage(error, t('teacherSchedulePortal.loadContractsFailed')));
  } finally {
    contractLoading.value = false;
  }
}

async function fetchSlots() {
  if (!canManageSlots.value) {
    slots.value = [];
    return;
  }

  const teacherId = resolveTeacherId();
  if (!teacherId) {
    slots.value = [];
    ElMessage.warning(t('teacherSchedulePortal.missingTeacherLoad'));
    return;
  }

  loading.value = true;
  try {
    const allSlots: TeacherSlotResponse[] = [];
    let page = 1;
    let totalPages = 1;

    do {
      const params: TeacherSlotParams = {
        page,
        per_page: 100,
        teacher_id: teacherId,
        date_from: queryRange.value.start,
        date_to: queryRange.value.end,
      };

      if (filters.status === 'available') {
        params.is_available = true;
      } else if (filters.status === 'closed') {
        params.is_available = false;
      }

      const res = assertApiSuccess(await getTeacherSlots(params), t('teacherSchedulePortal.loadFailed'));
      allSlots.push(...(res.data || []));
      totalPages = res.total_pages || 1;

      if (!res.data || res.data.length === 0) break;
      page += 1;
    } while (page <= totalPages);

    slots.value = allSlots.sort((a, b) => `${a.slot_date} ${a.start_time}`.localeCompare(`${b.slot_date} ${b.start_time}`));
  } catch (error) {
    console.error(error);
    ElMessage.error(getApiErrorMessage(error, t('teacherSchedulePortal.loadFailed')));
  } finally {
    loading.value = false;
  }
}

function handleFilterChange() {
  if (!filters.dateRange || filters.dateRange.length !== 2) {
    filters.dateRange = getDefaultQueryRange(currentDate.value);
    isDateRangeSyncedToCalendar.value = true;
  } else {
    filters.dateRange = normalizeScheduleRange(filters.dateRange);
  }
  fetchSlots();
}

function handleDateRangeChange() {
  if (!filters.dateRange || filters.dateRange.length !== 2) {
    filters.dateRange = getDefaultQueryRange(currentDate.value);
    isDateRangeSyncedToCalendar.value = true;
  } else {
    filters.dateRange = normalizeScheduleRange(filters.dateRange);
    isDateRangeSyncedToCalendar.value = false;
  }
  handleFilterChange();
}

function resetFilters() {
  filters.dateRange = getDefaultQueryRange(currentDate.value);
  filters.status = '';
  isDateRangeSyncedToCalendar.value = true;
  fetchSlots();
}

function moveCalendar(amount: number) {
  const unit = calendarView.value === 'month' ? 'month' : 'week';
  calendarDate.value = clampScheduleDate(dayjs(calendarDate.value).add(amount, unit)).format('YYYY-MM-DD');
  isDateRangeSyncedToCalendar.value = true;
}

function goToday() {
  calendarDate.value = getScheduleMinDate().format('YYYY-MM-DD');
  selectedDate.value = calendarDate.value;
  isDateRangeSyncedToCalendar.value = true;
}

function handleDateClick(day: string) {
  if (!isWithinScheduleRange(day)) {
    ElMessage.warning(t('teacherSchedulePortal.outOfRange'));
    return;
  }

  selectedDate.value = day;
  drawerVisible.value = true;
}

function handleQCalendarDayClick(payload: any) {
  const day = payload?.scope?.timestamp?.date || payload?.timestamp?.date;
  if (day) {
    calendarDate.value = clampScheduleDate(day).format('YYYY-MM-DD');
    handleDateClick(day);
  }
}

function openCreateDialog(date?: string) {
  if (!ensureTeacherContractAccess()) return;
  if (date && !isWithinScheduleRange(date)) {
    ElMessage.warning(t('teacherSchedulePortal.outOfRange'));
    return;
  }

  const baseDate = clampScheduleDate(date || selectedDate.value || dayjs()).format('YYYY-MM-DD');
  createMode.value = 'single';
  isEditMode.value = false;
  editingSlot.value = null;
  Object.assign(slotForm, {
    date: baseDate,
    timeRange: ['09:00', '10:00'],
    isAllDay: false,
    isAvailable: true,
    notes: '',
    repeatType: 'none' as RepeatType,
    weekdays: [dayjs(baseDate).day() === 0 ? 6 : dayjs(baseDate).day() - 1],
    endType: 'date' as EndType,
    endDate: clampScheduleDate(dayjs(baseDate).add(1, 'month')).format('YYYY-MM-DD'),
    repeatCount: 4,
  });
  slotDialogVisible.value = true;
}

function openBatchCreateDialog() {
  if (!ensureTeacherContractAccess()) return;

  const [startDate, endDate] = filters.dateRange?.length === 2
    ? normalizeScheduleRange(filters.dateRange)
    : getDefaultQueryRange(currentDate.value);

  createMode.value = 'batch';
  isEditMode.value = false;
  editingSlot.value = null;
  Object.assign(slotForm, {
    date: startDate,
    timeRange: ['09:00', '10:00'],
    isAllDay: false,
    isAvailable: true,
    notes: '',
    repeatType: 'custom' as RepeatType,
    weekdays: [],
    endType: 'date' as EndType,
    endDate,
    repeatCount: 4,
  });
  slotDialogVisible.value = true;
}

function openEditDialog(slot: TeacherSlotResponse) {
  if (!ensureTeacherContractAccess()) return;

  createMode.value = 'single';
  isEditMode.value = true;
  editingSlot.value = slot;
  Object.assign(slotForm, {
    date: slot.slot_date,
    timeRange: [normalizeTime(slot.start_time), normalizeTime(slot.end_time)],
    isAllDay: false,
    isAvailable: slot.is_available,
    notes: slot.notes || '',
    repeatType: 'none' as RepeatType,
    weekdays: [],
    endType: 'date' as EndType,
    endDate: '',
    repeatCount: 4,
  });
  slotDialogVisible.value = true;
}

function openBatchDialog(mode: BatchMode) {
  if (!ensureTeacherContractAccess()) return;

  batchMode.value = mode;
  resetBatchForm();
  batchDialogVisible.value = true;
}

function resetBatchForm() {
  Object.assign(batchForm, {
    dateRange: filters.dateRange?.length === 2
      ? normalizeScheduleRange(filters.dateRange)
      : getDefaultQueryRange(currentDate.value),
    weekdays: [] as number[],
    filterTimeRange: [] as string[],
    newTimeRange: [] as string[],
    shouldUpdateAvailability: false,
    isAvailable: true,
    shouldUpdateNotes: false,
    notes: '',
  });
}

async function saveSlot() {
  if (!ensureTeacherContractAccess()) return;

  const teacherId = resolveTeacherId();
  const teacherContractId = resolveTeacherContractId();
  if (!teacherId) {
    ElMessage.warning(t('teacherSchedulePortal.missingTeacherSave'));
    return;
  }

  const times = resolveTimeRange();
  if (!slotForm.date || !times) return;
  if (!isWithinScheduleRange(slotForm.date)) {
    ElMessage.warning(t('teacherSchedulePortal.outOfRange'));
    return;
  }

  saving.value = true;
  try {
    if (isEditMode.value && editingSlot.value) {
      const payload: TeacherSlotUpdate = {
        teacher_contract_id: teacherContractId,
        is_available: slotForm.isAvailable,
        notes: slotForm.notes,
      };

      if (!editingSlot.value.is_booked) {
        payload.slot_date = slotForm.date;
        payload.start_time = times.start;
        payload.end_time = times.end;
      }

      const res = assertApiSuccess(await updateTeacherSlot(editingSlot.value.id, payload), t('teacherSchedulePortal.updateSlotFailed'));
      ElMessage.success(res.message || t('teacherSchedulePortal.updateSlotSuccess'));
    } else if (createMode.value === 'batch' || slotForm.repeatType === 'custom') {
      if (slotForm.weekdays.length === 0) {
        ElMessage.warning(t('teacherSchedulePortal.selectWeekday'));
        return;
      }

      const endDate = resolveBatchEndDate();
      if (!endDate) return;

      const payload: TeacherSlotBatchCreate = {
        teacher_id: teacherId,
        teacher_contract_id: teacherContractId,
        start_date: slotForm.date,
        end_date: endDate,
        weekdays: [...slotForm.weekdays].sort((a, b) => a - b),
        start_time: times.start,
        end_time: times.end,
        notes: slotForm.notes || undefined,
      };

      const res = assertApiSuccess(await batchCreateTeacherSlots(payload), t('teacherSchedulePortal.batchCreateFailed'));
      ElMessage.success(res.message || t('teacherSchedulePortal.createSuccess'));
    } else {
      const payload: TeacherSlotCreate = {
        teacher_id: teacherId,
        teacher_contract_id: teacherContractId,
        slot_date: slotForm.date,
        start_time: times.start,
        end_time: times.end,
        is_available: slotForm.isAvailable,
        notes: slotForm.notes || undefined,
      };

      const res = assertApiSuccess(await createTeacherSlot(payload), t('teacherSchedulePortal.createFailed'));
      ElMessage.success(res.message || t('teacherSchedulePortal.createSuccess'));
    }

    slotDialogVisible.value = false;
    selectedDate.value = slotForm.date;
    await fetchSlots();
  } catch (error) {
    console.error(error);
    ElMessage.error(getApiErrorMessage(error, t('teacherSchedulePortal.saveFailed')));
  } finally {
    saving.value = false;
  }
}

async function submitBatchAction() {
  if (!ensureTeacherContractAccess()) return;

  const teacherId = resolveTeacherId();
  const teacherContractId = resolveTeacherContractId();
  if (!teacherId) {
    ElMessage.warning(t('teacherSchedulePortal.missingTeacherBatch'));
    return;
  }

  if (!batchForm.dateRange || batchForm.dateRange.length !== 2) {
    ElMessage.warning(t('teacherSchedulePortal.selectBatchRange'));
    return;
  }

  const startDate = batchForm.dateRange[0];
  const endDate = batchForm.dateRange[1];
  if (!startDate || !endDate) {
    ElMessage.warning(t('teacherSchedulePortal.selectBatchRange'));
    return;
  }

  if (dayjs(endDate).isBefore(dayjs(startDate), 'day')) {
    ElMessage.warning(t('teacherSchedulePortal.endDateBeforeStart'));
    return;
  }

  if (!isWithinScheduleRange(startDate) || !isWithinScheduleRange(endDate)) {
    ElMessage.warning(t('teacherSchedulePortal.batchRangeOutOfRange'));
    return;
  }

  const filterTimeRange = resolveOptionalTimeRange(batchForm.filterTimeRange, t('teacherSchedulePortal.filterTimeLabel'));
  if (filterTimeRange === false) return;

  batchSaving.value = true;
  try {
    if (batchMode.value === 'delete') {
      await ElMessageBox.confirm(
        t('teacherSchedulePortal.confirmBatchDeleteMessage', { startDate, endDate }),
        t('teacherSchedulePortal.confirmBatchDeleteTitle'),
        {
          confirmButtonText: t('teacherSchedulePortal.batchDelete'),
          cancelButtonText: t('common.cancel'),
          type: 'warning',
        },
      );

      const payload: TeacherSlotBatchDelete = {
        teacher_id: teacherId,
        teacher_contract_id: teacherContractId,
        start_date: startDate,
        end_date: endDate,
        weekdays: batchForm.weekdays.length > 0 ? [...batchForm.weekdays].sort((a, b) => a - b) : undefined,
        start_time: filterTimeRange?.start,
        end_time: filterTimeRange?.end,
      };

      const res = assertApiSuccess(await batchDeleteTeacherSlots(payload), t('teacherSchedulePortal.batchActionFailed', { action: t('teacherSchedulePortal.batchDelete') }));
      ElMessage.success(res.message || t('teacherSchedulePortal.batchDeleteSuccess'));
    } else {
      const newTimeRange = resolveOptionalTimeRange(batchForm.newTimeRange, t('teacherSchedulePortal.newTimeLabel'));
      if (newTimeRange === false) return;

      if (!newTimeRange && !batchForm.shouldUpdateAvailability && !batchForm.shouldUpdateNotes) {
        ElMessage.warning(t('teacherSchedulePortal.selectBatchUpdateContent'));
        return;
      }

      const payload: TeacherSlotBatchUpdate = {
        teacher_id: teacherId,
        teacher_contract_id: teacherContractId,
        start_date: startDate,
        end_date: endDate,
        weekdays: batchForm.weekdays.length > 0 ? [...batchForm.weekdays].sort((a, b) => a - b) : undefined,
        filter_start_time: filterTimeRange?.start,
        filter_end_time: filterTimeRange?.end,
        new_start_time: newTimeRange?.start,
        new_end_time: newTimeRange?.end,
        is_available: batchForm.shouldUpdateAvailability ? batchForm.isAvailable : undefined,
        notes: batchForm.shouldUpdateNotes ? batchForm.notes : undefined,
      };

      const res = assertApiSuccess(await batchUpdateTeacherSlots(payload), t('teacherSchedulePortal.batchActionFailed', { action: t('teacherSchedulePortal.batchUpdate') }));
      ElMessage.success(res.message || t('teacherSchedulePortal.batchUpdateSuccess'));
    }

    batchDialogVisible.value = false;
    await fetchSlots();
  } catch (error) {
    if (error === 'cancel') return;
    console.error(error);
    ElMessage.error(getApiErrorMessage(
      error,
      t('teacherSchedulePortal.batchActionFailed', {
        action: batchMode.value === 'delete' ? t('teacherSchedulePortal.batchDelete') : t('teacherSchedulePortal.batchUpdate'),
      }),
    ));
  } finally {
    batchSaving.value = false;
  }
}

function resolveTimeRange() {
  const start = slotForm.isAllDay ? '06:00:00' : toTimePayload(slotForm.timeRange?.[0] || '');
  const end = slotForm.isAllDay ? '23:59:00' : toTimePayload(slotForm.timeRange?.[1] || '');

  if (!start || !end) {
    ElMessage.warning(t('teacherSchedulePortal.selectTimeRange'));
    return null;
  }

  if (start >= end) {
    ElMessage.warning(t('teacherSchedulePortal.invalidTimeRange'));
    return null;
  }

  return { start, end };
}

function resolveOptionalTimeRange(range: string[], label: string) {
  if (!range || range.length === 0) return null;

  const start = toTimePayload(range[0] || '');
  const end = toTimePayload(range[1] || '');

  if (!start || !end) {
    ElMessage.warning(t('teacherSchedulePortal.incompleteTimeRange', { label }));
    return false;
  }

  if (start >= end) {
    ElMessage.warning(t('teacherSchedulePortal.invalidOptionalTimeRange', { label }));
    return false;
  }

  return { start, end };
}

function resolveBatchEndDate() {
  if (slotForm.endType === 'date') {
    if (!slotForm.endDate) {
      ElMessage.warning(t('teacherSchedulePortal.selectRepeatEndDate'));
      return '';
    }
    if (dayjs(slotForm.endDate).isBefore(dayjs(slotForm.date), 'day')) {
      ElMessage.warning(t('teacherSchedulePortal.endDateBeforeStart'));
      return '';
    }
    if (!isWithinScheduleRange(slotForm.endDate)) {
      ElMessage.warning(t('teacherSchedulePortal.repeatEndOutOfRange'));
      return '';
    }
    return slotForm.endDate;
  }

  let cursor = dayjs(slotForm.date);
  let matchedCount = 0;
  const selectedWeekdays = new Set(slotForm.weekdays);

  for (let guard = 0; guard < 370; guard += 1) {
    if (cursor.isAfter(getScheduleMaxDate(), 'day')) {
      ElMessage.warning(t('teacherSchedulePortal.repeatCountOutOfRange'));
      return '';
    }

    const backendWeekday = cursor.day() === 0 ? 6 : cursor.day() - 1;
    if (selectedWeekdays.has(backendWeekday)) {
      matchedCount += 1;
      if (matchedCount >= slotForm.repeatCount) {
        if (!isWithinScheduleRange(cursor)) {
          ElMessage.warning(t('teacherSchedulePortal.repeatCountOutOfRange'));
          return '';
        }
        return cursor.format('YYYY-MM-DD');
      }
    }
    cursor = cursor.add(1, 'day');
  }

  ElMessage.warning(t('teacherSchedulePortal.repeatEndCalcFailed'));
  return '';
}

async function handleDelete(slot: TeacherSlotResponse) {
  if (!ensureTeacherContractAccess()) return;

  if (slot.is_booked) {
    ElMessage.warning(t('teacherSchedulePortal.bookedDeleteBlocked'));
    return;
  }

  try {
    await ElMessageBox.confirm(
      t('teacherSchedulePortal.confirmDeleteMessage', { date: slot.slot_date, time: formatSlotTime(slot) }),
      t('teacherSchedule.confirmRemoveTitle'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      },
    );

    const res = assertApiSuccess(await deleteTeacherSlot(slot.id, {
      teacher_contract_id: resolveTeacherContractId(),
    }), t('teacherSchedulePortal.deleteFailed'));
    ElMessage.success(res.message || t('teacherSchedulePortal.deleteSuccess'));
    await fetchSlots();
  } catch (error) {
    if (error === 'cancel') return;
    console.error(error);
    ElMessage.error(getApiErrorMessage(error, t('teacherSchedulePortal.deleteFailed')));
  }
}

function disabledSlotDate(time: Date) {
  return disabledScheduleRangeDate(time);
}

function disabledBatchRangeDate(time: Date) {
  return disabledScheduleRangeDate(time);
}

function disabledBatchEndDate(time: Date) {
  const date = dayjs(time);
  const start = dayjs(slotForm.date || dayjs());
  return date.isBefore(start, 'day') || disabledScheduleRangeDate(time);
}
</script>

<style scoped lang="scss">
:deep(.filter-form) {
  gap: 20px;
   .el-form-item {
     margin-right: 0;
     margin-bottom: 5px;
   }
}

.schedule-settings {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px 16px 20px 8px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;

  h2 {
    margin: 0;
    font-size: 22px;
    font-weight: 700;
    color: var(--el-text-color-primary);
  }

  p {
    margin: 6px 0 0;
    color: var(--el-text-color-secondary);
    font-size: 13px;
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.summary-item {
  min-height: 68px;
  padding: 12px 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;

  span {
    color: var(--el-text-color-secondary);
    font-size: 12px;
  }

  strong {
    color: var(--el-text-color-primary);
    font-size: 20px;
    line-height: 1.1;
  }

}

.calendar-panel {
  overflow: hidden;

  :deep(.el-card__body) {
    padding: 0;
  }
}

.calendar-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.calendar-title {
  font-weight: 700;
  color: var(--el-text-color-primary);
  margin-right: 10px;
}

.calendar-subtitle {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.calendar-actions {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  justify-content: flex-end;
  .el-segmented {
    --el-segmented-item-selected-color: var(--el-color-primary);
    --el-segmented-item-selected-bg-color: var(--el-color-primary-light-9);
    --el-border-radius-base: 6px;
    &__item {
      padding: 0 10px;
      font-weight: 500;
    }
  }
}

.qcalendar-shell {
  min-height: 540px;
  padding: 14px;
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
  --calendar-selected-color: var(--el-color-primary);
  --calendar-selected-background: var(--el-color-primary-light-9);
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  font-family: inherit;
}

:deep(.q-calendar__bordered) {
  border-color: var(--el-border-color-lighter);
}

:deep(.q-calendar__button) {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  color: inherit;
  font-size: 12px;
  font-weight: 700;
}

:deep(.q-calendar-month__head),
:deep(.q-calendar-agenda__head) {
  background: var(--el-fill-color-extra-light);
  color: var(--el-text-color-secondary);
}

:deep(.q-calendar-month__head--weekday),
:deep(.q-calendar-agenda__head--day) {
  min-height: 52px;
  justify-content: center;
}

:deep(.q-calendar-month__head--weekday .q-calendar__button),
:deep(.q-calendar-agenda__head--day .q-calendar__button) {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

:deep(.q-calendar-month__day),
:deep(.q-calendar-agenda__day) {
  transition: background-color 0.16s ease, box-shadow 0.16s ease;
}

:deep(.q-calendar-month__day:hover),
:deep(.q-calendar-agenda__day:hover) {
  background: var(--el-fill-color-extra-light);
}

:deep(.q-calendar-month__day.q-current-day),
:deep(.q-calendar-agenda__head--day.q-current-day) {
  background: linear-gradient(180deg, var(--el-color-primary-light-9), var(--el-bg-color));
}

:deep(.q-calendar-month__day.q-current-day .q-calendar__button),
:deep(.q-calendar-agenda__head--day.q-current-day .q-calendar__button) {
  color: var(--el-color-primary);
  background: var(--el-bg-color);
  box-shadow: inset 0 0 0 1px var(--el-color-primary-light-5);
}

:deep(.q-calendar-month__day.q-outside) {
  background: var(--el-fill-color-extra-light);
}

:deep(.q-calendar-month__day--label__wrapper) {
  min-height: 34px;
  padding: 4px 6px 0;
}

:deep(.q-calendar-month__head--weekday) {
  min-height: 46px;
  font-size: 14px;
}

:deep(.q-calendar-month__head--weekday .q-calendar__button) {
  width: 24px;
  height: 24px;
  min-width: 24px;
  min-height: 24px;
  line-height: 1;
  color: var(--el-text-color-regular);
  font-size: 14px;
}

:deep(.q-calendar-month__day.q-current-day .q-calendar__button) {
  color: var(--el-color-white);
  background: var(--el-color-primary);
  border: none;
  box-shadow: none;
}

:deep(.q-calendar-agenda__body) {
  background: var(--el-bg-color);
}

:deep(.q-calendar-agenda__day-interval) {
  background: var(--el-bg-color);
}

.agenda-head-day {
  width: 100%;
  min-height: 52px;
  border: 0;
  background: transparent;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  font: inherit;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  transition: background-color 0.16s ease, color 0.16s ease;

  &:hover {
    background: var(--el-fill-color-light);
    color: var(--el-color-primary);
  }

  &.is-today {
    color: var(--el-color-primary);
  }
}

.agenda-head-weekday {
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
}

.agenda-head-date {
  font-size: 13px;
  font-weight: 700;
  line-height: 1.2;
  color: var(--el-text-color-primary);
}

.agenda-head-day.is-today .agenda-head-date {
  min-width: 42px;
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.qcal-day-events,
.agenda-day {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.qcal-day-events {
  gap: 4px;
  height: 84px;
  overflow: hidden;
  padding: 0 6px 6px;
}

.qcal-event,
.agenda-event,
.qcal-more,
.agenda-empty {
  width: 100%;
  border: 0;
  text-align: left;
  cursor: pointer;
  font: inherit;
  transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease, background-color 0.16s ease;
}

.qcal-event,
.agenda-event {
  border: 1px solid var(--el-color-success-light-7);
  background: linear-gradient(180deg, var(--el-color-success-light-9), var(--el-bg-color));
  color: var(--el-text-color-primary);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);

  &.closed {
    border-color: var(--el-border-color);
    background: linear-gradient(180deg, var(--el-fill-color-lighter), var(--el-bg-color));
  }

  &.available {
    border-color: var(--el-color-success-light-7);
    background: linear-gradient(180deg, var(--el-color-success-light-9), var(--el-bg-color));
  }

  &.partially_booked {
    border-color: var(--el-color-warning-light-5);
    background: linear-gradient(180deg, var(--el-color-warning-light-8), var(--el-bg-color));
  }

  &.booked {
    border-color: var(--el-color-danger-light-7);
    background: linear-gradient(180deg, var(--el-color-danger-light-9), var(--el-bg-color));
  }

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
  }
}

.qcal-event {
  min-height: 24px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-bg-color);
  color: var(--el-text-color-regular);
  box-shadow: none;
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  overflow: hidden;
}

.qcal-event:hover {
  transform: translateY(-1px);
  border-color: var(--el-color-info-light-7);
  box-shadow: none;
}

.qcal-event.available {
  border-left: 3px solid var(--el-color-success);
  background: var(--el-color-success-light-9);
}

.qcal-event.partially_booked {
  border: 1px solid var(--el-border-color-lighter);
  border-left: 3px solid var(--el-color-warning-dark-2);
  background: var(--el-color-warning-light-8);
}

.qcal-event.booked {
  border: 1px solid var(--el-border-color-lighter);
  border-left: 3px solid var(--el-color-danger);
  background: var(--el-color-danger-light-9);
}

.qcal-event.closed {
  border: 1px solid var(--el-border-color-lighter);
  border-left: 3px solid var(--el-color-info);
  background: var(--el-fill-color-light);
  opacity: 0.72;
}

.qcal-event-dot {
  width: 4px;
  height: 4px;
  background: var(--el-color-success);
}

.qcal-event.closed .qcal-event-dot {
  background: var(--el-color-info);
}

.qcal-event.available .qcal-event-dot {
  background: var(--el-color-success);
}

.qcal-event.partially_booked .qcal-event-dot {
  background: var(--el-color-warning-dark-2);
}

.qcal-event.booked .qcal-event-dot {
  background: var(--el-color-danger);
}

.qcal-event-time {
  font-size: 10px;
  font-weight: 700;
  color: var(--el-text-color-secondary);
}

.qcal-event-status {
  min-width: 0;
  width: 100%;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 5px;
  overflow: hidden;
}

.qcal-event-dot,
.agenda-event-marker {
  flex-shrink: 0;
  border-radius: 999px;
}

.agenda-event-marker {
  width: 7px;
  height: 7px;
  background: var(--el-color-success);
}

.agenda-event.closed .agenda-event-marker {
  background: var(--el-color-info);
}

.agenda-event.available .agenda-event-marker {
  background: var(--el-color-success);
}

.agenda-event.partially_booked .agenda-event-marker {
  background: var(--el-color-warning-dark-2);
}

.agenda-event.booked .agenda-event-marker {
  background: var(--el-color-danger);
}

.qcal-event-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.qcal-more {
  min-height: 24px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  padding: 3px 6px;
  color: var(--el-color-primary);
  background: var(--el-bg-color);
  font-size: 12px;
  font-weight: 600;

  &:hover {
    border-color: var(--el-color-primary-light-5);
    background: var(--el-fill-color-extra-light);
  }
}

.agenda-day {
  min-height: 96px;
  padding: 10px;
  background: transparent;
}

.agenda-event {
  min-height: 60px;
  border-radius: 8px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 6px;
}

.agenda-event-time {
  width: 100%;
  font-weight: 700;
  color: var(--el-text-color-primary);
  font-size: 12px;
  line-height: 1.3;
}

.agenda-event-content {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;

  strong {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    line-height: 1.5;
  }

  small {
    color: var(--el-text-color-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.agenda-empty {
  min-height: 60px;
  border-radius: 8px;
  border: 1px dashed var(--el-border-color);
  background: transparent;
  color: var(--el-text-color-secondary);
  text-align: center;
  font-size: 13px;
  font-weight: 600;

  &:hover {
    border-color: var(--el-color-primary-light-5);
    background: var(--el-color-primary-light-9);
    color: var(--el-color-primary);
  }
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.daily-schedule {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.slot-row {
  border: 1px solid var(--el-border-color-lighter);
  border-left: 4px solid var(--el-color-success);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  justify-content: space-between;
  gap: 12px;

  &.booked {
    border-left-color: var(--el-color-danger);
  }

  &.partially_booked {
    border-left-color: var(--el-color-warning-dark-2);
    background: var(--el-color-warning-light-9);
  }

  &.available {
    border-left-color: var(--el-color-success);
    background: var(--el-color-success-light-9);
  }

  &.closed {
    border-left-color: var(--el-color-info);
    background: var(--el-fill-color-lighter);
  }
}

.slot-time {
  font-weight: 700;
}

.slot-meta {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.slot-notes {
  margin: 8px 0 0;
  color: var(--el-text-color-regular);
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}

.slot-actions {
  display: flex;
  flex-shrink: 0;
  align-items: flex-start;
  gap: 2px;
}

.time-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.time-picker {
  flex: 1 1 260px;
}

.count-unit {
  margin-left: 10px;
  color: var(--el-text-color-secondary);
}

.batch-alert {
  margin-bottom: 16px;
}

.form-hint-row,
.switch-row,
.notes-update {
  width: 100%;
  display: flex;
  gap: 12px;
}

.form-hint-row,
.switch-row {
  align-items: center;
  flex-wrap: wrap;
}

.notes-update {
  flex-direction: column;
}

.form-hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.w-full {
  width: 100%;
}

@media (max-width: 760px) {
  .schedule-settings {
    padding-right: 8px;
  }

  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .summary-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .date-range {
    width: 100%;
  }

  .calendar-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .qcalendar-shell {
    padding: 8px;
  }

  .agenda-event {
    flex-direction: column;
    gap: 4px;
  }

  .agenda-event-time {
    width: auto;
  }
}
</style>
