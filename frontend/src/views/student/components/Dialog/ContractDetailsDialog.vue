<template>
  <el-dialog v-model="show" :title="$t('studentAdmin.contractDetailDialog.title')" width="420px">
    <el-form :model="detailForm" :rules="detailRules" ref="detailFormRef" label-width="120px" label-position="top" @submit.prevent>
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item :label="$t('common.type')" prop="detail_type">
            <el-select v-model="detailForm.detail_type" class="w-full">
              <el-option :label="$t('studentAdmin.detailTypes.lessonPrice')" value="lesson_price"></el-option>
              <el-option :label="$t('studentAdmin.detailTypes.discount')" value="discount"></el-option>
              <el-option :label="$t('studentAdmin.detailTypes.compensation')" value="compensation"></el-option>
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item :label="$t('common.course')" prop="course_id" v-if="detailForm.detail_type === 'lesson_price'">
            <el-select v-model="detailForm.course_id" class="w-full" clearable>
              <el-option
                v-for="c in detailCourseOptions"
                :key="c.id"
                :label="formatCourseOptionLabel(c)"
                :value="c.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('studentAdmin.lessons')" prop="amount" v-else-if="detailForm.detail_type === 'compensation'">
            <el-input-number v-model="detailForm.amount" class="w-full"></el-input-number>
          </el-form-item>
          <el-form-item :label="$t('studentAdmin.amount')" prop="amount" v-else>
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
          <el-form-item :label="$t('studentAdmin.amount')" prop="amount" v-if="detailForm.detail_type === 'lesson_price'">
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
          <el-form-item :label="$t('studentAdmin.description')" prop="description">
            <el-input v-model="detailForm.description" maxlength="100" show-word-limit></el-input>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="24">
          <el-form-item :label="$t('common.note')">
            <el-input type="textarea" v-model="detailForm.notes"></el-input>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
    <template #footer>
      <el-button round @click="show = false">{{ $t('common.cancel') }}</el-button>
      <el-button round type="primary" :loading="detailLoading" @click="submitDetailForm">
        {{ isEdit ? $t('common.update') : $t('common.add') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { createContractDetail, type StudentContractDetailCreate, type CourseOption, getContractCourseOptions, updateContractDetail, type StudentContractDetail } from '@/api/studentContract';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { ref, computed, reactive, onMounted, watch, type PropType, nextTick } from 'vue'
import { useI18n } from 'vue-i18n';

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

const { t } = useI18n();

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

const formatCourseOptionLabel = (course: CourseOption) => {
  return course.course_code ? `${course.course_code} - ${course.course_name}` : course.course_name;
};

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
          const res = assertApiSuccess(await updateContractDetail(props.contractId, props.detailData?.id || '', payload), t('studentAdmin.contractDetailDialog.updateFailed'));
          ElMessage.success(res.message || t('studentAdmin.contractDetailDialog.updateSuccess'));
        } else {
          const res = assertApiSuccess(await createContractDetail(props.contractId, payload), t('studentAdmin.contractDetailDialog.createFailed'));
          ElMessage.success(res.message || t('studentAdmin.contractDetailDialog.createSuccess'));
        }
        emit('addDetailFinish', props.contractId)
        show.value = false;
      } catch(err) {
        ElMessage.error(getApiErrorMessage(err, isEdit.value ? t('studentAdmin.contractDetailDialog.updateFailed') : t('studentAdmin.contractDetailDialog.createFailed')));
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
      const cRes = assertApiSuccess(await getContractCourseOptions(props.studentId), t('studentAdmin.loadCourseOptionsFailed'));
      detailCourseOptions.value = cRes.data || [];
    } catch(err) {
      console.error(err);
      ElMessage.error(getApiErrorMessage(err, t('studentAdmin.loadCourseOptionsFailed')));
    }
  }
})

</script>
