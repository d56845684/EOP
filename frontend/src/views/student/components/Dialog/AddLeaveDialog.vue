<template>
  <el-dialog v-model="show" title="新增請假" width="360px">
    <el-form :model="leaveForm" label-position="top" class="mt-2 mb-2 p-4">
      <el-form-item label="請假日期">
        <el-date-picker v-model="leaveForm.leave_date" type="date" value-format="YYYY-MM-DD" class="w-full"></el-date-picker>
      </el-form-item>
      <el-form-item label="事由">
        <el-input v-model="leaveForm.reason" type="textarea" style="width: 100%"></el-input>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button round plain @click="show = false">取消</el-button>
      <el-button round type="primary" @click="submitLeaveForm" :loading="leaveLoading">新增</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue';
import { createContractLeaveRecord, type StudentContractLeaveRecordCreate } from '@/api/contract';
import { ElMessage } from 'element-plus';

const props = defineProps({
  addLeaveDialogVisible: {
    type: Boolean,
    default: false
  },
  contractId: {
    type: String,
    required: true
  }
})

const show = computed({
  get: () => props.addLeaveDialogVisible,
  set: (value) => {
    emit('update:addLeaveDialogVisible', value);
  }
});

const leaveLoading = ref(false);
const leaveForm = reactive<StudentContractLeaveRecordCreate>({
  leave_date: '',
  reason: ''
});

const emit = defineEmits(['addLeaveFinish', 'update:addLeaveDialogVisible'])

// --- Leave Records API ---
const submitLeaveForm = async () => {
  if (!leaveForm.leave_date || !props.contractId) {
     ElMessage.warning('請選擇請假日期');
     return;
  }
  leaveLoading.value = true;
  try {
     await createContractLeaveRecord(props.contractId, {
        leave_date: leaveForm.leave_date,
        reason: leaveForm.reason
     });
     ElMessage.success('請假紀錄已新增');
     
     // Re-fetch to update used leave counts
    //  await loadContent('contracts');
    emit('addLeaveFinish', props.contractId)
    show.value = false;
  } catch(err) {
     ElMessage.error('新增請假紀錄失敗');
  } finally {
     leaveLoading.value = false;
     leaveForm.leave_date = '';
     leaveForm.reason = '';
  }
};
</script>
