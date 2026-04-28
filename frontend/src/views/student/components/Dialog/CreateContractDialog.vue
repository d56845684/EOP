<template>
  <el-dialog v-model="show" :title="$t('studentAdmin.createContractDialog.title', { name: currentStudent?.name, studentNo: currentStudent?.student_no })" width="500px">
    <el-form :model="convertForm" :rules="convertRules" ref="convertFormRef" size="small" label-position="top" label-width="120px" @submit.prevent>
      <el-row>
        <el-col :span="16">
          <el-form-item :label="$t('contract.contractNo')" prop="contract_no">
            <el-input 
              v-model="convertForm.contract_no" 
              class="h-30px" 
              :placeholder="$t('studentAdmin.createContractDialog.contractNoPlaceholder')" 
            />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="16">
          <el-form-item :label="$t('studentAdmin.period')" prop="dateRange">
            <el-date-picker
              v-model="convertForm.dateRange"
              type="daterange"
              value-format="YYYY-MM-DD"
              :range-separator="$t('studentAdmin.to')"
              class="h-30px!"
            />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="20">
        <el-col :span="10">
          <el-form-item :label="$t('contract.contractTotalLessons')" prop="total_lessons">
            <el-input-number 
              v-model="convertForm.total_lessons" 
              :min="1" 
              class="w-200px h-30px"
            ></el-input-number>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item :label="$t('contract.contractTotalAmount')" prop="total_amount">
            <el-input-number 
              v-model="convertForm.total_amount" 
              :min="0" 
              class="w-full h-30px"
            >
              <template #prefix>
                <span class="text-gray-400">NT$</span>
              </template>
            </el-input-number>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="20">
        <el-col :span="10">
          <el-form-item :label="$t('studentAdmin.createContractDialog.relatedTrialBooking')">
            <el-select
              v-model="convertForm.booking_id"
              :disabled="bookingOptions.length === 0"
              :placeholder="bookingOptions.length > 0 ? $t('studentAdmin.pleaseSelect') : $t('studentAdmin.noBookingRecords')"
              class="w-200px h-30px"
              clearable
            >
              <el-option v-for="b in bookingOptions" :key="b.id" :label="b.booking_no + ' - ' + b.booking_date" :value="b.id"></el-option>
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item :label="$t('studentAdmin.createContractDialog.assignedTeacher')">
            <el-select 
              v-model="convertForm.teacher_id" 
              :placeholder="$t('studentAdmin.createContractDialog.teacherPlaceholder')" 
              class="w-full h-30px" 
              clearable
            >
              <el-option 
                v-for="t in teacherOptions" 
                :key="t.id" 
                :label="t.name" 
                :value="t.id"
              >
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="24">
          <el-form-item :label="$t('common.note')">
            <el-input type="textarea" v-model="convertForm.notes" :rows="3"></el-input>
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
        {{ $t('common.confirm') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { convertToFormal, type ConvertToFormalRequest, type StudentResponse } from '@/api/student';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { reactive, ref, computed, type PropType } from 'vue'
import { useI18n } from 'vue-i18n';

const props = defineProps({
    convertVisible: {
      type: Boolean,
      required: true
    },
    currentStudent: {
      type: Object as PropType<StudentResponse | null>,
      required: true
    },
    bookingOptions: {
      type: Array as PropType<any[]>,
      required: true
    },
    teacherOptions: {
      type: Array as PropType<any[]>,
      required: true
    }
})

const { t } = useI18n();

const emit = defineEmits(['submit-finish', 'update:convertVisible'])

const converting = ref(false);

const show = computed({
  get: () => props.convertVisible,
  set: (value:boolean) => {
    emit('update:convertVisible', value);
  }
});

const convertForm = reactive({
    contract_no: '',
    total_lessons: 0,
    total_amount: 0,
    dateRange: [],
    booking_id: null,
    teacher_id: null,
    notes: ''
})


const convertRules = reactive<FormRules>({
    contract_no: [{ required: true, message: t('studentAdmin.createContractDialog.contractNoRequired'), trigger: 'blur' }],
    total_lessons: [{ required: true, message: t('studentAdmin.createContractDialog.totalLessonsRequired'), trigger: 'blur' }],
    total_amount: [{ required: true, message: t('studentAdmin.createContractDialog.totalAmountRequired'), trigger: 'blur' }],
    dateRange: [{ required: true, message: t('studentAdmin.createContractDialog.dateRangeRequired'), trigger: 'change' }]
})

const convertFormRef = ref<FormInstance | null>(null);

const submitConvert = async () => {
  if (!convertFormRef.value) return;
  await convertFormRef.value.validate(async valid => {
    if (valid && props.currentStudent) {
      converting.value = true;
      try {
        const payload: ConvertToFormalRequest = {
          contract_no: convertForm.contract_no,
          total_lessons: convertForm.total_lessons,
          total_amount: convertForm.total_amount,
          start_date: convertForm.dateRange[0] || '',
          end_date: convertForm.dateRange[1] || '',
          teacher_id: convertForm.teacher_id || null,
          booking_id: convertForm.booking_id || null,
          notes: convertForm.notes || null,
        };
        const res = assertApiSuccess(await convertToFormal(props.currentStudent.id, payload), t('studentAdmin.createContractDialog.convertFailed'));
        ElMessage.success(res.message || t('studentAdmin.createContractDialog.convertSuccess'));
          
        const rowAny: any = props.currentStudent;
        rowAny.student_type = 'formal';
        rowAny._contract_id = res.data?.contract?.id || res.data?.id;
          
        emit('submit-finish');
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
