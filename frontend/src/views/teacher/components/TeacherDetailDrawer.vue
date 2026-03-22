<template>
  <el-drawer v-model="isVisible" :title="drawerTitle" size="600px" @closed="handleClosed">
    <div v-loading="loading" class="h-full">
        <!-- Tab 1: Basic Info -->
      <el-form ref="basicFormRef" :model="basicForm" :rules="basicRules" label-position="top" label-width="120px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('common.name')" prop="name">
              <el-input v-model="basicForm.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('common.email')" prop="email">
              <el-input v-model="basicForm.email" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('common.phone')" prop="phone">
              <el-input v-model="basicForm.phone" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="'Teacher Level'" prop="teacher_level">
              <el-input-number v-model="basicForm.teacher_level" :min="1" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item :label="$t('common.address')" prop="address">
          <el-input v-model="basicForm.address" />
        </el-form-item>
        <el-form-item :label="$t('teacher.introduction')" prop="bio">
          <el-input v-model="basicForm.bio" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="saveBasicInfo">{{ $t('common.save') }}</el-button>
        </el-form-item>
      </el-form>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { getTeacherList, updateTeacher, type TeacherUpdate } from '@/api/teacher';
import { getCourseOptions, type CourseOption } from '@/api/teacherContract';

const props = defineProps<{
  modelValue: boolean;
  teacherId: string | null;
}>();

const emit = defineEmits(['update:modelValue', 'saved']);

const isVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

// UI State
const loading = ref(false);
const saving = ref(false);
const teacherName = ref('');

const drawerTitle = computed(() => {
  return teacherName.value ? `${teacherName.value}` : 'Teacher Details';
});

// --- Tab 1: Basic Info ---
const basicFormRef = ref<FormInstance>();
const basicForm = reactive<TeacherUpdate>({
  name: '',
  email: '',
  phone: '',
  address: '',
  bio: '',
  teacher_level: 1
});

const basicRules = reactive<FormRules>({
  name: [{ required: true, message: 'Name is required', trigger: 'blur' }],
  email: [{ required: true, message: 'Email is required', trigger: 'blur', type: 'email' }]
});

// Course Rates
const courseOptions = ref<CourseOption[]>([]);

// --- Methods ---

const fetchData = async () => {
  if (!props.teacherId) return;
  loading.value = true;
  try {
    // 1. Fetch Teacher Basic Info
    // Since we don't have a GET /teachers/{id} strictly defined in the snippet, we fetch from list.
    // In a real scenario there might be a getTeacher(id).
    // Assuming backend returns it in the list endpoint.
    const res = await getTeacherList({ search: props.teacherId }); // pseudo fetch. Or pass full teacher object from parent
    const target = res.data.find(t => t.id === props.teacherId);
    if (target) {
      teacherName.value = target.name;
      basicForm.name = target.name;
      basicForm.email = target.email;
      basicForm.phone = target.phone || '';
      basicForm.address = target.address || '';
      basicForm.bio = target.bio || '';
      basicForm.teacher_level = target.teacher_level;
    }

    // 2. Fetch Options
    if (courseOptions.value.length === 0) {
      const optRes = await getCourseOptions();
      if (optRes.success) courseOptions.value = optRes.data;
    }

    // 3. Fetch Contracts
  } catch (error) {
    ElMessage.error('Failed to load teacher data');
  } finally {
    loading.value = false;
  }
};

const saveBasicInfo = async () => {
  const tId = props.teacherId;
  if (!basicFormRef.value || !tId) return;
  await basicFormRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true;
      try {
        await updateTeacher(tId, basicForm);
        ElMessage.success('Basic info updated successfully');
        teacherName.value = basicForm.name || teacherName.value;
        emit('saved');
      } catch (e) {
        ElMessage.error('Failed to update basic info');
      } finally {
        saving.value = false;
      }
    }
  });
};

const handleClosed = () => {
  teacherName.value = '';
};

watch(() => props.modelValue, (val) => {
  if (val && props.teacherId) {
    fetchData();
  }
});
</script>

<style scoped>
.h-full { height: 100%; }
.flex-col { flex-direction: column; }
</style>
