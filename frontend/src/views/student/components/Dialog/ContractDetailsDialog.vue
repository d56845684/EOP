<template>
  <el-dialog v-model="show" title="新增合約明細" width="420px">
    <el-form :model="detailForm" :rules="detailRules" ref="detailFormRef" label-width="120px" label-position="top" @submit.prevent>
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="類型" prop="detail_type">
            <el-select v-model="detailForm.detail_type" class="w-full">
              <el-option label="課程單價" value="lesson_price"></el-option>
              <el-option label="優惠折扣" value="discount"></el-option>
              <el-option label="補償堂數" value="compensation"></el-option>
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="課程" prop="course_id" v-if="detailForm.detail_type === 'lesson_price'">
            <el-select v-model="detailForm.course_id" class="w-full" clearable>
              <el-option v-for="c in detailCourseOptions" :key="c.value" :label="c.label" :value="c.value"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="堂數" prop="amount" v-else-if="detailForm.detail_type === 'compensation'">
            <el-input-number v-model="detailForm.amount" class="w-full"></el-input-number>
          </el-form-item>
          <el-form-item label="金額" prop="amount" v-else>
            <el-input-number v-model="detailForm.amount" class="w-full">
              <template #prefix>
                <span class="text-gray-400">NT$</span>
              </template>
            </el-input-number>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="12">
          <el-form-item label="金額" prop="amount" v-if="detailForm.detail_type === 'lesson_price'">
            <el-input-number v-model="detailForm.amount" class="w-full">
              <template #prefix>
                <span class="text-gray-400">NT$</span>
              </template>
            </el-input-number>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="24">
          <el-form-item label="說明" prop="description">
            <el-input v-model="detailForm.description" maxlength="100" show-word-limit></el-input>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="24">
          <el-form-item label="備註">
            <el-input type="textarea" v-model="detailForm.notes"></el-input>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
    <template #footer>
      <el-button round @click="show = false">取消</el-button>
      <el-button round type="primary" :loading="detailLoading" @click="submitDetailForm">
        {{ isEdit ? '更新' : '新增' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { createContractDetail, type StudentContractDetailCreate, type CourseOption, getContractCourseOptions, updateContractDetail, type StudentContractDetail } from '@/api/studentContract';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { ref, computed, reactive, onMounted, watch, type PropType, nextTick } from 'vue'

const props = defineProps({
    detailVisible: {
      type: Boolean,
      required: true
    },
    contractId: {
      type: String,
      required: true
    },
    studentId: {
      type: String,
      required: true
    },
    detailData: {
      type: Object as PropType<StudentContractDetail | null>,
      required: false
    }
})

const detailFormRef = ref<FormInstance>();
const detailForm = reactive<StudentContractDetailCreate>({
  detail_type: 'lesson_price',
  course_id: '',
  description: '',
  amount: 0,
  notes: ''
});
const detailRules = reactive<FormRules>({});
const isEdit = ref(false);

const emit = defineEmits(['submit-finish', 'update:detailVisible', 'addDetailFinish'])

const show = computed({
  get: () => props.detailVisible,
  set: (value:boolean) => {
    emit('update:detailVisible', value);
  }
});

const detailLoading = ref(false);
const detailCourseOptions = ref<CourseOption[]>([]);

const submitDetailForm = async () => {
  if (!detailFormRef.value || !props.contractId) return;
  await detailFormRef.value.validate(async valid => {
    if (valid) {
      detailLoading.value = true;
      try {
        const payload: StudentContractDetailCreate = { ...detailForm };
        if (payload.detail_type !== 'lesson_price') {
           payload.course_id = null;
        }
        if (isEdit.value) {
          const res = assertApiSuccess(await updateContractDetail(props.contractId, props.detailData?.id || '', payload), '更新合約明細失敗');
          ElMessage.success(res.message || '更新合約明細成功');
        } else {
          const res = assertApiSuccess(await createContractDetail(props.contractId, payload), '新增合約明細失敗');
          ElMessage.success(res.message || '新增合約明細成功');
        }
        emit('addDetailFinish', props.contractId)
        show.value = false;
      } catch(err) {
        ElMessage.error(getApiErrorMessage(err, isEdit.value ? '更新合約明細失敗' : '新增合約明細失敗'));
      } finally {
        detailLoading.value = false;
        nextTick(() => {
          detailForm.detail_type = 'lesson_price';
          detailForm.course_id = '';
          detailForm.description = '';
          detailForm.amount = 0;
          detailForm.notes = '';
          isEdit.value = false;
        })
      }
    }
  });
};

watch(() => props.detailData, (newVal) => {
  if (newVal) {
    detailForm.detail_type = newVal.detail_type;
    detailForm.course_id = newVal.course_id;
    detailForm.description = newVal.description;
    detailForm.amount = newVal.amount;
    detailForm.notes = newVal.notes;
    isEdit.value = true;
  }
})

onMounted(async () => {
  if (props.studentId) {
    try {
      const cRes = assertApiSuccess(await getContractCourseOptions(props.studentId), '載入課程選單失敗');
      detailCourseOptions.value = cRes.data || [];
    } catch(err) {
      console.error(err);
      ElMessage.error(getApiErrorMessage(err, '載入課程選單失敗'));
    }
  }
})

</script>
