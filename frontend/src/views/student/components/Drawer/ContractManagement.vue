<template>
  <div v-loading="contractLoading" class="pl-1 pr-2">
    <template v-if="activeContract || isCreatingContract">
      <!-- 當前合約 Current Contract -->
      <el-divider content-position="left" class="mt-1 mb-8">
        <span class="text-13px color-[#1d2d44]">{{ $t('myContracts.tabCurrent') }}</span>
      </el-divider>
      <el-row :gutter="60">
        <el-col :span="12">
          <div class="flex flex-col items-start mb-2">
            <label class="mb-2 flex-shrink-0 text-xs color-[#606266]">{{ $t('contract.contractNo') }}</label>
            <div class="w-full text-xs mt-1">{{ activeContract?.contract_no || '-' }}</div>
          </div>
        </el-col>
        <el-col v-if="activeContract" :span="12">
          <div class="flex flex-col items-start mb-2">
            <label class="mb-2 flex-shrink-0 text-xs color-[#606266]">{{ $t('studentAdmin.contractFileStatus') }}</label>
            <div class="w-full text-12px flex flex-col items-start gap-2" :class="activeContract?.contract_file_uploaded_at ? 'text-green' : 'text-red'">
              <div class="flex items-center gap-2">
                <div class="flex items-center gap-1">
                  <div :class="activeContract?.contract_file_uploaded_at ? 'i-hugeicons:checkmark-circle-03' : 'i-hugeicons:alert-02'" />
                  <span>{{ activeContract?.contract_file_uploaded_at ? $t('teacherContractDrawer.uploaded') : $t('teacherContractDrawer.notUploaded') }}</span>
                </div>
                <el-button
                  v-if="activeContract?.contract_file_uploaded_at"
                  type="primary"
                  link
                  size="small"
                  :loading="viewingContract"
                  @click="viewContractFile"
                >
                  <template #icon>
                    <div class="i-hugeicons:file-view" />
                  </template>
                  {{ $t('common.view') }}
                </el-button>
                <el-upload
                  ref="uploadRef"
                  v-model:file-list="contractFileList"
                  class="upload-file flex flex-col items-start"
                  action="#"
                  :limit="1"
                  :multiple="false"
                  accept=".pdf"
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="(uploadFile: UploadFile) => uploadStudentContract(uploadFile, 'contract')"
                >
                  <el-button
                    color="#626aef"
                    plain
                    round
                    size="small"
                    :loading="savingContract"
                  >
                    <template #icon>
                      <div class="i-hugeicons:file-upload" />
                    </template>
                    {{ activeContract?.contract_file_uploaded_at ? $t('teacherContractDrawer.updateContractFile') : $t('teacherContractDrawer.uploadContractFile') }}
                  </el-button>
                </el-upload>
              </div>
              <div
                v-if="activeContract?.contract_file_uploaded_at"
                class="text-11px color-gray-400 mt-2"
              >
                {{ $t('teacherContractDrawer.updatedAt') }}：{{ dayjs(activeContract?.contract_file_uploaded_at).format('YYYY-MM-DD HH:mm:ss') }}
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
      <!-- Main Contract Form -->
      <el-form :model="contractForm" size="small" label-position="top" class="constract-form mt-4">
        <el-row :gutter="60">
          <el-col :span="12">
            <el-form-item :label="$t('contract.contractStatus')">
              <el-select v-model="contractForm.contract_status" class="w-150px contract-select" :disabled="isCreatingContract">
                <el-option :label="$t('display.contractStatus.pending')" value="pending"></el-option>
                <el-option :label="$t('display.contractStatus.active')" value="active"></el-option>
                <el-option :label="$t('display.contractStatus.suspended')" value="suspended"></el-option>
                <el-option :label="$t('display.contractStatus.expired')" value="expired"></el-option>
                <el-option :label="$t('display.contractStatus.terminated')" value="terminated"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('studentAdmin.recurringStudent')">
              <el-switch
                v-model="contractForm.is_recurring"
                size="large"
                inline-prompt
                :active-text="$t('common.yes')"
                :inactive-text="$t('common.no')"
                style="--el-switch-off-color: #a7a8bd"
                class="translate-y-[-4px]"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('myContracts.colPeriod')">
              <el-date-picker
                v-model="contractForm.dateRange"
                type="daterange"
                value-format="YYYY-MM-DD"
                :range-separator="$t('studentAdmin.to')"
                class="w-full h-30px!"
                :readonly="!contractCanEdit"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('contract.contractTotalLessons')">
              <el-input-number
                v-model="contractForm.total_lessons"
                :min="1"
                :value-on-clear="null"
                :readonly="!contractCanEdit"
                class="w-150px h-30px"
              />
            </el-form-item>
          </el-col>
          <el-col v-if="activeContract" :span="12">
            <el-form-item :label="$t('myContracts.remainingLessons')">
              <span class="block w-130px h-30px line-height-30px px-2 bg-gray-100 rounded">
                {{ activeContract?.remaining_lessons }}
              </span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('contract.contractTotalAmount')">
              <el-input-number
                v-model="contractForm.total_amount"
                :min="0"
                :value-on-clear="null"
                :readonly="!contractCanEdit"
                class="w-150px h-30px!"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('studentAdmin.totalLeaveAllowed')">
              <el-input-number
                v-model="contractForm.total_leave_allowed"
                :min="0"
                :value-on-clear="null"
                :readonly="!contractCanEdit"
                class="w-150px h-30px!"
              />
            </el-form-item>
          </el-col>
          <el-col v-if="activeContract" :span="12">
            <el-form-item :label="$t('myContracts.usedLeaveCount')">
              <span class="block w-130px h-30px line-height-30px px-2 bg-gray-100 rounded">
                {{ activeContract?.used_leave_count }}
              </span>
            </el-form-item>
          </el-col>
          <el-col v-if="activeContract" :span="12">
            <el-form-item :label="$t('myContracts.emergencyLeaveQuota')">
              <span class="block w-130px h-30px line-height-30px px-2 bg-gray-100 rounded">
                {{ activeContract?.used_leave_count }}
              </span>
              <!-- <el-input-number
                v-model="contractForm.emergency_leave_quota"
                :min="0"
                :value-on-clear="null"
                class="w-150px h-30px!"
              /> -->
            </el-form-item>
          </el-col>
          <el-col v-if="activeContract" :span="12">
            <el-form-item :label="$t('myContracts.usedEmergencyLeaveCount')">
              <span class="block w-130px h-30px line-height-30px px-2 bg-gray-100 rounded">
                {{ activeContract?.used_emergency_leave_count || 0 }}
              </span>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item :label="$t('common.note')">
              <el-input
                type="textarea"
                v-model="contractForm.notes"
                :rows="3"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-button type="primary" round size="small" class="py-3!" :loading="savingContract" :disabled="!isContractFormDirty" @click="saveContractData">
              <template #icon>
                <div class="i-hugeicons:floppy-disk text-lg" />
              </template>
              {{ $t('common.save') }}
            </el-button>
          </el-col>
          <el-col v-if="activeContract" :span="12" justify="end">
            <el-form-item class="w-full action-column">
              <el-space :size="10" :spacer="h(ElDivider, { direction: 'vertical' })">
                <el-button
                  color="#626aef"
                  plain
                  round
                  size="small"
                  class="py-3!"
                  :loading="savingContract"
                  @click="downloadContractData"
                >
                  <template #icon>
                    <div class="i-hugeicons:file-download" />
                  </template>
                  {{ $t('studentAdmin.generateContractFile') }}
                </el-button>
                <el-button
                  v-if="!activeContract?.addendums.length"
                  color="#f07167"
                  plain
                  round
                  size="small"
                  :loading="savingContract"
                  @click="extendContract('create')"
                >
                  <template #icon>
                    <div class="i-hugeicons:file-add" />
                  </template>
                  {{ $t('studentAdmin.addendum.title') }}
                </el-button>
              </el-space>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <!-- 附約 Addendum  -->
      <template v-if="activeContract && (activeContract?.addendums.length || 0) > 0">
        <el-divider content-position="left" class="mt-5 mb-5">
          <span class="text-13px color-[#1d2d44]">{{ $t('studentAdmin.addendum.title') }}</span>
        </el-divider>
        <el-table :data="activeContract?.addendums" border :preserve-expanded-content="false" size="small" class="mb-8">
          <el-table-column type="expand" width="50">
            <template #default="props">
              <el-row class="px-4">
                <el-col :span="24" class="my-1">
                  <label class="text-12px color-gray-400 font-500 mr-4">{{ $t('common.note') }}</label>
                  <span class="text-12px">{{ props.row.notes || '-' }}</span>
                </el-col>
                <el-col :span="24" class="my-1">
                  <label class="text-12px color-gray-400 font-500 mr-4">{{ $t('studentAdmin.addendum.file') }}</label>
                  <span class="text-12px">{{ props.row.file_name || '-' }}</span>
                </el-col>
                <el-col :span="24" class="my-1">
                  <label class="text-12px color-gray-400 font-500 mr-4">{{ $t('studentAdmin.uploadedAt') }}</label>
                  <span class="text-12px">{{ props.row.file_uploaded_at ? formatDateTime(props.row.file_uploaded_at) : '-' }}</span>
                </el-col>
                <el-col :span="24" class="my-1">
                  <label class="text-12px color-gray-400 font-500 mr-4">{{ $t('studentAdmin.createdAt') }}</label>
                  <span class="text-12px">{{ props.row.created_at ? formatDateTime(props.row.created_at) : '-' }}</span>
                </el-col>
                <el-col :span="24" class="my-1">
                  <label class="text-12px color-gray-400 font-500 mr-4">{{ $t('studentAdmin.updatedAt') }}</label>
                  <span class="text-12px">{{ props.row.updated_at ? formatDateTime(props.row.updated_at) : '-' }}</span>
                </el-col>
              </el-row>
            </template>
          </el-table-column>
          <el-table-column prop="addendum_no" :label="$t('myContracts.addendumNo')" width="180" />
          <el-table-column prop="addendum_status" :label="$t('studentAdmin.addendum.status')" width="80">
            <template #default="scope">
              {{ formatStudentContractStatusLabel(scope.row.addendum_status, scope.row.addendum_status, t) }}
            </template>
          </el-table-column>
          <el-table-column prop="new_end_date" :label="$t('studentAdmin.addendum.newEndDate')" width="120" />
          
          <el-table-column :label="$t('common.actions')" min-width="80" align="center">
              <template #default="{row}">
                <el-row>
                  <el-col :span="8">
                    <el-tooltip :content="$t('common.edit')" effect="customized">
                      <el-button type="primary" round link @click="extendContract('update', row)">
                        <div class="i-hugeicons:edit-02" />
                      </el-button>
                    </el-tooltip>
                  </el-col>
                  <el-col :span="8">
                    <el-tooltip :content="$t('studentAdmin.addendum.uploadFile')" effect="customized">
                      <el-upload
                        ref="uploadAddendumRef"
                        v-model:file-list="addendumFileList"
                        class="upload-file py-2px"
                        action="#"
                        :limit="1"
                        :multiple="false"
                        accept=".pdf"
                        :auto-upload="false"
                        :show-file-list="false"
                        :on-change="(uploadFile: UploadFile) => uploadStudentContract(uploadFile, 'addendum')"
                      >
                        <el-button type="primary" round link>
                          <div class="i-hugeicons:upload-01" />
                        </el-button>
                      </el-upload>
                    </el-tooltip>
                  </el-col>
                  <el-col :span="8">
                    <el-tooltip :content="$t('common.delete')" effect="customized">
                      <el-button type="danger" round link @click="deleteAddendum()">
                        <div class="i-hugeicons:delete-02" />
                      </el-button>
                    </el-tooltip>
                  </el-col>
                </el-row>
              </template>
          </el-table-column>
        </el-table>
      </template>

      <!-- 合約明細 Contract Details -->
      <el-divider v-if="activeContract" content-position="left" class="mt-5 mb-3">
        <span class="text-13px color-[#1d2d44]">{{ $t('contract.contractDetails') }}</span>
      </el-divider>
      <el-button v-if="activeContract" type="primary" round text size="small" class="float-right mb-2" @click="openAddDetailDialog">
        <template #icon><div class="i-hugeicons:add-square" /></template>
        {{ $t('studentAdmin.addDetail') }}
      </el-button>
      <el-table v-if="activeContract" :data="contractDetails" size="small" class="mt-2 w-full" border>
        <el-table-column prop="detail_type" :label="$t('common.type')" width="100">
          <template #default="{ row }">
            {{ getDetailTypeLabel(row.detail_type) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="amount"
          :label="$t('myContracts.detailAmount')"
          width="120"
          :formatter="(
            row: { detail_type: string; amount: string; }) => 
              row.detail_type !== 'compensation' ? 
                'NT$ ' + row.amount : 
                row.amount + ' ' + $t('studentAdmin.lessonsUnit')
          "
        />
        <el-table-column :label="$t('studentAdmin.description')">
          <template #default="{ row }">
            {{ row.detail_type === 'lesson_price' ? (row.course_name || '-') : (row.description || '-') }}
          </template>
        </el-table-column>
        <el-table-column prop="notes" :label="$t('common.note')" />
        <el-table-column :label="$t('common.actions')" width="80" align="center" fixed="right">
          <template #default="{ row }">
            <el-tooltip :content="$t('common.edit')" effect="customized">
              <el-button type="primary" round link @click="handleEditContractDetail(row)">
                <div class="i-hugeicons:edit-02" />
              </el-button>
            </el-tooltip>
            <el-tooltip :content="$t('common.delete')" effect="customized">
              <el-button type="danger" round link @click="handleDeleteContractDetail(row.id)">
                <div class="i-hugeicons:delete-02" />
              </el-button>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <!-- 請假紀錄 Leave Records -->
      <el-divider v-if="activeContract" content-position="left" class="mt-10 mb-5">
        <span class="text-13px color-[#1d2d44]">{{ $t('studentAdmin.leaveRecords') }}</span>
      </el-divider>
      <el-button v-if="activeContract" type="primary" round text size="small" class="float-right mb-2" @click="addLeaveDialogVisible = true">
        <template #icon><div class="i-hugeicons:add-square" /></template>
        {{ $t('studentAdmin.addLeaveDialog.title') }}
      </el-button>
      <el-table v-if="activeContract" :data="leaveRecords" border size="small" :empty-text="$t('studentAdmin.noLeaveRecords')">
        <el-table-column prop="leave_date" :label="$t('studentAdmin.leaveDate')" width="120" />
        <el-table-column prop="reason" :label="$t('studentAdmin.reason')" />
        <el-table-column :label="$t('common.actions')" width="80" align="center">
            <template #default="{ row }">
              <el-tooltip :content="$t('common.delete')" effect="customized">
                <el-button type="danger" round link @click="deleteLeave(row.id)">
                  <div class="i-hugeicons:delete-02" />
                </el-button>
              </el-tooltip>
            </template>
        </el-table-column>
      </el-table>
    </template>
    <template v-else>
      <div class="flex items-center justify-center min-h-80px">
        <el-button type="primary" round @click="openAddContractDialog">
          <template #icon><div class="i-hugeicons:add-square" /></template>
          {{ $t('contract.addContract') }}
        </el-button>
      </div>
    </template>

    <!-- 歷史合約 History Contracts -->
    <el-divider content-position="left" class="mt-10 mb-5">
      <span class="text-13px color-[#1d2d44]">{{ $t('myContracts.tabHistory') }}</span>
    </el-divider>
    <el-table :data="contractHistory" border size="small" :empty-text="$t('studentAdmin.noHistoryContracts')">
      <el-table-column prop="contract_no" :label="$t('contract.contractNo')" width="180" />
      <el-table-column :label="$t('myContracts.colPeriod')" min-width="200">
        <template #default="{ row }">
          {{ row.start_date }} ~ {{ row.end_date }}
        </template>
      </el-table-column>
      <el-table-column prop="contract_status" :label="$t('contract.contractStatus')" width="100" align="center">
        <template #default="{ row }">
          {{ formatStudentContractStatusLabel(row.contract_status, row.contract_status, t) }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('common.view')" width="60" align="center">
        <template #default="{ row }">
          <el-tooltip :content="$t('common.view')" effect="customized">
            <el-button type="primary" round link @click="handleViewContract(row)">
              <div class="i-hugeicons:property-view" />
            </el-button>
          </el-tooltip>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- Contract Detail Dialog -->
    <ContractDetailsDialog
      v-model:detailVisible="detailVisible"
      :studentId="activeContract?.student_id || ''"
      :contractId="activeContract?.id || ''"
      :detailData="contractDetailData"
      @addDetailFinish="handleUpdateContractDetails"
    />

    <AddLeaveDialog 
      v-model:addLeaveDialogVisible="addLeaveDialogVisible"
      :contractId="activeContract?.id || ''"
      @addLeaveFinish="handleUpdateContractDetails"
    />

    <ContractDialog
      v-model:contractDialogVisible="contractDialogVisible"
      :contract="currentContract"
    />

    <ExtendDialog
      v-model:extendDialogVisible="extendDialogVisible"
      :contract="activeContract"
      :addendum="activeAddendum"
      :type="extendType"
      @handleAddendum="handleAddendum"
    />
  </div>
</template>

<script setup lang="ts">
import { h, ref, watch, computed } from 'vue';
import { dayjs, ElDivider, ElMessage, ElMessageBox, type UploadFile, type UploadInstance } from 'element-plus'
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import ContractDetailsDialog from '../Dialog/ContractDetailsDialog.vue';
import AddLeaveDialog from '../Dialog/AddLeaveDialog.vue';
import ContractDialog from '../Dialog/ContractDialog.vue';
import ExtendDialog from '../Dialog/ExtendDialog.vue';
import { 
  deleteContractDetail,
  deleteContractLeaveRecord,
  getContractDownloadUrl,
  generateContract,
  createAddendum,
  updateAddendum,
  type StudentContract,
  type StudentContractDetail ,
  type StudentContractAddendum,
  type StudentContractAddendumUpdate
} from '@/api/studentContract';
import { CONTRACT_STATUS, ENDED_STUDENT_CONTRACT_STATUSES } from '@/constants/contract';
import { triggerDownload, getFileNameFromResponse}  from '@/utils/download';
import { formatStudentContractStatusLabel } from '@/utils/i18n-formatters';
import { uploadContractFile } from '@/utils/upload';
import { createFormSnapshot } from '@/utils/formDirty';
import { useI18n } from 'vue-i18n';

type ContractForm = {
  contract_status: StudentContract['contract_status'];
  is_recurring: boolean;
  dateRange: string[];
  total_lessons: number | null;
  total_amount: number | null;
  total_leave_allowed: number | null;
  emergency_leave_quota: number | null;
  notes: string;
}

const props = defineProps({
  contracts: {
    type: Array as () => StudentContract[],
    required: true
  },
  contractLoading: {
    type: Boolean,
    required: true
  },
  hasActive: {
    type: Boolean,
    required: true
  },
  leaveRecords: {
    type: Array,
    required: true
  },
  contractDetails: {
    type: Array,
    required: true
  }
})

const { t } = useI18n();

const createEmptyContractForm = (): ContractForm => ({
  contract_status: 'pending',
  is_recurring: false,
  dateRange: [],
  total_lessons: null,
  total_amount: null,
  total_leave_allowed: null,
  emergency_leave_quota: null,
  notes: ''
});

const contractForm = ref<ContractForm>(createEmptyContractForm())
const contractFormSnapshot = ref('');
const getContractFormSnapshot = () => createFormSnapshot(contractForm.value);
const resetContractFormSnapshot = () => {
  contractFormSnapshot.value = getContractFormSnapshot();
};
const isContractFormDirty = computed(() => getContractFormSnapshot() !== contractFormSnapshot.value);
const fillContractForm = (contract: StudentContract) => {
  contractForm.value = {
    contract_status: contract.contract_status,
    is_recurring: contract.is_recurring,
    dateRange: [contract.start_date, contract.end_date],
    total_lessons: contract.total_lessons,
    total_amount: contract.total_amount,
    total_leave_allowed: contract.total_leave_allowed,
    emergency_leave_quota: contract.emergency_leave_quota ?? null,
    notes: contract.notes || ''
  }
  resetContractFormSnapshot();
  if (contract.addendums && contract.addendums.length > 0) {
    activeAddendum.value = contract.addendums[contract.addendums.length - 1] || null;
  }
};

const detailVisible = ref(false);
const addLeaveDialogVisible = ref(false)
const contractDialogVisible = ref(false)
const extendDialogVisible = ref(false)
const savingContract = ref(false)
const viewingContract = ref(false)
const contractDetailData = ref<StudentContractDetail | null>(null);
const currentContract = ref<StudentContract | null>(null);
const extendType = ref<'create' | 'update'>('create');
const activeAddendum = ref<StudentContractAddendum | null>(null);
const isCreatingContract = ref(false);

const addendumFileList = ref([]);
const contractFileList = ref([]);

const contractCanEdit = computed(() => {
  return isCreatingContract.value || activeContract.value?.contract_status === CONTRACT_STATUS.PENDING;
})

const endedContractStatusSet = new Set<string>(ENDED_STUDENT_CONTRACT_STATUSES);

const isEndedContract = (contract: StudentContract) => {
  return endedContractStatusSet.has(contract.contract_status.toLowerCase());
}

const getContractTimestamp = (contract: StudentContract) => {
  const dateValue = contract.updated_at || contract.created_at || contract.start_date || contract.end_date;
  const timestamp = dayjs(dateValue).valueOf();
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

const sortedContracts = computed(() => {
  return [...props.contracts].sort((a, b) => getContractTimestamp(b) - getContractTimestamp(a));
})

const activeContract = computed(() => {
  return sortedContracts.value.find((contract) => !isEndedContract(contract)) || null;
})

const contractHistory = computed(() => {
  return sortedContracts.value.filter(isEndedContract);
})

const emit = defineEmits([
  'saveContractData',
  'updateContent',
  'updateContractDetails'
])

const openAddContractDialog = () => {
  isCreatingContract.value = true;
  activeAddendum.value = null;
  contractForm.value = createEmptyContractForm();
  resetContractFormSnapshot();
}

defineExpose({
  openAddContractDialog,
});

const openAddDetailDialog = () => {
  detailVisible.value = true;
}

const saveContractData = () => {
  // TODO: Save contract data
  emit('saveContractData', contractForm.value, isCreatingContract.value)
  resetContractFormSnapshot();
}

const handleUpdateContractDetails = () => {
  // TODO: Update contract details
  emit('updateContractDetails', activeContract.value?.id)
}

const handleAddendum = async ({data, addendumId}: {data: StudentContractAddendumUpdate, addendumId?: string}) => {
  // TODO: Update addendum
  if (!activeContract.value) return;
  const actionLabel = extendType.value === 'create' ? t('common.add') : t('common.update');
  try {
    const res = extendType.value === 'create' ? await createAddendum(activeContract.value.id, data) : await updateAddendum(activeContract.value.id, addendumId!, data)
    assertApiSuccess(res, t('studentAdmin.addendum.saveFailed', { action: actionLabel }));
    ElMessage.success(res.message || t('studentAdmin.addendum.saveSuccess', { action: actionLabel }));
    extendDialogVisible.value = false;
    emit('updateContent', 'contract')
  } catch(err) {
    ElMessage.error(getApiErrorMessage(err, t('studentAdmin.addendum.saveFailed', { action: actionLabel })));
  }
}

const handleEditContractDetail = (detail: StudentContractDetail) => {
  // TODO: Edit contract details
  contractDetailData.value = detail;
  detailVisible.value = true;
}

const downloadContractData = async () => {
  if (!activeContract.value) return;
  try {
    const res = await generateContract(activeContract.value.id);
    const blob = new Blob([res.data], { 
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
    });
    const fileName = getFileNameFromResponse(res);
    triggerDownload(blob, fileName);
  } catch(err) {
    console.log(err)
    ElMessage.error(t('myContracts.downloadFailed'));
  }
}

const viewContractFile = async () => {
  if (!activeContract.value) return;
  viewingContract.value = true;
  try {
    const res = assertApiSuccess(await getContractDownloadUrl(activeContract.value.id), t('myContracts.downloadFailed'));
    if (res.download_url) {
      window.open(res.download_url, '_blank');
    } else {
      ElMessage.warning(t('myContracts.noDownloadUrl'));
    }
  } catch (err) {
    ElMessage.error(getApiErrorMessage(err, t('myContracts.downloadFailed')));
  } finally {
    viewingContract.value = false;
  }
}

const extendContract = (type: 'create' | 'update', row?: StudentContractAddendum) => {
  // TODO: Extend contract
  extendType.value = type;
  if (type === 'update' && row) {
    activeAddendum.value = row;
  }
  extendDialogVisible.value = true;
}

const deleteAddendum = () => {
  // TODO: Delete addendum
}

const uploadRef = ref<UploadInstance | null>(null);
const uploadAddendumRef = ref<UploadInstance | null>(null);
const uploadStudentContract = async (uploadFile: UploadFile, type: 'contract' | 'addendum' | null) => {
  if (!activeContract.value || (type === 'addendum' && !activeAddendum.value)) return;
  try {
    const activeAddendumId = type === 'addendum' ? activeAddendum.value!.id : null;
    await uploadContractFile('student', activeContract.value.id, activeAddendumId, uploadFile.raw!).then(res => {
      if (res && res.success) {
        ElMessage.success(res.message || t(type === 'addendum' ? 'studentAdmin.addendum.uploadSuccess' : 'studentAdmin.contractUploadSuccess'));
        emit('updateContent', 'contract')
      }
    }).catch(err => {
      console.log(err)
      ElMessage.error(getApiErrorMessage(err, t(type === 'addendum' ? 'studentAdmin.addendum.uploadFailed' : 'studentAdmin.contractUploadFailed')));
    }).finally(() => {
      if (type === 'addendum') {
        uploadAddendumRef.value?.clearFiles();
        addendumFileList.value = [];
      }
      else {
        uploadRef.value?.clearFiles();
        contractFileList.value = [];
      }
    })
  } catch(err) {
    console.log(err)
    ElMessage.error(getApiErrorMessage(err, t(type === 'addendum' ? 'studentAdmin.addendum.uploadFailed' : 'studentAdmin.contractUploadFailed')));
    if (type === 'addendum') {
      uploadAddendumRef.value?.clearFiles();
      addendumFileList.value = [];
    }
    else {
      uploadRef.value?.clearFiles();
      contractFileList.value = [];
    }
  }
}

const handleDeleteContractDetail = async (id: string) => {
  if (!activeContract.value) return;
  try {
    ElMessageBox.confirm(
      t('studentAdmin.deleteContractDetailConfirm'),
      t('studentAdmin.deleteContractDetailTitle'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      }
    ).then(async () => {
      const res = assertApiSuccess(await deleteContractDetail(activeContract.value!.id, id), t('studentAdmin.deleteContractDetailFailed'));
      ElMessage.success(res.message || t('studentAdmin.deleteContractDetailSuccess'));
      // Re-fetch to update used leave counts
      // await loadContent('contracts');
      emit('updateContent', 'contracts')
    })
  } catch(err){
      ElMessage.error(getApiErrorMessage(err, t('studentAdmin.deleteContractDetailFailed')));
  }
}

const deleteLeave = async (id: string) => {
  if (!activeContract.value) return;
  try {
    ElMessageBox.confirm(
      t('studentAdmin.deleteLeaveConfirm'),
      t('studentAdmin.deleteLeaveTitle'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      }
    ).then(async () => {
      const res = assertApiSuccess(await deleteContractLeaveRecord(activeContract.value!.id, id), t('studentAdmin.deleteLeaveFailed'));
      ElMessage.success(res.message || t('studentAdmin.deleteLeaveSuccess'));
      // Re-fetch to update used leave counts
      // await loadContent('contracts');
      emit('updateContent', 'contracts')
    })
  } catch(err){
      ElMessage.error(getApiErrorMessage(err, t('studentAdmin.deleteLeaveFailed')));
  }
};

const handleViewContract = (row: StudentContract) => {
  currentContract.value = row;
  contractDialogVisible.value = true;
}

const formatDateTime = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss');
}

const getDetailTypeLabel = (type: string) => {
  if (type === 'lesson_price') return t('studentAdmin.detailTypes.lessonPrice');
  if (type === 'discount') return t('studentAdmin.detailTypes.discount');
  if (type === 'compensation') return t('studentAdmin.detailTypes.compensation');
  return type;
}

watch(activeContract, (newVal: StudentContract | null) => {
  if (isCreatingContract.value) return;
  if (newVal) {
    fillContractForm(newVal);
  }
}, { deep: true, immediate: true })

watch(() => props.contracts, () => {
  if (isCreatingContract.value && activeContract.value) {
    isCreatingContract.value = false;
    fillContractForm(activeContract.value);
  }
}, { deep: true })

watch(() => contractForm.value.total_lessons, (totalLessons) => {
  if (!isCreatingContract.value) return;
  contractForm.value.total_leave_allowed = totalLessons ? Math.ceil(totalLessons * 0.2) : null;
})
</script>

<style lang="scss" scoped>
.bg-gray-100 {
  background-color: #eef1f3;
  border: 1px solid #e2e1e4;
  color: #606266;
  text-align: center;
}
:deep(.action-column) {
  .el-form-item__content {
    justify-content: end;
  }
  .el-divider--vertical {
    height: 1.5em;
    border-color: #b5b5b5;
  }
}

:deep(.contract-select) {
  .el-input__wrapper {
    height: 30px;
  }
}

:deep(.upload-file) {
  max-width: 200px;
  .el-upload-list {
    width: 100%;
    .el-upload-list__item-name {
      font-size: 11px !important;
    }
  }
}
</style>
