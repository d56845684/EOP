<template>
  <el-dialog
    v-model="show"
    :title="$t('studentAdmin.createContractDialog.title', { name: currentStudent?.name, studentNo: currentStudent?.student_no })"
    width="380px"
  >
    <el-form
      ref="convertFormRef"
      :model="convertForm"
      :rules="convertRules"
      size="small"
      label-position="top"
      label-width="120px"
      @submit.prevent
    >
      <el-row>
        <el-col :span="22">
          <el-form-item :label="$t('studentAdmin.createContractDialog.pendingContract')" prop="student_contract_id">
            <el-select
              v-model="convertForm.student_contract_id"
              filterable
              class="w-full h-30px"
              :disabled="sortedContractOptions.length === 0"
              :placeholder="sortedContractOptions.length > 0 ? $t('studentAdmin.createContractDialog.pendingContractPlaceholder') : $t('studentAdmin.createContractDialog.noPendingContracts')"
            >
              <template #label>
                <div v-if="selectedContractOption" class="min-w-0 flex gap-2 items-center leading-tight">
                  <span class="truncate">{{ selectedContractOption.contract_no }}</span>
                </div>
              </template>
              <el-option
                v-for="contract in sortedContractOptions"
                :key="contract.id"
                :label="formatContractOptionLabel(contract)"
                :value="contract.id"
                :disabled="!contract.contract_file_path"
              >
                <div class="flex items-center justify-between gap-4">
                  <div class="min-w-0 flex gap-2 items-center">
                    <span class="truncate">{{ contract.contract_no }}</span>
                    <span class="text-xs text-gray-500">{{ formatContractPeriodLabel(contract) }}</span>
                  </div>
                  <el-tag v-if="!contract.contract_file_path" type="warning" size="small" effect="plain">
                    {{ $t('studentAdmin.createContractDialog.contractFileRequired') }}
                  </el-tag>
                </div>
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="22">
          <el-form-item :label="$t('studentAdmin.createContractDialog.relatedTrialBooking')">
            <el-select
              v-model="convertForm.booking_id"
              :disabled="bookingOptions.length === 0"
              :placeholder="bookingOptions.length > 0 ? $t('studentAdmin.pleaseSelect') : $t('studentAdmin.noBookingRecords')"
              class="w-full h-30px"
              clearable
            >
              <el-option
                v-for="booking in bookingOptions"
                :key="booking.id"
                :label="`${booking.booking_no} - ${booking.booking_date}`"
                :value="booking.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
    <template #footer>
      <el-button round @click="show = false">{{ $t('common.cancel') }}</el-button>
      <el-button round type="primary" :loading="converting" @click="submitConvert">
        <template #icon>
          <div class="i-hugeicons:floppy-disk" />
        </template>
        {{ $t('common.confirm') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { convertToFormal, type ConvertToFormalRequest, type ConvertToFormalResponse, type StudentResponse } from '@/api/student';
import type { StudentContract } from '@/api/studentContract';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { reactive, ref, computed, watch, type PropType } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  convertVisible: {
    type: Boolean,
    required: true,
  },
  currentStudent: {
    type: Object as PropType<StudentResponse | null>,
    required: true,
  },
  contractOptions: {
    type: Array as PropType<StudentContract[]>,
    required: true,
  },
  bookingOptions: {
    type: Array as PropType<any[]>,
    required: true,
  },
});

const { t } = useI18n();

const emit = defineEmits<{
  (event: 'submit-finish', payload: ConvertToFormalResponse): void;
  (event: 'update:convertVisible', value: boolean): void;
}>();

const converting = ref(false);
const convertFormRef = ref<FormInstance | null>(null);

const show = computed({
  get: () => props.convertVisible,
  set: (value: boolean) => {
    emit('update:convertVisible', value);
  },
});

const convertForm = reactive({
  student_contract_id: '',
  booking_id: null as string | null,
});

const convertRules = reactive<FormRules>({
  student_contract_id: [{ required: true, message: t('studentAdmin.createContractDialog.pendingContractRequired'), trigger: 'change' }],
});

const formatContractOptionLabel = (contract: StudentContract) => {
  return `${contract.contract_no} - ${contract.start_date} ~ ${contract.end_date}`;
};

const formatContractPeriodLabel = (contract: StudentContract) => {
  return `${contract.start_date} ~ ${contract.end_date}`;
};

const getContractTimestamp = (contract: StudentContract) => {
  const dateValue = contract.updated_at || contract.created_at || contract.start_date || contract.end_date;
  const timestamp = Date.parse(dateValue);
  return Number.isNaN(timestamp) ? 0 : timestamp;
};

const sortedContractOptions = computed(() => {
  return [...props.contractOptions].sort((a, b) => getContractTimestamp(b) - getContractTimestamp(a));
});

const selectedContractOption = computed(() => {
  return sortedContractOptions.value.find((contract) => contract.id === convertForm.student_contract_id);
});

const setDefaultContractSelection = () => {
  if (!show.value) return;
  const selectedStillExists = sortedContractOptions.value.some((contract) => contract.id === convertForm.student_contract_id);
  if (selectedStillExists) return;
  convertForm.student_contract_id = sortedContractOptions.value[0]?.id || '';
};

const resetForm = () => {
  convertForm.student_contract_id = '';
  convertForm.booking_id = null;
  convertFormRef.value?.clearValidate();
};

watch(show, (visible) => {
  if (visible) {
    resetForm();
    setDefaultContractSelection();
  }
});

watch(sortedContractOptions, () => {
  setDefaultContractSelection();
});

const submitConvert = async () => {
  if (!convertFormRef.value) return;
  await convertFormRef.value.validate(async (valid) => {
    if (valid && props.currentStudent) {
      converting.value = true;
      try {
        const payload: ConvertToFormalRequest = {
          student_contract_id: convertForm.student_contract_id,
          booking_id: convertForm.booking_id || null,
        };
        const res = assertApiSuccess(await convertToFormal(props.currentStudent.id, payload), t('studentAdmin.createContractDialog.convertFailed'));
        ElMessage.success(res.message || t('studentAdmin.createContractDialog.convertSuccess'));
        if (res.bonus_error) {
          ElMessage.warning(res.bonus_error);
        }

        const rowAny: any = props.currentStudent;
        rowAny.student_type = res.student.student_type;
        rowAny._contract_id = res.contract.id;

        show.value = false;
        emit('submit-finish', res);
      } catch (err) {
        ElMessage.error(getApiErrorMessage(err, t('studentAdmin.createContractDialog.convertFailed')));
      } finally {
        converting.value = false;
      }
    }
  });
};
</script>

<style lang="scss" scoped>
</style>
