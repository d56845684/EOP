<template>
  <div class="leave-management pl-2 pr-4">
    <section class="flex justify-between items-center px-1 mb-2">
      <h3 class="my-0">請假管理</h3>
      <el-button :loading="loading" size="small" round class="h-30px! px-3!" @click="fetchLeaveRecords">
        <template #icon>
          <div class="i-hugeicons:refresh" />
        </template>
        重新整理
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
        <el-form-item label="狀態">
          <el-select
            v-model="queryParams.leave_status"
            clearable
            placeholder="全部"
            class="w-150px"
            @clear="handleSearch"
            @change="handleSearch"
          >
            <el-option label="待審核" value="pending" />
            <el-option label="已核准" value="approved" />
            <el-option label="已駁回" value="rejected" />
            <el-option label="已撤回" value="cancelled" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" round class="h-30px!" @click="handleSearch">
            <template #icon>
              <div class="i-hugeicons:search-01" />
            </template>
            查詢
          </el-button>
          <el-button round class="h-30px!" @click="resetQuery">
            <template #icon>
              <div class="i-hugeicons:arrow-reload-horizontal" />
            </template>
            重置
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
        empty-text="尚無請假紀錄"
      >
        <el-table-column prop="leave_no" label="請假編號" width="145" fixed="left" show-overflow-tooltip />

        <el-table-column label="預約編號" width="145" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.booking_no || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="申請人" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="initiator-cell">
              <span>{{ row.initiator_name || '-' }}</span>
              <el-tag size="small" effect="plain" :type="row.initiator_type === 'teacher' ? 'primary' : 'success'">
                {{ getInitiatorLabel(row.initiator_type) }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="請假日期 / 時間" width="165" align="center">
          <template #default="{ row }">
            <div>{{ row.leave_date || '-' }}</div>
            <div class="muted-text">{{ formatTime(row.start_time) }} ~ {{ formatTime(row.end_time) }}</div>
          </template>
        </el-table-column>

        <el-table-column label="類型" width="105" align="center">
          <template #default="{ row }">
            <el-tag :type="row.leave_type === 'emergency' ? 'warning' : 'info'" size="small" effect="plain">
              {{ getLeaveTypeLabel(row.leave_type) }}
            </el-tag>
            <div v-if="row.deduct_lesson" class="muted-text mt-1">扣堂</div>
          </template>
        </el-table-column>

        <el-table-column label="狀態" width="95" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.leave_status)" size="small" effect="plain">
              {{ getStatusLabel(row.leave_status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="請假原因" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.reason || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="駁回原因" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.rejection_reason || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="審核資訊" width="175" align="center">
          <template #default="{ row }">
            <div>{{ row.approver_name || '-' }}</div>
            <div class="muted-text">{{ formatDateTime(row.approved_at) }}</div>
          </template>
        </el-table-column>

        <el-table-column label="申請時間" width="165" align="center">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <div v-if="row.leave_status === 'pending'" class="action-cell">
              <el-button
                link
                type="success"
                size="small"
                :loading="operatingId === row.id && operatingAction === 'approve'"
                @click="handleApprove(row)"
              >
                核准
              </el-button>
              <el-button
                link
                type="danger"
                size="small"
                :loading="operatingId === row.id && operatingAction === 'reject'"
                @click="openRejectDialog(row)"
              >
                駁回
              </el-button>
              <el-button
                link
                type="info"
                size="small"
                :loading="operatingId === row.id && operatingAction === 'cancel'"
                @click="handleCancel(row)"
              >
                撤回
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

    <el-dialog v-model="rejectDialogVisible" title="駁回請假" width="460px" destroy-on-close @closed="resetRejectForm">
      <el-alert
        v-if="rejectTarget"
        :title="`${rejectTarget.leave_no}｜${rejectTarget.initiator_name || '-'}｜${rejectTarget.leave_date}`"
        type="warning"
        show-icon
        :closable="false"
        class="mb-4"
      />
      <el-form ref="rejectFormRef" :model="rejectForm" :rules="rejectRules" label-position="top">
        <el-form-item label="駁回原因" prop="rejection_reason">
          <el-input
            v-model="rejectForm.rejection_reason"
            type="textarea"
            :rows="4"
            maxlength="300"
            show-word-limit
            placeholder="請輸入駁回原因"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="primary" round :loading="rejecting" @click="submitReject">送出駁回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
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
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';

type TagType = 'primary' | 'success' | 'warning' | 'info' | 'danger' | '';
type OperatingAction = 'approve' | 'reject' | 'cancel' | '';

const LEAVE_STATUS_MAP: Record<LeaveStatus, string> = {
  pending: '待審核',
  approved: '已核准',
  rejected: '已駁回',
  cancelled: '已撤回',
};

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
  rejection_reason: [{ required: true, message: '請輸入駁回原因', trigger: 'blur' }],
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
  return type === 'teacher' ? '老師' : '學生';
}

function getLeaveTypeLabel(type?: string | null) {
  if (type === 'emergency') return '緊急請假';
  if (type === 'normal') return '一般請假';
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
  return LEAVE_STATUS_MAP[status] || status;
}

async function fetchLeaveRecords() {
  loading.value = true;
  try {
    const res = assertApiSuccess(await getLeaveRecordList({
      page: queryParams.page,
      per_page: queryParams.per_page,
      leave_status: queryParams.leave_status || undefined,
    }), '載入請假紀錄失敗');

    leaveRecords.value = res.data || [];
    total.value = res.total || 0;
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '載入請假紀錄失敗'));
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
    await ElMessageBox.confirm(`確定要核准「${row.leave_no}」的請假申請嗎？`, '核准請假', {
      confirmButtonText: '核准',
      cancelButtonText: '取消',
      type: 'warning',
    });
  } catch {
    return;
  }

  operatingId.value = row.id;
  operatingAction.value = 'approve';
  try {
    const res = assertApiSuccess(await approveLeaveRecord(row.id), '核准請假失敗');
    ElMessage.success(res.message || '請假已核准');
    fetchLeaveRecords();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '核准請假失敗'));
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
      }), '駁回請假失敗');

      ElMessage.success(res.message || '請假已駁回');
      rejectDialogVisible.value = false;
      fetchLeaveRecords();
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, '駁回請假失敗'));
    } finally {
      rejecting.value = false;
      operatingId.value = '';
      operatingAction.value = '';
    }
  });
}

async function handleCancel(row: LeaveRecordResponse) {
  try {
    await ElMessageBox.confirm(`確定要撤回「${row.leave_no}」的請假申請嗎？`, '撤回請假', {
      confirmButtonText: '撤回',
      cancelButtonText: '取消',
      type: 'warning',
    });
  } catch {
    return;
  }

  operatingId.value = row.id;
  operatingAction.value = 'cancel';
  try {
    const res = assertApiSuccess(await cancelLeaveRecord(row.id), '撤回請假失敗');
    ElMessage.success(res.message || '請假已撤回');
    fetchLeaveRecords();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '撤回請假失敗'));
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
