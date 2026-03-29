<template>
  <el-dialog v-model="show" :title="$t('contract.contractInfo')" width="600px" style="max-height: 80vh; overflow-y: auto;">
    <el-descriptions
      direction="vertical"
      :column="4"
      border
    >
      <el-descriptions-item label="合約編號" :span="2">{{ contract?.contract_no }}</el-descriptions-item>
      <el-descriptions-item label="起迄時間" :span="2">{{ contract?.start_date }} - {{ contract?.end_date }}</el-descriptions-item>
      <el-descriptions-item label="合約狀態">
        <div class="text-sm">
          {{ CONTRACT_STATUS_MAP[contract?.contract_status ?? ''] }}
        </div>
      </el-descriptions-item>
      <el-descriptions-item label="合約總金額" :span="3">NT$ {{ contract?.total_amount }}</el-descriptions-item>
      <el-descriptions-item label="總堂數">
        <div class="text-sm">{{ contract?.total_lessons }}</div>
      </el-descriptions-item>
      <el-descriptions-item label="可請假次數">{{ contract?.total_leave_allowed }}</el-descriptions-item>
      <el-descriptions-item label="已請假次數">{{ contract?.used_leave_count }}</el-descriptions-item>
      <el-descriptions-item label="剩餘堂數">{{ contract?.remaining_lessons }}</el-descriptions-item>
      <el-descriptions-item label="備註" :span="4">{{ contract?.notes || '無' }}</el-descriptions-item>
      <el-descriptions-item label="合約明細" :span="4">
        <el-table :data="contract?.details" size="small">
          <el-table-column prop="detail_type" label="類型">
            <template #default="scope">
              {{ scope.row.detail_type === 'lesson_price' ? '課程單價' : scope.row.detail_type === 'discount' ? '優惠折扣' : '補償堂數' }}
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
        </el-table>
      </el-descriptions-item>
  </el-descriptions>
  <template #footer>
    <div class="flex justify-center">
      <el-button round @click="closeDialog">
        <template #icon>
          <div class="i-hugeicons:cancel-circle-half-dot" />
        </template>
        {{ $t('common.close') }}
      </el-button>
    </div>
  </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { type StudentContract } from '@/api/contract'
import { computed, type PropType } from 'vue'
import { CONTRACT_STATUS_MAP } from '@/constants/contract';

const props = defineProps({
  contractDialogVisible: {
    type: Boolean,
    required: true
  },
  contract: {
    type: Object as PropType<StudentContract | null>,
    required: true
  }
})

const show = computed({
  get: () => props.contractDialogVisible,
  set: (value: any) => {
    emit('update:contractDialogVisible', value);
  }
});

const emit = defineEmits(['update:contractDialogVisible'])

const closeDialog = () => {
  emit('update:contractDialogVisible', false)
}

</script>
