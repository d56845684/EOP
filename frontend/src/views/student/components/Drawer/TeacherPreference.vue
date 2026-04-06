<template>
  <div class="teacher-preference-container py-2">
    <div class="flex justify-end items-center mb-4">
      <el-button type="primary" round size="small" @click="openDialog('add')">
        <template #icon>
          <div class="i-hugeicons:add-square" />
        </template>
        新增偏好設定
      </el-button>
    </div>

    <!-- Main display area -->
    <div v-loading="loading" class="preference-list">
      <el-card
        v-for="pref in preferences" 
        :key="pref.id" 
        shadow="never" 
        body-class="py-3 px-4" 
        class="mb-2 border-[#ebeef5]"
      >
        <div class="flex justify-between items-start">
          <div>
             <el-tag :type="pref.primary_teacher_id ? 'primary' : 'success'" size="small" effect="light">
               {{ pref.primary_teacher_id ? '指定教師' : (pref.course_name || '全域課程') }}
             </el-tag>
             <div class="mt-2">
              <div v-if="pref.primary_teacher_id" class="text-sm text-[#606266]">
                <label class="text-[#909399] text-xs font-500 mr-2">主要教師</label><span>{{ pref.primary_teacher_name }}</span>
              </div>
              <div v-else class="text-sm text-[#606266]">
                <label class="text-[#909399] text-xs font-500 mr-2">最低教師等級</label><span>Lv. {{ pref.min_teacher_level }}</span>
              </div>
             </div>
          </div>
          <div class="flex gap-2">
            <el-button link type="primary" size="small" @click="openDialog('edit', pref)">編輯</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(pref.id)">刪除</el-button>
          </div>
        </div>
      </el-card>
      <div v-if="preferences.length === 0 && !loading" class="text-center text-gray-400 py-8 text-sm">
        暫無偏好設定
      </div>
    </div>

    <!-- Dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogType === 'add' ? '新增偏好設定' : '編輯偏好設定'" width="500px" append-to-body destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="偏好類型">
          <el-radio-group v-model="formData.type" @change="handleTypeChange">
            <div class="flex flex-col gap-2">
              <el-radio value="specify_teacher" label="specify_teacher">
                直接指定可預約的老師
              </el-radio>
              <el-radio value="min_level" label="min_level">
                依教師等級過濾
              </el-radio>
            </div>
          </el-radio-group>
        </el-form-item>

        <template v-if="formData.type === 'specify_teacher'">
          <el-form-item label="主要教師">
            <el-select v-model="formData.primary_teacher_id" placeholder="請選擇老師" filterable class="w-full">
              <el-option v-for="teacher in teachers" :key="teacher.id" :label="teacher.name" :value="teacher.id" />
            </el-select>
          </el-form-item>
        </template>

        <template v-else-if="formData.type === 'min_level'">
          <el-form-item label="適用課程">
            <el-select v-model="formData.course_id" placeholder="請選擇課程" class="w-full">
              <el-option label="全域課程" :value="null" />
              <el-option v-for="course in courses" :key="course.id" :label="course.course_name" :value="course.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="最低教師等級">
            <el-input-number v-model="formData.min_teacher_level" :min="1" :step="1" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSave" :loading="saving">確定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { 
  getStudentTeacherPreferences, 
  createStudentTeacherPreference, 
  updateStudentTeacherPreference, 
  deleteStudentTeacherPreference,
  type StudentTeacherPreferenceResponse,
  type StudentTeacherPreferenceCreate,
  type StudentTeacherPreferenceUpdate
} from '@/api/studentTeacherPreference';
import { getBookingTeacherOptions, getBookingCourseOptions, type BookingTeacherOption, type BookingCourseOption } from '@/api/booking';
const props = defineProps<{
  studentId: string;
}>();

const loading = ref(false);
const preferences = ref<StudentTeacherPreferenceResponse[]>([]);

const dialogVisible = ref(false);
const dialogType = ref<'add' | 'edit'>('add');
const saving = ref(false);
const currentEditId = ref<string | null>(null);

const formData = reactive({
  type: 'specify_teacher' as 'specify_teacher' | 'min_level',
  primary_teacher_id: null as string | null,
  course_id: null as string | null,
  min_teacher_level: 1 as number | null
});

const teachers = ref<BookingTeacherOption[]>([]);
const courses = ref<BookingCourseOption[]>([]);

const loadPreferences = async () => {
  if (!props.studentId) return;
  loading.value = true;
  try {
    const res = await getStudentTeacherPreferences(props.studentId);
    preferences.value = res.data || [];
  } catch (err) {
    console.error(err);
    ElMessage.error('載入偏好設定失敗');
  } finally {
    loading.value = false;
  }
};

const loadOptions = async () => {
  try {
    const [teacherRes, courseRes] = await Promise.all([
      getBookingTeacherOptions({ student_id: props.studentId }),
      getBookingCourseOptions()
    ]);
    teachers.value = teacherRes.data || [];
    courses.value = courseRes.data || [];
  } catch (err) {
    console.error(err);
  }
};

const handleTypeChange = () => {
  if (formData.type === 'specify_teacher') {
    formData.course_id = null;
    formData.min_teacher_level = null;
  } else {
    formData.primary_teacher_id = null;
    // defaults
    if (!formData.min_teacher_level) {
      formData.min_teacher_level = 1;
    }
  }
};

const openDialog = (type: 'add' | 'edit', item?: StudentTeacherPreferenceResponse) => {
  dialogType.value = type;
  if (type === 'add') {
    currentEditId.value = null;
    formData.type = 'specify_teacher';
    formData.primary_teacher_id = null;
    formData.course_id = null;
    formData.min_teacher_level = 1;
  } else if (item) {
    currentEditId.value = item.id;
    if (item.primary_teacher_id) {
      formData.type = 'specify_teacher';
      formData.primary_teacher_id = item.primary_teacher_id;
      formData.course_id = null;
      formData.min_teacher_level = null;
    } else {
      formData.type = 'min_level';
      formData.primary_teacher_id = null;
      formData.course_id = item.course_id;
      formData.min_teacher_level = item.min_teacher_level || 1;
    }
  }
  dialogVisible.value = true;
};

const handleSave = async () => {
  if (formData.type === 'specify_teacher' && !formData.primary_teacher_id) {
    ElMessage.warning('請選擇主要教師');
    return;
  }
  if (formData.type === 'min_level' && !formData.min_teacher_level) {
    ElMessage.warning('請輸入最低教師等級');
    return;
  }

  saving.value = true;
  try {
    if (dialogType.value === 'add') {
      const payload: StudentTeacherPreferenceCreate = {
        student_id: props.studentId,
        course_id: formData.type === 'min_level' ? formData.course_id : null,
        min_teacher_level: formData.type === 'min_level' ? formData.min_teacher_level : null,
        primary_teacher_id: formData.type === 'specify_teacher' ? formData.primary_teacher_id : null,
      };
      await createStudentTeacherPreference(payload);
      ElMessage.success('新增偏好設定成功');
    } else if (currentEditId.value) {
      const payload: StudentTeacherPreferenceUpdate = {
        course_id: formData.type === 'min_level' ? formData.course_id : null,
        min_teacher_level: formData.type === 'min_level' ? formData.min_teacher_level : null,
        primary_teacher_id: formData.type === 'specify_teacher' ? formData.primary_teacher_id : null,
      };
      await updateStudentTeacherPreference(currentEditId.value, payload);
      ElMessage.success('更新偏好設定成功');
    }
    dialogVisible.value = false;
    loadPreferences();
  } catch (err) {
    console.error(err);
    ElMessage.error(dialogType.value === 'add' ? '新增失敗' : '更新失敗');
  } finally {
    saving.value = false;
  }
};

const handleDelete = (id: string) => {
  ElMessageBox.confirm('確定要刪除此偏好設定嗎？', '警告', {
    confirmButtonText: '確定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try {
      await deleteStudentTeacherPreference(id);
      ElMessage.success('刪除成功');
      loadPreferences();
    } catch (err) {
      console.error(err);
      ElMessage.error('刪除失敗');
    }
  }).catch(() => {});
};

onMounted(() => {
  loadPreferences();
  loadOptions();
});
</script>

<style scoped>
.teacher-preference-container {
  min-height: 200px;
  :deep(.el-card) {
    &__body {
      padding: 12px;
    }
  }
}
</style>
