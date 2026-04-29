<template>
  <el-dialog v-model="show" :title="$t('studentAdmin.addLeaveDialog.title')" width="360px">
    <el-form :model="leaveForm" label-position="top" class="mt-2 mb-2 p-4">
      <el-form-item :label="$t('studentAdmin.leaveDate')">
        <el-date-picker v-model="leaveForm.leave_date" type="date" value-format="YYYY-MM-DD" class="w-full"></el-date-picker>
      </el-form-item>
      <el-form-item :label="$t('studentAdmin.reason')">
        <el-input v-model="leaveForm.reason" type="textarea" style="width: 100%"></el-input>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button round plain @click="show = false">{{ $t('common.cancel') }}</el-button>
      <el-button round type="primary" @click="submitLeaveForm" :loading="leaveLoading">{{ $t('common.add') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue';
import { createContractLeaveRecord, type StudentContractLeaveRecordCreate } from '@/api/studentContract';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';

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

const { t } = useI18n();

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
     ElMessage.warning(t('studentAdmin.addLeaveDialog.dateRequired'));
     return;
  }
  leaveLoading.value = true;
  try {
     const res = assertApiSuccess(await createContractLeaveRecord(props.contractId, {
        leave_date: leaveForm.leave_date,
        reason: leaveForm.reason
     }), t('studentAdmin.addLeaveDialog.createFailed'));
     ElMessage.success(res.message || t('studentAdmin.addLeaveDialog.createSuccess'));
     
     // Re-fetch to update used leave counts
    //  await loadContent('contracts');
    emit('addLeaveFinish', props.contractId)
    show.value = false;
  } catch(err) {
     ElMessage.error(getApiErrorMessage(err, t('studentAdmin.addLeaveDialog.createFailed')));
  } finally {
     leaveLoading.value = false;
     leaveForm.leave_date = '';
     leaveForm.reason = '';
  }
};
</script>
