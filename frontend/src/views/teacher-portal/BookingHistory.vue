<template>
  <div class="booking-history">
    <section class="page-header">
      <div>
        <h2>{{ $t('teacherRecords.title') }}</h2>
      </div>
      <el-button :loading="loading" size="small" round class="h-30px px-3" @click="fetchBookings">
        <template #icon><div class="i-hugeicons:refresh" /></template>
        重新整理
      </el-button>
    </section>

    <el-card shadow="never" class="filter-panel">
      <el-form :inline="true" :model="filters" label-position="top" size="small" class="filter-form">
        <el-form-item label="關鍵字">
          <el-input
            v-model="filters.search"
            clearable
            placeholder="預約編號、學生、課程"
            class="h-30px! w-220px!"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="日期範圍">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="~"
            start-placeholder="開始日期"
            end-placeholder="結束日期"
            class="h-30px! w-220px!"
            clearable
            @change="handleSearch"
          />
        </el-form-item>
        <el-form-item label="狀態">
          <el-select 
            v-model="filters.status" 
            clearable 
            placeholder="全部" 
            class="h-30px! w-132px!" 
            @change="handleSearch"
          >
            <el-option label="待確認" value="pending" />
            <el-option label="已確認" value="confirmed" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item class="mr-4!">
          <el-checkbox v-model="filters.incompleteNotesOnly" class="h-30px!" @change="handleSearch">
            未上傳課後筆記
          </el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" round class="h-30px! px-4!" @click="handleSearch">
            <template #icon><div class="i-hugeicons:search-01" /></template>
            查詢
          </el-button>
          <el-button round class="h-30px! px-4!" @click="resetFilters">
            <template #icon><div class="i-hugeicons:arrow-reload-horizontal" /></template>
            重置
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
        empty-text="尚無預約紀錄"
      >
        <el-table-column prop="booking_no" label="預約編號" width="145" fixed="left" />

        <el-table-column label="日期 / 時間" width="150" align="center">
          <template #default="{ row }">
            <div>{{ row.booking_date || '-' }}</div>
            <div class="muted-text">{{ formatTime(row.start_time) }} ~ {{ formatTime(row.end_time) }}</div>
          </template>
        </el-table-column>

        <el-table-column label="學生" min-width="120">
          <template #default="{ row }">
            {{ row.student_name || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="課程" min-width="150">
          <template #default="{ row }">
            {{ row.course_name || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="狀態" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.booking_status)" size="small" effect="plain">
              {{ BOOKING_STATUS_MAP[row.booking_status] || row.booking_status }}
            </el-tag>
            <el-tag v-if="row.has_pending_leave" class="mt-1" type="warning" size="small" effect="plain">
              請假審核中
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="類型" width="95" align="center">
          <template #default="{ row }">
            <el-tag :type="row.booking_type === 'trial' ? 'warning' : ''" size="small" effect="plain">
              {{ BOOKING_TYPE_MAP[row.booking_type] || row.booking_type || '-' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Zoom" width="140" align="center">
          <template #default="{ row }">
            <div v-if="isUpcoming(row) && zoomInfoMap[row.id]?.join_url" class="zoom-cell">
              <el-button
                type="success"
                size="small"
                round
                plain
                class="h-24px! px-2!"
                @click="openUrl(zoomInfoMap[row.id]?.join_url)"
              >
                <template #icon><div class="i-hugeicons:video-01" /></template>
                進入教室
              </el-button>
              <div v-if="zoomInfoMap[row.id]?.passcode" class="zoom-passcode">
                密碼 {{ zoomInfoMap[row.id]?.passcode }}
                <el-button link size="small" class="copy-btn" @click="copyText(zoomInfoMap[row.id]?.passcode)">
                  <div class="i-hugeicons:copy-01" />
                </el-button>
              </div>
            </div>
            <span v-else class="muted-text">-</span>
          </template>
        </el-table-column>

        <el-table-column label="課後筆記" width="220" fixed="right">
          <template #default="{ row }">
            <template v-if="row.booking_status === 'completed'">
              <div v-if="row.notes" class="note-preview">
                {{ row.notes }}
              </div>
              <el-button link type="primary" size="small" @click="openNoteDialog(row)">
                {{ row.notes ? '編輯課後筆記' : '上傳課後筆記' }}
              </el-button>
            </template>
            <span v-else class="muted-text">課後可填寫</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-cell">
              <el-button
                v-if="canEditBooking(row)"
                link
                type="primary"
                size="small"
                @click="openEditDialog(row)"
              >
                編輯
              </el-button>
              <el-button
                v-if="canRequestLeave(row)"
                link
                type="danger"
                size="small"
                @click="openLeaveDialog(row)"
              >
                請假
              </el-button>
              <span v-if="!canEditBooking(row) && !canRequestLeave(row)" class="muted-text">
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
          layout="total, sizes, prev, pager, next, jumper"
          :total="paginationTotal"
          @size-change="fetchBookings"
          @current-change="fetchBookings"
        />
      </div>
    </el-card>

    <el-dialog v-model="editDialogVisible" title="編輯預約" width="500px" destroy-on-close @closed="resetEditForm">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="96px">
        <el-form-item label="預約編號">
          <span>{{ editingBooking?.booking_no || '-' }}</span>
        </el-form-item>
        <el-form-item label="上課時間">
          <span>
            {{ editingBooking?.booking_date || '-' }}
            {{ formatTime(editingBooking?.start_time) }} ~ {{ formatTime(editingBooking?.end_time) }}
          </span>
        </el-form-item>
        <el-form-item label="狀態" prop="booking_status">
          <el-select v-model="editForm.booking_status" class="w-full">
            <el-option label="已確認" value="confirmed" />
          </el-select>
        </el-form-item>
        <el-form-item label="備註">
          <el-input v-model="editForm.notes" type="textarea" :rows="4" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" round :loading="editing" @click="submitEdit">儲存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="leaveDialogVisible" title="老師請假" width="500px" destroy-on-close @closed="resetLeaveForm">
      <el-alert
        v-if="leaveBooking"
        :title="`${leaveBooking.booking_date} ${formatTime(leaveBooking.start_time)} ~ ${formatTime(leaveBooking.end_time)}`"
        type="warning"
        :closable="false"
        show-icon
        class="mb-4"
      />
      <el-form ref="leaveFormRef" :model="leaveForm" :rules="leaveRules" label-position="top">
        <el-form-item label="請假原因" prop="reason">
          <el-input
            v-model="leaveForm.reason"
            type="textarea"
            :rows="4"
            maxlength="300"
            show-word-limit
            placeholder="請輸入請假原因"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="leaveDialogVisible = false">取消</el-button>
        <el-button type="primary" round :loading="leaving" @click="submitLeave">送出請假</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="noteDialogVisible" title="課後筆記" width="560px" destroy-on-close @closed="resetNoteForm">
      <el-alert
        v-if="noteBooking"
        :title="`${noteBooking.booking_date} ${formatTime(noteBooking.start_time)} ~ ${formatTime(noteBooking.end_time)}`"
        type="info"
        :closable="false"
        show-icon
        class="mb-4"
      />
      <el-form ref="noteFormRef" :model="noteForm" :rules="noteRules" label-position="top">
        <el-form-item label="課後筆記" prop="notes">
          <el-input
            v-model="noteForm.notes"
            type="textarea"
            :rows="7"
            maxlength="1200"
            show-word-limit
            placeholder="請輸入課後筆記、學生狀況或作業提醒"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="noteDialogVisible = false">取消</el-button>
        <el-button type="primary" round :loading="savingNote" @click="submitNote">儲存筆記</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
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
import { BOOKING_STATUS_MAP, BOOKING_TYPE_MAP } from '@/constants/booking';
import { copyToClipboardUtil } from '@/utils/clipboard';

const authStore = useAuthStore();

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

const editDialogVisible = ref(false);
const editing = ref(false);
const editingBooking = ref<BookingItem | null>(null);
const editFormRef = ref<FormInstance>();
const editForm = reactive({
  booking_status: 'confirmed' as BookingStatus,
  notes: '',
});
const editRules: FormRules = {
  booking_status: [{ required: true, message: '請選擇狀態', trigger: 'change' }],
};

const leaveDialogVisible = ref(false);
const leaving = ref(false);
const leaveBooking = ref<BookingItem | null>(null);
const leaveFormRef = ref<FormInstance>();
const leaveForm = reactive({ reason: '' });
const leaveRules: FormRules = {
  reason: [{ required: true, message: '請輸入請假原因', trigger: 'blur' }],
};

const noteDialogVisible = ref(false);
const savingNote = ref(false);
const noteBooking = ref<BookingItem | null>(null);
const noteFormRef = ref<FormInstance>();
const noteForm = reactive({ notes: '' });
const noteRules: FormRules = {
  notes: [{ required: true, message: '請輸入課後筆記', trigger: 'blur' }],
};

const displayBookings = computed(() => {
  if (!filters.incompleteNotesOnly) return bookings.value;
  return bookings.value.filter((booking) => booking.booking_status === 'completed' && !booking.notes);
});
const paginationTotal = computed(() => (filters.incompleteNotesOnly ? displayBookings.value.length : total.value));

function formatTime(value?: string | null) {
  return value ? value.slice(0, 5) : '-';
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
  return ['pending', 'confirmed'].includes(booking.booking_status)
    && isUpcoming(booking)
    && !booking.has_pending_leave
    && getBookingStart(booking).diff(dayjs(), 'minute') >= 30;
}

function canEditBooking(booking: BookingItem) {
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
    ElMessage.warning('目前登入帳號沒有教師資料，無法載入預約紀錄');
    return;
  }

  loading.value = true;
  try {
    const res = assertApiSuccess(await getBookingList(buildListParams()), '載入預約紀錄失敗');
    bookings.value = res.data || [];
    total.value = res.total || 0;
    await fetchZoomInfos();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '載入預約紀錄失敗'));
  } finally {
    loading.value = false;
  }
}

async function fetchZoomInfos() {
  const ids = bookings.value
    .filter((booking) => ['pending', 'confirmed'].includes(booking.booking_status))
    .filter((booking) => isUpcoming(booking))
    .filter((booking) => !zoomInfoMap.value[booking.id])
    .map((booking) => booking.id);

  if (ids.length === 0) return;

  try {
    const res = assertApiSuccess(await batchGetZoomMeetings(ids), '載入 Zoom 會議失敗');
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

function openEditDialog(booking: BookingItem) {
  editingBooking.value = booking;
  editForm.booking_status = 'confirmed';
  editForm.notes = booking.notes || '';
  editDialogVisible.value = true;
}

function resetEditForm() {
  editingBooking.value = null;
  editForm.booking_status = 'confirmed';
  editForm.notes = '';
  editFormRef.value?.clearValidate();
}

async function submitEdit() {
  if (!editFormRef.value || !editingBooking.value) return;

  await editFormRef.value.validate(async (valid) => {
    if (!valid || !editingBooking.value) return;

    editing.value = true;
    try {
      const res = assertApiSuccess(await updateBooking(editingBooking.value.id, {
        booking_status: editForm.booking_status,
        notes: editForm.notes || null,
      }), '更新預約失敗');

      ElMessage.success(res.message || '預約已更新');
      editDialogVisible.value = false;
      fetchBookings();
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, '更新預約失敗'));
    } finally {
      editing.value = false;
    }
  });
}

function openLeaveDialog(booking: BookingItem) {
  if (!canRequestLeave(booking)) {
    ElMessage.warning('此預約目前無法請假');
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
      await ElMessageBox.confirm('送出後將建立老師請假申請，確定繼續嗎？', '確認請假', {
        confirmButtonText: '送出請假',
        cancelButtonText: '取消',
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
      }), '送出請假失敗');

      ElMessage.success(res.message || '請假申請已送出');
      leaveDialogVisible.value = false;
      fetchBookings();
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, '送出請假失敗'));
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
        notes: noteForm.notes,
      }), '儲存課後筆記失敗');

      ElMessage.success(res.message || '課後筆記已儲存');
      noteDialogVisible.value = false;
      fetchBookings();
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, '儲存課後筆記失敗'));
    } finally {
      savingNote.value = false;
    }
  });
}

function openUrl(url?: string | null) {
  if (url) window.open(url, '_blank');
}

function copyText(text?: string | null) {
  if (text) copyToClipboardUtil(text, '已複製');
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

.zoom-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.zoom-passcode {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: var(--el-text-color-secondary);
  font-size: 11px;
}

.copy-btn {
  height: 18px !important;
  padding: 0 2px !important;
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
