<template>
  <el-dialog v-model="show" :title="$t('contract.contractInfo')" width="600px" style="max-height: 80vh; overflow-y: auto;">
    <el-descriptions
      direction="vertical"
      :column="4"
      border
    >
      <el-descriptions-item :label="$t('contract.contractNo')" :span="2">{{ contract?.contract_no }}</el-descriptions-item>
      <el-descriptions-item :label="$t('myContracts.colPeriod')" :span="2">{{ contract?.start_date }} - {{ contract?.end_date }}</el-descriptions-item>
      <el-descriptions-item :label="$t('contract.contractStatus')">
        <div class="text-sm">
          {{ formatStudentContractStatusLabel(contract?.contract_status, contract?.contract_status ?? '-', t) }}
        </div>
      </el-descriptions-item>
      <el-descriptions-item :label="$t('contract.contractTotalAmount')" :span="3">NT$ {{ contract?.total_amount }}</el-descriptions-item>
      <el-descriptions-item :label="$t('contract.contractTotalLessons')">
        <div class="text-sm">{{ contract?.total_lessons }}</div>
      </el-descriptions-item>
      <el-descriptions-item :label="$t('studentAdmin.totalLeaveAllowed')">{{ contract?.total_leave_allowed || 0 }}</el-descriptions-item>
      <el-descriptions-item :label="$t('myContracts.usedLeaveCount')">{{ contract?.used_leave_count || 0 }}</el-descriptions-item>
      <el-descriptions-item :label="$t('myContracts.emergencyLeaveQuota')">{{ contract?.emergency_leave_quota || 0 }}</el-descriptions-item>
      <el-descriptions-item :label="$t('myContracts.usedEmergencyLeaveCount')">{{ contract?.used_emergency_leave_count || 0 }}</el-descriptions-item>
      <el-descriptions-item :label="$t('myContracts.remainingLessons')">{{ contract?.remaining_lessons }}</el-descriptions-item>
      <el-descriptions-item :label="$t('common.note')" :span="4">{{ contract?.notes || $t('studentAdmin.none') }}</el-descriptions-item>
      <el-descriptions-item :label="$t('contract.contractDetails')" :span="4">
        <el-table :data="contract?.details" size="small">
          <el-table-column prop="detail_type" :label="$t('common.type')">
            <template #default="scope">
              {{ getDetailTypeLabel(scope.row.detail_type) }}
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
import { type StudentContract } from '@/api/studentContract'
import { computed, type PropType } from 'vue'
import { useI18n } from 'vue-i18n';
import { formatStudentContractStatusLabel } from '@/utils/i18n-formatters';

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

const { t } = useI18n();

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

const getDetailTypeLabel = (type: string) => {
  if (type === 'lesson_price') return t('studentAdmin.detailTypes.lessonPrice');
  if (type === 'discount') return t('studentAdmin.detailTypes.discount');
  if (type === 'compensation') return t('studentAdmin.detailTypes.compensation');
  return type;
}

</script>
