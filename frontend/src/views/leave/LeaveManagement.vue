<template>
  <div class="leave-management pl-2 pr-4">
    <section class="flex justify-between items-center px-1 mb-2">
      <h3 class="my-0">{{ $t('menu.leave_management') }}</h3>
      <el-button :loading="loading" size="small" round class="h-30px! px-3!" @click="fetchLeaveRecords">
        <template #icon>
          <div class="i-hugeicons:refresh" />
        </template>
        {{ $t('common.refresh') }}
      </el-button>
    </section>

    <el-card shadow="never" class="filter-card mb-14px">
      <el-form
        :inline="true"
        :model="queryParams"
        size="small"
        label-position="top"
        class="filter-form flex items-end"
        @submit.prevent="handleSearch"
      >
        <el-form-item :label="$t('common.status')">
          <el-select
            v-model="queryParams.leave_status"
            clearable
            :placeholder="$t('common.all')"
            class="w-150px"
            @clear="handleSearch"
            @change="handleSearch"
          >
            <el-option v-for="(label, value) in leaveStatusMap" :key="value" :label="label" :value="value" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" round class="h-30px!" @click="handleSearch">
            <template #icon>
              <div class="i-hugeicons:search-01" />
            </template>
            {{ $t('common.search') }}
          </el-button>
          <el-button round class="h-30px!" @click="resetQuery">
            <template #icon>
              <div class="i-hugeicons:arrow-reload-horizontal" />
            </template>
            {{ $t('common.btnReset') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table
        v-loading="loading"
        :data="leaveRecords"
        size="small"
        stripe
        class="w-full"
        :empty-text="$t('leaveManagement.noRecords')"
      >
        <el-table-column prop="leave_no" :label="$t('leaveManagement.leaveNo')" width="145" fixed="left" show-overflow-tooltip />

        <el-table-column :label="$t('leaveManagement.bookingNo')" width="145" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.booking_no || '-' }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('leaveManagement.applicant')" min-width="250" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="initiator-cell">
              <span>{{ row.initiator_name || '-' }}</span>
              <el-tag size="small" effect="plain" class="flex-shrink-0" :type="row.initiator_type === 'teacher' ? 'primary' : 'success'">
                {{ getInitiatorLabel(row.initiator_type) }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('leaveManagement.leaveDateTime')" width="165" align="center">
          <template #default="{ row }">
            <div>{{ row.leave_date || '-' }}</div>
            <div class="muted-text">{{ formatTime(row.start_time) }} ~ {{ formatTime(row.end_time) }}</div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('common.type')" min-width="130" align="center">
          <template #default="{ row }">
            <el-tag :type="row.leave_type === 'emergency' ? 'warning' : 'info'" size="small" effect="plain">
              {{ getLeaveTypeLabel(row.leave_type) }}
            </el-tag>
            <div v-if="row.deduct_lesson" class="muted-text mt-1">{{ $t('leaveManagement.deductLesson') }}</div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('common.status')" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.leave_status)" size="small" effect="plain">
              {{ getStatusLabel(row.leave_status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="$t('leaveManagement.reason')" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.reason || '-' }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('leaveManagement.rejectionReason')" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.rejection_reason || '-' }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('leaveManagement.approvalInfo')" min-width="175">
          <template #default="{ row }">
            <div>{{ row.approver_name || '-' }}</div>
            <div class="muted-text">{{ formatDateTime(row.approved_at) }}</div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('leaveManagement.appliedAt')" min-width="240" align="center">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('common.actions')" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <div v-if="row.leave_status === 'pending'" class="action-cell">
              <el-button
                v-if="hasPermission('bookings.edit')"
                link
                type="success"
                size="small"
                :loading="operatingId === row.id && operatingAction === 'approve'"
                @click="handleApprove(row)"
              >
                {{ $t('leaveManagement.approve') }}
              </el-button>
              <el-button
                v-if="hasPermission('bookings.edit')"
                link
                type="danger"
                size="small"
                :loading="operatingId === row.id && operatingAction === 'reject'"
                @click="openRejectDialog(row)"
              >
                {{ $t('leaveManagement.reject') }}
              </el-button>
              <el-button
                v-if="hasPermission('bookings.list')"
                link
                type="info"
                size="small"
                :loading="operatingId === row.id && operatingAction === 'cancel'"
                @click="handleCancel(row)"
              >
                {{ $t('leaveManagement.withdraw') }}
              </el-button>
            </div>
            <span v-else class="muted-text">-</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-footer">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.per_page"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="fetchLeaveRecords"
          @current-change="fetchLeaveRecords"
        />
      </div>
    </el-card>

    <el-dialog v-model="rejectDialogVisible" :title="$t('leaveManagement.rejectTitle')" width="460px" destroy-on-close @closed="resetRejectForm">
      <el-alert
        v-if="rejectTarget"
        :title="`${rejectTarget.leave_no}｜${rejectTarget.initiator_name || '-'}｜${rejectTarget.leave_date}`"
        type="warning"
        show-icon
        :closable="false"
        class="mb-4"
      />
      <el-form ref="rejectFormRef" :model="rejectForm" :rules="rejectRules" label-position="top">
        <el-form-item :label="$t('leaveManagement.rejectionReason')" prop="rejection_reason">
          <el-input
            v-model="rejectForm.rejection_reason"
            type="textarea"
            :rows="4"
            maxlength="300"
            show-word-limit
            :placeholder="$t('leaveManagement.rejectPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="rejectDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" round :loading="rejecting" @click="submitReject">{{ $t('leaveManagement.submitReject') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import type { FormInstance, FormRules } from 'element-plus';
import { ElMessage, ElMessageBox } from 'element-plus';
import dayjs from 'dayjs';
import {
  approveLeaveRecord,
  cancelLeaveRecord,
  getLeaveRecordList,
  rejectLeaveRecord,
  type LeaveInitiatorType,
  type LeaveRecordResponse,
  type LeaveStatus,
} from '@/api/leaveRecord';
import { assertApiSuccess } from '@/api/response';
import { usePermissionStore } from '@/stores/permission';
import { useApiError } from '@/composables/useApiError';

const permissionStore = usePermissionStore();
const hasPermission = (permission: string) => permissionStore.hasPermission(permission);
const { showApiError } = useApiError();
const { t } = useI18n();

type TagType = 'primary' | 'success' | 'warning' | 'info' | 'danger' | '';
type OperatingAction = 'approve' | 'reject' | 'cancel' | '';

const leaveStatusMap = computed<Record<LeaveStatus, string>>(() => ({
  pending: t('leaveManagement.status.pending'),
  approved: t('leaveManagement.status.approved'),
  rejected: t('leaveManagement.status.rejected'),
  cancelled: t('leaveManagement.status.cancelled'),
}));

const loading = ref(false);
const leaveRecords = ref<LeaveRecordResponse[]>([]);
const total = ref(0);
const operatingId = ref('');
const operatingAction = ref<OperatingAction>('');

const rejectDialogVisible = ref(false);
const rejecting = ref(false);
const rejectTarget = ref<LeaveRecordResponse | null>(null);
const rejectFormRef = ref<FormInstance>();
const rejectForm = reactive({ rejection_reason: '' });
const rejectRules: FormRules = {
  rejection_reason: [{ required: true, message: t('leaveManagement.rejectReasonRequired'), trigger: 'blur' }],
};

const queryParams = reactive({
  page: 1,
  per_page: 20,
  leave_status: '' as LeaveStatus | '',
});

function formatTime(value?: string | null) {
  return value ? value.slice(0, 5) : '-';
}

function formatDateTime(value?: string | null) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-';
}

function getInitiatorLabel(type: LeaveInitiatorType) {
  return type === 'teacher' ? t('leaveManagement.initiator.teacher') : t('leaveManagement.initiator.student');
}

function getLeaveTypeLabel(type?: string | null) {
  if (type === 'emergency') return t('leaveManagement.type.emergency');
  if (type === 'normal') return t('leaveManagement.type.normal');
  return '-';
}

function getStatusTagType(status: LeaveStatus): TagType {
  if (status === 'approved') return 'success';
  if (status === 'rejected') return 'danger';
  if (status === 'cancelled') return 'info';
  if (status === 'pending') return 'warning';
  return '';
}

function getStatusLabel(status: LeaveStatus) {
  return leaveStatusMap.value[status] || status;
}

async function fetchLeaveRecords() {
  loading.value = true;
  try {
    const res = assertApiSuccess(await getLeaveRecordList({
      page: queryParams.page,
      per_page: queryParams.per_page,
      leave_status: queryParams.leave_status || undefined,
    }), t('leaveManagement.loadFailed'));

    leaveRecords.value = res.data || [];
    total.value = res.total || 0;
  } catch (error) {
    showApiError(error, t('leaveManagement.loadFailed'));
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  queryParams.page = 1;
  fetchLeaveRecords();
}

function resetQuery() {
  queryParams.page = 1;
  queryParams.leave_status = '';
  fetchLeaveRecords();
}

async function handleApprove(row: LeaveRecordResponse) {
  try {
    await ElMessageBox.confirm(t('leaveManagement.approveConfirmMessage', { leaveNo: row.leave_no }), t('leaveManagement.approveTitle'), {
      confirmButtonText: t('leaveManagement.approve'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    });
  } catch {
    return;
  }

  operatingId.value = row.id;
  operatingAction.value = 'approve';
  try {
    const res = assertApiSuccess(await approveLeaveRecord(row.id), t('leaveManagement.approveFailed'));
    ElMessage.success(res.message || t('leaveManagement.approved'));
    fetchLeaveRecords();
  } catch (error) {
    showApiError(error, t('leaveManagement.approveFailed'));
  } finally {
    operatingId.value = '';
    operatingAction.value = '';
  }
}

function openRejectDialog(row: LeaveRecordResponse) {
  rejectTarget.value = row;
  rejectForm.rejection_reason = '';
  rejectDialogVisible.value = true;
}

function resetRejectForm() {
  rejectTarget.value = null;
  rejectForm.rejection_reason = '';
  rejectFormRef.value?.clearValidate();
}

async function submitReject() {
  if (!rejectFormRef.value || !rejectTarget.value) return;

  await rejectFormRef.value.validate(async (valid) => {
    if (!valid || !rejectTarget.value) return;

    rejecting.value = true;
    operatingId.value = rejectTarget.value.id;
    operatingAction.value = 'reject';
    try {
      const res = assertApiSuccess(await rejectLeaveRecord(rejectTarget.value.id, {
        rejection_reason: rejectForm.rejection_reason.trim(),
      }), t('leaveManagement.rejectFailed'));

      ElMessage.success(res.message || t('leaveManagement.rejected'));
      rejectDialogVisible.value = false;
      fetchLeaveRecords();
    } catch (error) {
      showApiError(error, t('leaveManagement.rejectFailed'));
    } finally {
      rejecting.value = false;
      operatingId.value = '';
      operatingAction.value = '';
    }
  });
}

async function handleCancel(row: LeaveRecordResponse) {
  try {
    await ElMessageBox.confirm(t('leaveManagement.withdrawConfirmMessage', { leaveNo: row.leave_no }), t('leaveManagement.withdrawTitle'), {
      confirmButtonText: t('leaveManagement.withdraw'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    });
  } catch {
    return;
  }

  operatingId.value = row.id;
  operatingAction.value = 'cancel';
  try {
    const res = assertApiSuccess(await cancelLeaveRecord(row.id), t('leaveManagement.withdrawFailed'));
    ElMessage.success(res.message || t('leaveManagement.withdrawn'));
    fetchLeaveRecords();
  } catch (error) {
    showApiError(error, t('leaveManagement.withdrawFailed'));
  } finally {
    operatingId.value = '';
    operatingAction.value = '';
  }
}

onMounted(() => {
  fetchLeaveRecords();
});
</script>

<style scoped lang="scss">
.leave-management {
  :deep(.filter-form) {
    gap: 20px;
    .el-form-item {
      margin-right: 0;
      margin-bottom: 5px;
    }
  }

  .initiator-cell {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    min-width: 0;

    span {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .muted-text {
    color: var(--el-text-color-secondary);
    font-size: 12px;
  }

  .action-cell {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    flex-wrap: wrap;
  }

  .pagination-footer {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
  }
}

@media (max-width: 760px) {
  .leave-management {
    .page-header {
      align-items: flex-start;
      flex-direction: column;
    }
  }
}
</style>
