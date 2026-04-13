<template>
  <el-dialog v-model="show" :title="type === 'create' ? '新增附約' : '編輯附約'" width="360px" style="max-height: 80vh; overflow-y: auto;">
    <div class="w-full box-border rounded-lg px-2 py-2 mb-4 bg-[#f5f7fa] text-xs">
      <div class="flex items-center gap-4 mb-2">
        <label class="text-xs color-[#606266] font-500">主約</label>
        <div class="flex-1">{{ contract?.contract_no }}</div>
      </div>
      <div class="flex items-center gap-4 mb-2">
        <label class="text-xs color-[#606266] font-500">學生</label>
        <div class="flex-1">{{ contract?.student_name }}</div>
      </div>
      <div class="flex items-center gap-4">
        <label class="text-xs color-[#606266] font-500">目前結束日期</label>
        <div class="flex-1">{{ contract?.end_date }}</div>
      </div>
    </div>
    <el-form label-position="top" size="small">
      <el-form-item label="更新結束時間">
        <el-date-picker
          v-model="contractForm.new_end_date"
          type="date"
          value-format="YYYY-MM-DD"
          class="w-160px! h-30px!"
        />
      </el-form-item>
      <el-form-item label="備註">
        <el-input
          type="textarea"
          v-model="contractForm.notes"
          :rows="3"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button round size="small" class="py-3!" @click="closeDialog">
        {{ $t('common.cancel') }}
      </el-button>
      <el-button type="primary" round size="small" class="py-3!" @click="saveExtendData">
        <template #icon>
          <div class="i-hugeicons:floppy-disk" />
        </template>
        {{ $t('common.confirm') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch, type PropType } from 'vue'
import type { StudentContract, StudentContractAddendum } from '@/api/studentContract';

const props = defineProps({
  extendDialogVisible: {
    type: Boolean,
    required: true
  },
  contract: {
    type: Object as PropType<StudentContract | null>,
    required: true
  },
  type: {
    type: String as PropType<'create' | 'update'>,
    required: true
  },
  addendum: {
    type: Object as PropType<StudentContractAddendum | null>,
    required: true
  }
})

const contractForm = ref({
  new_end_date: '',
  notes: ''
})

const show = computed({
  get: () => props.extendDialogVisible,
  set: (value: any) => {
    emit('update:extendDialogVisible', value);
  }
});

const emit = defineEmits(['update:extendDialogVisible', 'handleAddendum'])

const closeDialog = () => {
  emit('update:extendDialogVisible', false)
}

const saveExtendData = () => {
  emit('handleAddendum', {data: contractForm.value, addendumId: props.addendum?.id})
}

watch(() => props.addendum, (newVal) => {
  if (newVal) {
    if (props.type === 'update') {
      contractForm.value = {
        new_end_date: newVal.new_end_date,
        notes: newVal.notes
      }
    }
  }
})

</script>