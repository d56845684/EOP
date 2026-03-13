<template>
  <div v-loading="contractLoading">
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
        <el-col :span="24">
          <el-form-item label="起迄時間">
            <el-date-picker v-model="contractForm.dateRange" type="daterange" value-format="YYYY-MM-DD" class="w-full"></el-date-picker>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="總堂數">
            <el-input-number v-model="contractForm.total_lessons" :min="1" class="w-full"></el-input-number>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="剩餘堂數">
            <span class="block h-30px line-height-30px px-2 bg-gray-100 rounded">{{ contract.remaining_lessons }}</span>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="合約總金額">
            <el-input-number v-model="contractForm.total_amount" :min="0" class="w-full"></el-input-number>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="可請假次數">
            <el-input-number v-model="contractForm.total_leave_allowed" :min="0" class="w-full"></el-input-number>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="已請假次數">
            <span class="block h-30px line-height-30px px-2 bg-gray-100 rounded">{{ contract.used_leave_count }}</span>
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="備註">
            <el-input type="textarea" v-model="contractForm.notes" :rows="3"></el-input>
          </el-form-item>
        </el-col>
        <el-col :span="24" justify="end">
          <el-form-item class="w-full action-column">
              <el-space :size="10" :spacer="h(ElDivider, { direction: 'vertical' })">
                <el-button type="primary" :loading="savingContract" @click="saveContractData">
                  <template #icon>
                    <div class="i-hugeicons:floppy-disk text-lg" />
                  </template>
                  儲存合約
                </el-button>
                <el-button color="#626aef" plain :loading="savingContract" @click="saveContractData">
                  <template #icon>
                    <div class="i-hugeicons:file-download" />
                  </template>
                  下載合約
                </el-button>
              </el-space>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <el-divider content-position="left" class="mt-5 mb-3">合約明細</el-divider>
    <el-button type="primary" text class="float-right mb-2" @click="openAddDetailDialog">
      <template #icon><div class="i-hugeicons:add-square" /></template>
      新增明細
    </el-button>
    <el-table :data="contractDetails" class="mt-2 w-full" size="small" border>
        <el-table-column prop="detail_type" label="類型">
          <template #default="{ row }">
            {{ row.detail_type === 'lesson_price' ? '課程單價' : row.detail_type === 'discount' ? '優惠折扣' : '補償堂數' }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="說明" />
        <el-table-column prop="amount" label="金額" />
        <el-table-column prop="notes" label="備註" />
    </el-table>

    <el-divider content-position="left" class="mt-10 mb-5">請假紀錄</el-divider>
    <el-form :inline="true" :model="leaveForm" label-position="left" size="small" class="mt-2 mb-2 p-4 bg-gray-50 rounded">
      <el-form-item label="請假日期">
          <el-date-picker v-model="leaveForm.leave_date" type="date" value-format="YYYY-MM-DD" style="width: 140px"></el-date-picker>
      </el-form-item>
      <el-form-item label="事由">
          <el-input v-model="leaveForm.reason" style="width: 160px"></el-input>
      </el-form-item>
      <el-form-item class="h-full">
        <div class="w-full flex justify-end items-center">
          <el-button type="primary" size="small" @click="submitLeaveForm" :loading="leaveLoading">新增</el-button>
        </div>
      </el-form-item>
    </el-form>
    <el-table :data="leaveRecords" size="small" border>
      <el-table-column prop="leave_date" label="請假日期" />
      <el-table-column prop="reason" label="事由" />
      <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button type="danger" link @click="deleteLeave(row.id)">
              <div class="i-hugeicons:delete-02" />
            </el-button>
          </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { h, ref } from 'vue';
import { ElDivider } from 'element-plus'

  const props = defineProps({
    contract: {
      type: Object,
      required: true
    },
    contractLoading: {
      type: Boolean,
      required: true
    }
  })

  const contractForm = ref({
    contract_status: 'pending',
    is_recurring: false,
    dateRange: [],
    total_lessons: 0,
    total_amount: 0,
    total_leave_allowed: 0,
    notes: ''
  })

  const leaveForm = ref({
    leave_date: '',
    reason: ''
  })

  const contractDetails = ref([])
  const leaveRecords = ref([])

  const savingContract = ref(false)
  const leaveLoading = ref(false)

  const emit = defineEmits(['openAddDetailDialog', 'submitLeaveForm', 'deleteLeave', 'saveContractData'])

  const openAddDetailDialog = () => {
    // TODO: Open dialog to add contract details
    emit('openAddDetailDialog')
  }

  const submitLeaveForm = () => {
    // TODO: Submit leave form
    emit('submitLeaveForm')
  }

  const deleteLeave = (id) => {
    // TODO: Delete leave record
    emit('deleteLeave', id)
  }

  const saveContractData = () => {
    // TODO: Save contract data
    emit('saveContractData')
  } 
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