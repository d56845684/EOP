<template>
  <div class="booking-history">
    <section class="page-header">
      <div>
        <h2>{{ $t('teacherRecords.title') }}</h2>
      </div>
      <el-button :loading="loading" size="small" round class="h-30px px-3" @click="fetchBookings">
        <template #icon><div class="i-hugeicons:refresh" /></template>
        {{ $t('teacherRecords.refresh') }}
      </el-button>
    </section>

    <el-card shadow="never" class="filter-panel">
      <el-form :inline="true" :model="filters" label-position="top" size="small" class="filter-form">
        <el-form-item :label="$t('teacherRecords.filterKeyword')">
          <el-input
            v-model="filters.search"
            clearable
            :placeholder="$t('teacherRecords.filterKeywordPlaceholder')"
            class="h-30px! w-220px!"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item :label="$t('common.dateRange')">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="~"
            :start-placeholder="$t('common.startDate')"
            :end-placeholder="$t('common.endDate')"
            class="h-30px! w-220px!"
            clearable
            @change="handleSearch"
          />
        </el-form-item>
        <el-form-item :label="$t('common.status')">
          <el-select 
            v-model="filters.status" 
            clearable 
            :placeholder="$t('common.all')"
            class="h-30px! w-132px!" 
            @change="handleSearch"
          >
            <el-option :label="$t('bookingShared.status.pending')" value="pending" />
            <el-option :label="$t('bookingShared.status.confirmed')" value="confirmed" />
            <el-option :label="$t('bookingShared.status.completed')" value="completed" />
            <el-option :label="$t('bookingShared.status.cancelled')" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item class="mr-4!">
          <el-checkbox v-model="filters.incompleteNotesOnly" class="h-30px!" @change="handleSearch">
            {{ $t('teacherRecords.filterIncompleteNotes') }}
          </el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" round class="h-30px! px-4!" @click="handleSearch">
            <template #icon><div class="i-hugeicons:search-01" /></template>
            {{ $t('common.search') }}
          </el-button>
          <el-button round class="h-30px! px-4!" @click="resetFilters">
            <template #icon><div class="i-hugeicons:arrow-reload-horizontal" /></template>
            {{ $t('common.btnReset') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table
        v-loading="loading"
        :data="displayBookings"
        stripe
        size="small"
        class="w-full"
        :empty-text="$t('teacherRecords.emptyText')"
      >
        <el-table-column prop="booking_no" :label="$t('teacherRecords.bookingNo')" width="145" />

        <el-table-column :label="$t('teacherRecords.colDateTime')" width="150" align="center">
          <template #default="{ row }">
            <div>{{ row.booking_date || '-' }}</div>
            <div class="muted-text">{{ formatTime(row.start_time) }} ~ {{ formatTime(row.end_time) }}</div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('teacherRecords.colStudent')" min-width="120">
          <template #default="{ row }">
            {{ formatTeacherHistoryStudent(row) }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('teacherRecords.colCourse')" min-width="150">
          <template #default="{ row }">
            {{ row.course_name || '-' }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('common.status')" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.booking_status)" size="small" effect="plain">
              {{ $t(`bookingShared.status.${row.booking_status}`) }}
            </el-tag>
            <el-tag v-if="row.has_pending_leave" class="mt-1" type="warning" size="small" effect="plain">
              {{ $t('teacherRecords.leavePending') }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="$t('teacherRecords.colType')" width="95" align="center">
          <template #default="{ row }">
            <el-tag :type="row.booking_type === 'trial' ? 'warning' : ''" size="small" effect="plain">
              {{ row.booking_type === 'trial' || row.booking_type === 'regular' ? $t(`bookingShared.type.${row.booking_type}`) : (row.booking_type || '-') }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="$t('bookingAdmin.zoomColumn')" min-width="160" align="center">
          <template #default="{ row }">
            <template v-if="['pending', 'confirmed', 'completed'].includes(row.booking_status)">
              <div v-if="!zoomInfoMap[row.id]" class="flex justify-center items-center min-h-12">
                <span class="text-gray-400">-</span>
              </div>
              <div v-else class="flex flex-col items-center gap-2 min-h-12 justify-center">
                <div class="flex flex-col items-center gap-1 translate-x-14px">
                  <div v-if="zoomInfoMap[row.id]?.join_url" class="w-full grid grid-cols-[1fr_24px] items-center gap-1">
                    <el-button
                      type="success"
                      size="small"
                      round
                      plain
                      class="text-xs h-20px! px-1.5!"
                      @click="openUrl(zoomInfoMap[row.id]?.join_url)"
                    >
                      <template #icon><div class="i-hugeicons:video-01" /></template>
                      {{ $t('bookingAdmin.joinMeeting') }}
                    </el-button>
                    <el-button
                      size="small"
                      round
                      link
                      class="text-xs h-20px! px-1! color-gray-400! hover:color-gray-500! ml-0!"
                      :title="$t('common.copy')"
                      @click="copyMeetingLink(zoomInfoMap[row.id]?.join_url)"
                    >
                      <div class="i-hugeicons:copy-01" />
                    </el-button>
                  </div>
                  <div
                    v-if="zoomInfoMap[row.id]?.passcode"
                    class="w-full grid grid-cols-[1fr_24px] items-center gap-1 text-11px leading-12px color-gray-400"
                  >
                    <span>{{ $t('bookingAdmin.passcode', { passcode: zoomInfoMap[row.id]?.passcode }) }}</span>
                    <el-button
                      size="small"
                      round
                      link
                      class="text-xs h-20px! px-1! color-gray-400! hover:color-gray-500! ml-0!"
                      @click="copyText(zoomInfoMap[row.id]?.passcode)"
                    >
                      <div class="i-hugeicons:copy-01" />
                    </el-button>
                  </div>
                </div>
                <el-button
                  v-if="zoomInfoMap[row.id]?.drive_view_link || zoomInfoMap[row.id]?.recording_url"
                  type="info"
                  size="small"
                  round
                  plain
                  class="text-xs h-20px! px-1.5!"
                  @click="openUrl(zoomInfoMap[row.id]?.drive_view_link || zoomInfoMap[row.id]?.recording_url)"
                >
                  <template #icon><div class="i-hugeicons:video-replay" /></template>
                  {{ $t('bookingAdmin.viewRecording') }}
                </el-button>
              </div>
            </template>
            <div v-else class="flex justify-center items-center min-h-12">
              <span class="text-gray-400">-</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('teacherRecords.colNotes')" width="120" fixed="right" align="center">
          <template #default="{ row }">
            <template v-if="row.booking_status === 'completed'">
              <div v-if="row.notes" class="note-preview">
                {{ row.notes }}
              </div>
              <el-button link type="primary" size="small" @click="openNoteDialog(row)">
                {{ row.notes ? $t('teacherRecords.editNote') : $t('teacherRecords.uploadNote') }}
              </el-button>
            </template>
            <span v-else class="muted-text">{{ $t('teacherRecords.noteAvailableAfterClass') }}</span>
          </template>
        </el-table-column>

        <el-table-column :label="$t('teacherRecords.colActions')" min-width="110" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-cell">
              <el-button
                v-if="canConfirmBooking(row)"
                link
                type="primary"
                size="small"
                :loading="confirmingBookingId === row.id"
                @click="confirmBooking(row)"
              >
                {{ $t('teacherRecords.btnConfirm') }}
              </el-button>
              <el-button
                v-if="canRequestLeave(row)"
                link
                type="danger"
                size="small"
                @click="openLeaveDialog(row)"
              >
                {{ $t('teacherRecords.btnLeave') }}
              </el-button>
              <span v-if="!canConfirmBooking(row) && !canRequestLeave(row)" class="muted-text">
                -
              </span>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-footer">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.per_page"
          :page-sizes="[10, 20, 50, 100]"
          size="small"
          layout="total, sizes, prev, pager, next, jumper"
          :total="paginationTotal"
          @size-change="fetchBookings"
          @current-change="fetchBookings"
        />
      </div>
    </el-card>

    <el-dialog v-model="leaveDialogVisible" :title="$t('teacherRecords.leaveDialogTitleTeacher')" width="500px" destroy-on-close @closed="resetLeaveForm">
      <el-alert
        v-if="leaveBooking"
        :title="`${leaveBooking.booking_date} ${formatTime(leaveBooking.start_time)} ~ ${formatTime(leaveBooking.end_time)}`"
        type="warning"
        :closable="false"
        show-icon
        class="mb-4"
      />
      <el-form ref="leaveFormRef" :model="leaveForm" :rules="leaveRules" label-position="top">
        <el-form-item :label="$t('teacherRecords.labelLeaveReason')" prop="reason">
          <el-input
            v-model="leaveForm.reason"
            type="textarea"
            :rows="4"
            maxlength="300"
            show-word-limit
            :placeholder="$t('teacherRecords.leaveReasonPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="leaveDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" round :loading="leaving" @click="submitLeave">{{ $t('teacherRecords.leaveSubmit') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="noteDialogVisible" :title="$t('teacherRecords.colNotes')" width="560px" destroy-on-close @closed="resetNoteForm">
      <el-alert
        v-if="noteBooking"
        :title="`${noteBooking.booking_date} ${formatTime(noteBooking.start_time)} ~ ${formatTime(noteBooking.end_time)}`"
        type="info"
        :closable="false"
        show-icon
        class="mb-4"
      />
      <el-form ref="noteFormRef" :model="noteForm" :rules="noteRules" label-position="top">
        <el-form-item :label="$t('teacherRecords.colNotes')" prop="notes">
          <el-input
            v-model="noteForm.notes"
            type="textarea"
            :rows="7"
            maxlength="1200"
            show-word-limit
            :placeholder="$t('teacherRecords.notePlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="noteDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" round :loading="savingNote" @click="submitNote">{{ $t('teacherRecords.saveNote') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { FormInstance, FormRules } from 'element-plus';
import { ElMessage, ElMessageBox } from 'element-plus';
import dayjs from 'dayjs';
import { useAuthStore } from '@/stores/auth';
import {
  getBookingList,
  updateBooking,
  type BookingItem,
  type BookingListParams,
  type BookingStatus,
} from '@/api/booking';
import { createLeaveRecord } from '@/api/leaveRecord';
import { batchGetZoomMeetings, type ZoomMeetingLogResponse } from '@/api/zoom';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { copyToClipboardUtil } from '@/utils/clipboard';

const authStore = useAuthStore();
const { t } = useI18n();

const currentTeacherId = computed(() => authStore.userInfo?.teacher_id || '');

const loading = ref(false);
const bookings = ref<BookingItem[]>([]);
const total = ref(0);
const zoomInfoMap = ref<Record<string, ZoomMeetingLogResponse>>({});

const queryParams = reactive({
  page: 1,
  per_page: 10,
});

const filters = reactive({
  search: '',
  dateRange: [] as string[],
  status: '' as BookingStatus | '',
  incompleteNotesOnly: false,
});

const confirmingBookingId = ref('');

const leaveDialogVisible = ref(false);
const leaving = ref(false);
const leaveBooking = ref<BookingItem | null>(null);
const leaveFormRef = ref<FormInstance>();
const leaveForm = reactive({ reason: '' });
const leaveRules: FormRules = {
  reason: [{ required: true, message: t('teacherRecords.leaveReasonRequired'), trigger: 'blur' }],
};

const noteDialogVisible = ref(false);
const savingNote = ref(false);
const noteBooking = ref<BookingItem | null>(null);
const noteFormRef = ref<FormInstance>();
const noteForm = reactive({ notes: '' });
const noteRules: FormRules = {
  notes: [{ required: true, message: t('teacherRecords.noteRequired'), trigger: 'blur' }],
};

const displayBookings = computed(() => {
  if (!filters.incompleteNotesOnly) return bookings.value;
  return bookings.value.filter((booking) => booking.booking_status === 'completed' && !booking.notes);
});
const paginationTotal = computed(() => (filters.incompleteNotesOnly ? displayBookings.value.length : total.value));

function formatTime(value?: string | null) {
  return value ? value.slice(0, 5) : '-';
}

function formatTeacherHistoryStudent(booking: BookingItem) {
  const studentNo = booking.student_no?.trim();
  const studentEngName = booking.student_eng_name?.trim();
  if (studentNo && studentEngName) return `${studentNo}-${studentEngName}`;
  return studentNo || studentEngName || booking.student_name || '-';
}

function getStatusType(status: BookingStatus) {
  if (status === 'completed') return 'success';
  if (status === 'cancelled') return 'info';
  if (status === 'confirmed') return 'primary';
  if (status === 'pending') return 'warning';
  return '';
}

function getBookingStart(booking: BookingItem) {
  return dayjs(`${booking.booking_date} ${formatTime(booking.start_time)}`);
}

function isUpcoming(booking: BookingItem) {
  return getBookingStart(booking).isAfter(dayjs());
}

function canRequestLeave(booking: BookingItem) {
  return booking.booking_status === 'confirmed'
    && isUpcoming(booking)
    && !booking.has_pending_leave
    && getBookingStart(booking).diff(dayjs(), 'minute') >= 30;
}

function canConfirmBooking(booking: BookingItem) {
  return booking.booking_status === 'pending' && !booking.has_pending_leave;
}

function buildListParams(): BookingListParams {
  const params: BookingListParams = {
    page: queryParams.page,
    per_page: queryParams.per_page,
    teacher_id: currentTeacherId.value,
    search: filters.search.trim() || undefined,
    booking_status: filters.status || undefined,
  };

  if (filters.dateRange.length === 2) {
    params.date_from = filters.dateRange[0];
    params.date_to = filters.dateRange[1];
  }

  return params;
}

async function fetchBookings() {
  if (!currentTeacherId.value) {
    bookings.value = [];
    total.value = 0;
    ElMessage.warning(t('teacherRecords.missingTeacher'));
    return;
  }

  loading.value = true;
  try {
    const res = assertApiSuccess(await getBookingList(buildListParams()), t('teacherRecords.loadFailed'));
    bookings.value = res.data || [];
    total.value = res.total || 0;
    await fetchZoomInfos();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('teacherRecords.loadFailed')));
  } finally {
    loading.value = false;
  }
}

async function fetchZoomInfos() {
  const ids = bookings.value
    .filter((booking) => ['pending', 'confirmed', 'completed'].includes(booking.booking_status))
    .filter((booking) => !zoomInfoMap.value[booking.id])
    .map((booking) => booking.id);

  if (ids.length === 0) return;

  try {
    const res = assertApiSuccess(await batchGetZoomMeetings(ids), t('teacherRecords.loadZoomFailed'));
    if (res.data) {
      zoomInfoMap.value = { ...zoomInfoMap.value, ...res.data };
    }
  } catch {
    // Zoom meeting may not exist yet; keep the booking list usable.
  }
}

function handleSearch() {
  queryParams.page = 1;
  fetchBookings();
}

function resetFilters() {
  filters.search = '';
  filters.dateRange = [];
  filters.status = '';
  filters.incompleteNotesOnly = false;
  handleSearch();
}

async function confirmBooking(booking: BookingItem) {
  if (!canConfirmBooking(booking)) return;

  try {
    await ElMessageBox.confirm(
      t('teacherRecords.confirmClassMessage', {
        date: booking.booking_date,
        time: `${formatTime(booking.start_time)} ~ ${formatTime(booking.end_time)}`,
      }),
      t('teacherRecords.confirmClassTitle'),
      {
        confirmButtonText: t('teacherRecords.confirmClassSubmit'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      },
    );
  } catch {
    return;
  }

  confirmingBookingId.value = booking.id;
  try {
    const res = assertApiSuccess(await updateBooking(booking.id, {
      booking_status: 'confirmed',
    }), t('teacherRecords.confirmClassFailed'));

    ElMessage.success(res.message || t('teacherRecords.confirmClassSuccess'));
    fetchBookings();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('teacherRecords.confirmClassFailed')));
  } finally {
    confirmingBookingId.value = '';
  }
}

function openLeaveDialog(booking: BookingItem) {
  if (!canRequestLeave(booking)) {
    ElMessage.warning(t('teacherRecords.leaveUnavailable'));
    return;
  }

  leaveBooking.value = booking;
  leaveForm.reason = '';
  leaveDialogVisible.value = true;
}

function resetLeaveForm() {
  leaveBooking.value = null;
  leaveForm.reason = '';
  leaveFormRef.value?.clearValidate();
}

async function submitLeave() {
  if (!leaveFormRef.value || !leaveBooking.value) return;

  await leaveFormRef.value.validate(async (valid) => {
    if (!valid || !leaveBooking.value) return;

    try {
      await ElMessageBox.confirm(t('teacherRecords.leaveConfirmMessage'), t('teacherRecords.leaveConfirmTitle'), {
        confirmButtonText: t('teacherRecords.leaveSubmit'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      });
    } catch {
      return;
    }

    leaving.value = true;
    try {
      const res = assertApiSuccess(await createLeaveRecord({
        booking_id: leaveBooking.value.id,
        reason: leaveForm.reason,
      }), t('teacherRecords.leaveFailed'));

      ElMessage.success(res.message || t('teacherRecords.leaveSubmitted'));
      leaveDialogVisible.value = false;
      fetchBookings();
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, t('teacherRecords.leaveFailed')));
    } finally {
      leaving.value = false;
    }
  });
}

function openNoteDialog(booking: BookingItem) {
  noteBooking.value = booking;
  noteForm.notes = booking.notes || '';
  noteDialogVisible.value = true;
}

function resetNoteForm() {
  noteBooking.value = null;
  noteForm.notes = '';
  noteFormRef.value?.clearValidate();
}

async function submitNote() {
  if (!noteFormRef.value || !noteBooking.value) return;

  await noteFormRef.value.validate(async (valid) => {
    if (!valid || !noteBooking.value) return;

    savingNote.value = true;
    try {
      const res = assertApiSuccess(await updateBooking(noteBooking.value.id, {
        booking_status: noteBooking.value.booking_status,
        notes: noteForm.notes,
      }), t('teacherRecords.saveFailed'));

      ElMessage.success(res.message || t('teacherRecords.saveSuccess'));
      noteDialogVisible.value = false;
      fetchBookings();
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, t('teacherRecords.saveFailed')));
    } finally {
      savingNote.value = false;
    }
  });
}

function openUrl(url?: string | null) {
  if (url) window.open(url, '_blank');
}

function copyText(text?: string | null) {
  if (text) copyToClipboardUtil(text, t('bookingAdmin.passcodeCopied'));
}

function copyMeetingLink(url?: string | null) {
  if (url) copyToClipboardUtil(url, t('bookingAdmin.joinLinkCopied'));
}

watch(
  currentTeacherId,
  (teacherId) => {
    if (!teacherId) return;
    fetchBookings();
  },
  { immediate: true },
);
</script>

<style scoped lang="scss">
.booking-history {
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
}

:deep(.filter-form) {
  gap: 20px;
   .el-form-item {
     margin-right: 0;
     margin-bottom: 5px;
   }
}

.muted-text {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.note-preview {
  max-width: 260px;
  color: var(--el-text-color-regular);
  font-size: 12px;
  line-height: 1.45;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  white-space: normal;
}

.action-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-wrap: wrap;
}

.pagination-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.w-full {
  width: 100%;
}

@media (max-width: 760px) {
  .booking-history {
    padding-right: 8px;
  }

  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .search-input,
  .date-range,
  .status-select {
    width: 100%;
  }
}
</style>
