<template>
  <el-dialog v-model="show" :title="`${currentStudent?.name}(${currentStudent?.student_no}) - 轉正`" width="500px">
    <el-form :model="convertForm" :rules="convertRules" ref="convertFormRef" label-position="top" label-width="120px" @submit.prevent>
      <el-row>
        <el-col :span="16">
          <el-form-item label="合約編號" prop="contract_no">
            <el-input v-model="convertForm.contract_no" placeholder="請輸入合約編號"></el-input>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="總堂數" prop="total_lessons">
            <el-input-number v-model="convertForm.total_lessons" :min="1" class="w-full"></el-input-number>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="合約總金額" prop="total_amount">
            <el-input-number v-model="convertForm.total_amount" :min="0" class="w-full">
              <template #prefix>
                <span class="text-gray-400">NT$</span>
              </template>
            </el-input-number>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="24">
          <el-form-item label="起迄日期" prop="dateRange">
            <el-date-picker v-model="convertForm.dateRange" type="daterange" value-format="YYYY-MM-DD" class="w-full"></el-date-picker>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="關聯試上預約">
            <el-select v-model="convertForm.booking_id" :disabled="bookingOptions.length === 0" :placeholder="bookingOptions.length > 0 ? '請選擇' : '無預約紀錄'" class="w-full" clearable>
              <el-option v-for="b in bookingOptions" :key="b.id" :label="b.booking_no + ' - ' + b.booking_date" :value="b.id"></el-option>
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="指定教師">
            <el-select v-model="convertForm.teacher_id" placeholder="請選擇教師(選填)" class="w-full" clearable>
              <el-option v-for="t in teacherOptions" :key="t.id" :label="t.name" :value="t.id"></el-option>
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="24">
          <el-form-item label="備註">
            <el-input type="textarea" v-model="convertForm.notes" :rows="3"></el-input>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
    <template #footer>
      <el-button @click="show = false">取消</el-button>
      <el-button type="primary" :loading="converting" @click="submitConvert">確認轉正</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { convertToFormal, type ConvertToFormalRequest, type StudentResponse } from '@/api/student';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { reactive, ref, computed, type PropType } from 'vue'

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
      type: Array,
      required: true
    },
    teacherOptions: {
      type: Array,
      required: true
    }
})

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
    contract_no: [{ required: true, message: '請輸入合約編號', trigger: 'blur' }],
    total_lessons: [{ required: true, message: '請輸入總堂數', trigger: 'blur' }],
    total_amount: [{ required: true, message: '請輸入合約總金額', trigger: 'blur' }],
    dateRange: [{ required: true, message: '請選擇起迄日期', trigger: 'change' }]
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
        const res: any = await convertToFormal(props.currentStudent.id, payload);
        ElMessage.success('轉換學生身份成功');
          
        const rowAny: any = props.currentStudent;
        rowAny.student_type = 'formal';
        rowAny._contract_id = res.data?.contract?.id || res.data?.id || res.contract?.id;
          
        emit('submit-finish');
      } catch (err) {
        ElMessage.error('轉換學生身份失敗');
      } finally {
        converting.value = false;
      }
    }
  });
};
</script>

<style lang="scss" scoped>

</style>