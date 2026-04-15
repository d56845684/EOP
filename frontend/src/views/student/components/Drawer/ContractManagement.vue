<template>
  <div v-loading="contractLoading" class="pl-1 pr-2">
    <template v-if="hasActive">
      <!-- 當前合約 Current Contract -->
      <el-divider content-position="left" class="mt-1 mb-8">
        <span class="text-13px color-[#1d2d44]">當前合約</span>
      </el-divider>
      <el-row :gutter="60">
        <el-col :span="12">
          <div class="flex flex-col items-start mb-2">
            <label class="mb-2 flex-shrink-0 text-xs color-[#606266]">合約編號</label>
            <div class="w-full text-xs mt-1">{{ activeContract?.contract_no }}</div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="flex flex-col items-start mb-2">
            <label class="mb-2 flex-shrink-0 text-xs color-[#606266]">合約書狀態</label>
            <div class="w-full text-12px flex flex-col items-start gap-2" :class="activeContract?.contract_file_uploaded_at ? 'text-green' : 'text-red'">
              <div class="flex items-center gap-2">
                <div class="flex items-center gap-1">
                  <div :class="activeContract?.contract_file_uploaded_at ? 'i-hugeicons:checkmark-circle-03' : 'i-hugeicons:alert-02'" />
                  <span>{{ activeContract?.contract_file_uploaded_at ? '已上傳' : '未上傳' }}</span>
                </div>
                <el-upload
                  ref="uploadRef"
                  v-model:file-list="contractFileList"
                  class="upload-file flex flex-col items-start ml-4"
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
                    {{ activeContract?.contract_file_uploaded_at ? '更新合約書' : '上傳合約書' }}
                  </el-button>
                </el-upload>
              </div>
              <div
                v-if="activeContract?.contract_file_uploaded_at"
                class="text-11px color-gray-400 mt-2"
              >
                更新時間：{{ dayjs(activeContract?.contract_file_uploaded_at).format('YYYY-MM-DD HH:mm:ss') }}
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
      <!-- Main Contract Form -->
      <el-form :model="contractForm" size="small" label-position="top" class="constract-form mt-4">
        <el-row :gutter="60">
          <el-col :span="12">
            <el-form-item label="合約狀態">
              <el-select v-model="contractForm.contract_status" class="w-150px contract-select">
                <el-option label="待生效" value="pending"></el-option>
                <el-option label="生效中" value="active"></el-option>
                <el-option label="已過期" value="expired"></el-option>
                <el-option label="已終止" value="terminated"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="帶狀課學生">
              <el-switch
                v-model="contractForm.is_recurring"
                size="large"
                inline-prompt
                active-text="是"
                inactive-text="否"
                style="--el-switch-off-color: #a7a8bd"
                class="translate-y-[-4px]"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="起迄時間">
              <el-date-picker
                v-model="contractForm.dateRange"
                type="daterange"
                value-format="YYYY-MM-DD"
                range-separator="至"
                class="w-full h-30px!"
                :readonly="!contractCanEdit"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="總堂數">
              <el-input-number
                v-model="contractForm.total_lessons"
                :min="1"
                :readonly="!contractCanEdit"
                class="w-150px h-30px"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="剩餘堂數">
              <span class="block w-130px h-30px line-height-30px px-2 bg-gray-100 rounded">
                {{ activeContract?.remaining_lessons }}
              </span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="合約總金額">
              <el-input-number
                v-model="contractForm.total_amount"
                :min="0"
                :readonly="!contractCanEdit"
                class="w-150px h-30px!"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="可請假次數">
              <el-input-number
                v-model="contractForm.total_leave_allowed"
                :min="0"
                :readonly="!contractCanEdit"
                class="w-150px h-30px!"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="已請假次數">
              <span class="block w-130px h-30px line-height-30px px-2 bg-gray-100 rounded">
                {{ activeContract?.used_leave_count }}
              </span>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="備註">
              <el-input
                type="textarea"
                v-model="contractForm.notes"
                :rows="3"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-button type="primary" round size="small" class="py-3!" :loading="savingContract" @click="saveContractData">
              <template #icon>
                <div class="i-hugeicons:floppy-disk text-lg" />
              </template>
              儲存
            </el-button>
          </el-col>
          <el-col :span="12" justify="end">
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
                  產生合約書
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
                  附約
                </el-button>
              </el-space>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <!-- 附約 Addendum  -->
      <template v-if="(activeContract?.addendums.length || 0) > 0">
        <el-divider content-position="left" class="mt-5 mb-5">
          <span class="text-13px color-[#1d2d44]">附約</span>
        </el-divider>
        <el-table :data="activeContract?.addendums" border :preserve-expanded-content="false" size="small" class="mb-8">
          <el-table-column type="expand" width="50">
            <template #default="props">
              <el-row class="px-4">
                <el-col :span="24" class="my-1">
                  <label class="text-12px color-gray-400 font-500 mr-4">備註</label>
                  <span class="text-12px">{{ props.row.notes || '-' }}</span>
                </el-col>
                <el-col :span="24" class="my-1">
                  <label class="text-12px color-gray-400 font-500 mr-4">附約文件</label>
                  <span class="text-12px">{{ props.row.file_name || '-' }}</span>
                </el-col>
                <el-col :span="24" class="my-1">
                  <label class="text-12px color-gray-400 font-500 mr-4">上傳時間</label>
                  <span class="text-12px">{{ props.row.file_uploaded_at ? formatDateTime(props.row.file_uploaded_at) : '-' }}</span>
                </el-col>
                <el-col :span="24" class="my-1">
                  <label class="text-12px color-gray-400 font-500 mr-4">建立時間</label>
                  <span class="text-12px">{{ props.row.created_at ? formatDateTime(props.row.created_at) : '-' }}</span>
                </el-col>
                <el-col :span="24" class="my-1">
                  <label class="text-12px color-gray-400 font-500 mr-4">更新時間</label>
                  <span class="text-12px">{{ props.row.updated_at ? formatDateTime(props.row.updated_at) : '-' }}</span>
                </el-col>
              </el-row>
            </template>
          </el-table-column>
          <el-table-column prop="addendum_no" label="附約編號" width="180" />
          <el-table-column prop="addendum_status" label="附約狀態" width="80">
            <template #default="scope">
              {{ STUDENT_CONTRACT_STATUS_MAP[scope.row.addendum_status] }}
            </template>
          </el-table-column>
          <el-table-column prop="new_end_date" label="展延結束日期" width="120" />
          
          <el-table-column label="操作" min-width="80" align="center">
              <template #default="{row}">
                <el-row>
                  <el-col :span="8">
                    <el-tooltip content="編輯" effect="customized">
                      <el-button type="primary" round link @click="extendContract('update', row)">
                        <div class="i-hugeicons:edit-02" />
                      </el-button>
                    </el-tooltip>
                  </el-col>
                  <el-col :span="8">
                    <el-tooltip content="上傳附約文件" effect="customized">
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
                    <el-tooltip content="刪除" effect="customized">
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
      <el-divider content-position="left" class="mt-5 mb-3">
        <span class="text-13px color-[#1d2d44]">合約明細</span>
      </el-divider>
      <el-button type="primary" round text size="small" class="float-right mb-2" @click="openAddDetailDialog">
        <template #icon><div class="i-hugeicons:add-square" /></template>
        新增明細
      </el-button>
      <el-table :data="contractDetails" size="small" class="mt-2 w-full" border>
        <el-table-column prop="detail_type" label="類型" width="100">
          <template #default="{ row }">
            {{ row.detail_type === 'lesson_price' ? '課程單價' : row.detail_type === 'discount' ? '優惠折扣' : '補償堂數' }}
          </template>
        </el-table-column>
        <el-table-column
          prop="amount"
          label="金額/堂數"
          width="120"
          :formatter="(
            row: { detail_type: string; amount: string; }) => 
              row.detail_type !== 'compensation' ? 
                'NT$ ' + row.amount : 
                row.amount + ' 堂'
          "
        />
        <el-table-column prop="description" label="說明" />
        <el-table-column prop="notes" label="備註" />
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="{ row }">
            <el-tooltip content="編輯" effect="customized">
              <el-button type="primary" round link @click="handleEditContractDetail(row)">
                <div class="i-hugeicons:edit-02" />
              </el-button>
            </el-tooltip>
            <el-tooltip content="刪除" effect="customized">
              <el-button type="danger" round link @click="handleDeleteContractDetail(row.id)">
                <div class="i-hugeicons:delete-02" />
              </el-button>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <!-- 請假紀錄 Leave Records -->
      <el-divider content-position="left" class="mt-10 mb-5">
        <span class="text-13px color-[#1d2d44]">請假紀錄</span>
      </el-divider>
      <el-button type="primary" round text size="small" class="float-right mb-2" @click="addLeaveDialogVisible = true">
        <template #icon><div class="i-hugeicons:add-square" /></template>
        新增請假
      </el-button>
      <el-table :data="leaveRecords" border size="small" empty-text="目前沒有請假紀錄">
        <el-table-column prop="leave_date" label="請假日期" width="120" />
        <el-table-column prop="reason" label="事由" />
        <el-table-column label="操作" width="80" align="center">
            <template #default="{ row }">
              <el-tooltip content="刪除" effect="customized">
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
          新增合約
        </el-button>
      </div>
    </template>

    <!-- 歷史合約 History Contracts -->
    <el-divider content-position="left" class="mt-10 mb-5">
      <span class="text-13px color-[#1d2d44]">歷史合約</span>
    </el-divider>
    <el-table :data="contractHistory" border size="small" empty-text="目前沒有歷史合約紀錄">
      <el-table-column prop="contract_no" label="合約編號" width="180" />
      <el-table-column label="起迄時間" min-width="200">
        <template #default="{ row }">
          {{ row.start_date }} ~ {{ row.end_date }}
        </template>
      </el-table-column>
      <el-table-column prop="contract_status" label="合約狀態" width="100" align="center">
        <template #default="{ row }">
          {{ STUDENT_CONTRACT_STATUS_MAP[row.contract_status] || row.contract_status }}
        </template>
      </el-table-column>
      <el-table-column label="檢視" width="60" align="center">
        <template #default="{ row }">
          <el-tooltip content="檢視" effect="customized">
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
  generateContract,
  createAddendum,
  updateAddendum,
  type StudentContract,
  type StudentContractDetail ,
  type StudentContractAddendum
} from '@/api/studentContract';
import { CONTRACT_STATUS, STUDENT_CONTRACT_STATUS_MAP } from '@/constants/contract';
import { triggerDownload, getFileNameFromResponse}  from '@/utils/download';
import { uploadContractFile } from '@/utils/upload';

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

const contractForm = ref({
  contract_status: 'pending',
  is_recurring: false,
  dateRange: [] as string[],
  total_lessons: 0,
  total_amount: 0,
  total_leave_allowed: 0,
  notes: ''
})

const detailVisible = ref(false);
const addLeaveDialogVisible = ref(false)
const contractDialogVisible = ref(false)
const extendDialogVisible = ref(false)
const savingContract = ref(false)
const contractDetailData = ref<StudentContractDetail | null>(null);
const currentContract = ref<StudentContract | null>(null);
const extendType = ref<'create' | 'update'>('create');
const activeAddendum = ref<StudentContractAddendum | null>(null);

const addendumFileList = ref([]);
const contractFileList = ref([]);

const contractCanEdit = computed(() => {
  return activeContract.value?.contract_status === CONTRACT_STATUS.PENDING;
})

const activeContract = computed(() => {
  return props.contracts.find((contract) => contract.contract_status === CONTRACT_STATUS.ACTIVE) || null;
})

const contractHistory = computed(() => {
  return props.contracts.filter((contract) => contract.contract_status !== CONTRACT_STATUS.ACTIVE);
})

const emit = defineEmits([
  'saveContractData',
  'updateContent',
  'updateContractDetails',
  'openAddContractDialog'
])

const openAddContractDialog = () => {
  emit('openAddContractDialog')
}

const openAddDetailDialog = () => {
  detailVisible.value = true;
}

const saveContractData = () => {
  // TODO: Save contract data
  emit('saveContractData', contractForm.value)
}

const handleUpdateContractDetails = () => {
  // TODO: Update contract details
  emit('updateContractDetails', activeContract.value?.id)
}

const handleAddendum = async ({data, addendumId}: {data: StudentContractAddendum, addendumId?: string}) => {
  // TODO: Update addendum
  if (!activeContract.value) return;
  try {
    const res = extendType.value === 'create' ? await createAddendum(activeContract.value.id, data) : await updateAddendum(activeContract.value.id, addendumId!, data)
    assertApiSuccess(res, `${extendType.value === 'create' ? '新增' : '更新'}合約附約失敗`);
    ElMessage.success(res.message || `${extendType.value === 'create' ? '新增' : '更新'}合約附約成功`);
    extendDialogVisible.value = false;
    emit('updateContent', 'contract')
  } catch(err) {
    ElMessage.error(getApiErrorMessage(err, `${extendType.value === 'create' ? '新增' : '更新'}合約附約失敗`));
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
    ElMessage.error('下載合約失敗');
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
        ElMessage.success(res.message || `${type === 'addendum' ? '合約附約' : '合約'}已上傳`);
        emit('updateContent', 'contract')
      }
    }).catch(err => {
      console.log(err)
      ElMessage.error(getApiErrorMessage(err, `${type === 'addendum' ? '合約附約' : '合約'}上傳失敗`));
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
    ElMessage.error(getApiErrorMessage(err, `${type === 'addendum' ? '合約附約' : '合約'}上傳失敗`));
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
      '確定要刪除此合約明細嗎？',
      '刪除合約明細',
      {
        confirmButtonText: '確定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    ).then(async () => {
      const res = assertApiSuccess(await deleteContractDetail(activeContract.value!.id, id), '刪除合約明細失敗');
      ElMessage.success(res.message || '合約明細已刪除');
      // Re-fetch to update used leave counts
      // await loadContent('contracts');
      emit('updateContent', 'contracts')
    })
  } catch(err){
      ElMessage.error(getApiErrorMessage(err, '刪除合約明細失敗'));
  }
}

const deleteLeave = async (id: string) => {
  if (!activeContract.value) return;
  try {
    ElMessageBox.confirm(
      '確定要刪除此請假紀錄嗎？',
      '刪除請假紀錄',
      {
        confirmButtonText: '確定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    ).then(async () => {
      const res = assertApiSuccess(await deleteContractLeaveRecord(activeContract.value!.id, id), '刪除請假紀錄失敗');
      ElMessage.success(res.message || '請假紀錄已刪除');
      // Re-fetch to update used leave counts
      // await loadContent('contracts');
      emit('updateContent', 'contracts')
    })
  } catch(err){
      ElMessage.error(getApiErrorMessage(err, '刪除請假紀錄失敗'));
  }
};

const handleViewContract = (row: StudentContract) => {
  currentContract.value = row;
  contractDialogVisible.value = true;
}

const formatDateTime = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss');
}

watch(activeContract, (newVal: StudentContract | null) => {
  if (newVal) {
    contractForm.value = {
      contract_status: newVal.contract_status,
      is_recurring: newVal.is_recurring,
      dateRange: [newVal.start_date, newVal.end_date],
      total_lessons: newVal.total_lessons,
      total_amount: newVal.total_amount,
      total_leave_allowed: newVal.total_leave_allowed,
      notes: newVal.notes || ''
    }
    if (newVal.addendums && newVal.addendums.length > 0) {
      activeAddendum.value = newVal.addendums[newVal.addendums.length - 1] || null;
    }
  }
}, { deep: true, immediate: true })
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
    &__item-name {
      font-size: 11px !important;
    }
  }
}
</style>
