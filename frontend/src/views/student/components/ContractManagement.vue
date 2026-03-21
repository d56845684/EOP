<template>
  <div v-loading="contractLoading">
    <div class="flex items-center mb-2">
      <label class="w-100px text-sm color-[#606266]">合約編號</label>
      <div class="w-full text-sm">{{ contract.contract_no }}</div>
    </div>
    <!-- Main Contract Form -->
    <el-form :model="contractForm" label-position="top" class="constract-form mt-4">
      <el-row :gutter="40">
        <el-col :span="12">
          <el-form-item label="合約狀態">
            <el-select v-model="contractForm.contract_status" class="w-full">
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
              class="w-full"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="總堂數">
            <el-input-number
              v-model="contractForm.total_lessons"
              :min="1"
              class="w-full"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="剩餘堂數">
            <span class="block h-30px line-height-30px px-2 bg-gray-100 rounded">
              {{ contract.remaining_lessons }}
            </span>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="合約總金額">
            <el-input-number
              v-model="contractForm.total_amount"
              :min="0"
              class="w-full"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="可請假次數">
            <el-input-number
              v-model="contractForm.total_leave_allowed"
              :min="0"
              class="w-full"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="已請假次數">
            <span class="block h-30px line-height-30px px-2 bg-gray-100 rounded">
              {{ contract.used_leave_count }}
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
        <el-col :span="24" justify="end">
          <el-form-item class="w-full action-column">
              <el-space :size="10" :spacer="h(ElDivider, { direction: 'vertical' })">
                <el-button type="primary" round :loading="savingContract" @click="saveContractData">
                  <template #icon>
                    <div class="i-hugeicons:floppy-disk text-lg" />
                  </template>
                  儲存合約
                </el-button>
                <el-button
                  color="#626aef"
                  plain
                  round
                  :loading="savingContract"
                  @click="downloadContractData"
                >
                  <template #icon>
                    <div class="i-hugeicons:file-download" />
                  </template>
                  下載合約
                </el-button>
                <el-button
                  color="#626aef"
                  plain
                  round
                  :loading="savingContract"
                  @click="uploadContractData"
                >
                  <template #icon>
                    <div class="i-hugeicons:file-upload" />
                  </template>
                  上傳合約
                </el-button>
              </el-space>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <el-divider content-position="left" class="mt-5 mb-3">合約明細</el-divider>
    <el-button type="primary" round text class="float-right mb-2" @click="openAddDetailDialog">
      <template #icon><div class="i-hugeicons:add-square" /></template>
      新增明細
    </el-button>
    <el-table :data="contractDetails" class="mt-2 w-full" border>
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
              <el-button type="primary" round link @click="handleEditContractDetail(row)">
                <div class="i-hugeicons:edit-02" />
              </el-button>
              <el-button type="danger" round link @click="handleDeleteContractDetail(row.id)">
                <div class="i-hugeicons:delete-02" />
              </el-button>
            </template>
        </el-table-column>
    </el-table>

    <el-divider content-position="left" class="mt-10 mb-5">請假紀錄</el-divider>
    <el-button type="primary" round text class="float-right mb-2" @click="addLeaveDialogVisible = true">
      <template #icon><div class="i-hugeicons:add-square" /></template>
      新增請假
    </el-button>
    <el-table :data="leaveRecords" border>
      <el-table-column prop="leave_date" label="請假日期" width="120" />
      <el-table-column prop="reason" label="事由" />
      <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button type="danger" round link @click="deleteLeave(row.id)">
              <div class="i-hugeicons:delete-02" />
            </el-button>
          </template>
      </el-table-column>
    </el-table>

    <!-- Contract Detail Dialog -->
    <ContractDetailsDialog
      v-model:detailVisible="detailVisible"
      :studentId="contract.student_id"
      :contractId="contract?.id || ''"
      :detailData="contractDetailData"
      @addDetailFinish="handleUpdateContractDetails"
    />

    <AddLeaveDialog 
      v-model:addLeaveDialogVisible="addLeaveDialogVisible"
      :contractId="contract.id"
      @addLeaveFinish="handleUpdateContractDetails"
    />
  </div>
</template>

<script setup lang="ts">
import { h, ref, watch } from 'vue';
import { ElDivider, ElMessage, ElMessageBox } from 'element-plus'
import ContractDetailsDialog from './ContractDetailsDialog.vue';
import AddLeaveDialog from './AddLeaveDialog.vue';
import { deleteContractDetail, deleteContractLeaveRecord, getContractDownloadUrl, type StudentContract, type StudentContractDetail } from '@/api/contract';

const props = defineProps({
  contract: {
    type: Object as () => StudentContract,
    required: true
  },
  contractLoading: {
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
const savingContract = ref(false)
const contractDetailData = ref<StudentContractDetail | null>(null);

const emit = defineEmits([
  'saveContractData',
  'updateContent',
  'updateContractDetails'
])

const openAddDetailDialog = () => {
  detailVisible.value = true;
}

const saveContractData = () => {
  // TODO: Save contract data
  emit('saveContractData', contractForm.value)
}

const handleUpdateContractDetails = () => {
  // TODO: Update contract details
  emit('updateContractDetails', props.contract.id)
}

const handleEditContractDetail = (detail: StudentContractDetail) => {
  // TODO: Edit contract details
  contractDetailData.value = detail;
  detailVisible.value = true;
}

const downloadContractData = async () => {
  let url = ''
  const res = await getContractDownloadUrl(props.contract.id);
  if (res && res.data) {
    url = res.data
    window.open(url, '_blank')
  }
}

const uploadContractData = async () => {
  // TODO: Upload contract data
}

const handleDeleteContractDetail = async (id: string) => {
  if (!props.contract) return;
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
      await deleteContractDetail(props.contract.id, id);
      ElMessage.success('合約明細已刪除');
      // Re-fetch to update used leave counts
      // await loadContent('contracts');
      emit('updateContent', 'contracts')
    })
  } catch(err){
      ElMessage.error('刪除合約明細失敗');
  }
}

const deleteLeave = async (id: string) => {
  if (!props.contract) return;
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
      await deleteContractLeaveRecord(props.contract.id, id);
      ElMessage.success('請假紀錄已刪除');
      // Re-fetch to update used leave counts
      // await loadContent('contracts');
      emit('updateContent', 'contracts')
    })
  } catch(err){
      ElMessage.error('刪除請假紀錄失敗');
  }
};

watch(() => props.contract, (newVal: StudentContract) => {
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
  }
}, { deep: true, immediate: true })
</script>

<style lang="scss" scoped>
.bg-gray-100 {
  background-color: #eef1f3;
  border: 1px solid #e2e1e4;
  color: #606266;
  width: 100%;
  display: inline-block;
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
</style>