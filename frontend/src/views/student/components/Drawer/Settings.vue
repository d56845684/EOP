<template>
  <div class="settings-container py-2">
    <template v-if="hasPermission('students.contracts')">
      <div class="flex justify-between items-center mb-5">
        <span class="text-13px font-500 color-[#1d2d44]">學生選課</span>
        <el-button v-if="hasPermission('students.edit')" type="primary" round size="small" @click="openCourseDialog('add')">
          <template #icon>
            <div class="i-hugeicons:add-square" />
          </template>
          新增選課
        </el-button>
      </div>
      <div v-loading="coursesLoading" class="preference-list">
        <el-card
          v-for="enrollment in studentCourses"
          :key="enrollment.id"
          shadow="never"
          body-class="py-3 px-4"
          class="mb-2 border-[#ebeef5]"
        >
          <div class="flex justify-between items-center">
            <div class="flex items-center gap-2">
              <el-tag type="primary" size="small" effect="light">{{ enrollment.course_code || '—' }}</el-tag>
              <span class="text-sm text-[#303133] font-500">{{ enrollment.course_name || enrollment.id }}</span>
            </div>
            <el-button link type="danger" size="small" @click="handleCourseDelete(enrollment.id)">移除</el-button>
          </div>
        </el-card>
        <div v-if="studentCourses.length === 0 && !coursesLoading" class="text-center text-gray-400 py-6 text-sm">
          尚未選擇任何課程
        </div>
      </div>

      <!-- Add Course Dialog -->
      <el-dialog
        v-model="courseDialogVisible"
        title="選課管理"
        width="540px"
        body-class="min-h-200px"
        append-to-body
        destroy-on-close
      >
        <el-row :gutter="16" class="h-full">
          <!-- Left: search & select -->
          <el-col :xs="24" :sm="10" class="mb-4 sm:mb-0">
            <div class="panel-label">搜尋課程</div>
            <el-select
              v-model="selectedCourseId"
              filterable
              placeholder="請輸入課程名稱搜尋"
              class="w-full"
              :loading="courseOptionsLoading"
              @change="handleCourseSelect"
            >
              <el-option
                v-for="opt in courseOptions"
                :key="opt.id"
                :label="opt.course_name + (opt.course_code ? ` (${opt.course_code})` : '')"
                :value="opt.id"
                :disabled="isInDialogList(opt.id)"
              />
            </el-select>
          </el-col>

          <!-- Right: all courses (enrolled + pending) -->
          <el-col :xs="24" :sm="14">
            <div class="panel-label">
              加入的課程
              <span class="panel-count">({{ dialogEnrolledCourses.length + pendingCourses.length }})</span>
            </div>
            <div class="pending-panel">
              <template v-if="dialogEnrolledCourses.length > 0 || pendingCourses.length > 0">
                <div class="flex flex-wrap gap-2 p-2">
                  <!-- Already enrolled: closable, deletes from server -->
                  <el-tag
                    v-for="item in dialogEnrolledCourses"
                    :key="'enrolled-' + item.id"
                    closable
                    type="success"
                    effect="light"
                    class="cursor-default"
                    :loading="deletingCourseIds.has(item.id)"
                    @close="handleDialogDeleteEnrolled(item)"
                  >
                    {{ item.course_name }}
                  </el-tag>
                  <!-- Pending new: closable, removes from local list -->
                  <el-tag
                    v-for="item in pendingCourses"
                    :key="'pending-' + item.id"
                    closable
                    type="primary"
                    effect="light"
                    class="cursor-default"
                    @close="removePending(item.id)"
                  >
                    {{ item.course_name }}
                    <span class="text-9px ml-0.5 opacity-60">待新增</span>
                  </el-tag>
                </div>
              </template>
              <el-empty v-else description="尚未選擇課程" :image-size="64" />
            </div>
          </el-col>
        </el-row>

        <template #footer>
          <span class="dialog-footer">
            <el-button round size="small" class="px-5! h-30px!" @click="courseDialogVisible = false">返回</el-button>
            <el-button
              type="primary" round size="small" class="px-5! h-30px!"
              :loading="courseSaving"
              :disabled="pendingCourses.length === 0"
              @click="handleConfirmAddCourses"
            >確認新增 ({{ pendingCourses.length }})</el-button>
          </span>
        </template>
      </el-dialog>

      <el-divider class="mt-10 mb-10" />
    </template>

    <template v-if="hasPermission('students.edit')">
      <div class="flex justify-between items-center mb-5">
        <span class="text-13px font-500 color-[#1d2d44]">學生教師偏好設定</span>
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
                  <label class="text-[#909399] text-xs font-500 mr-2">主要教師</label><span class="text-[#303133] font-500">{{ pref.primary_teacher_name }}</span>
                </div>
                <div v-else class="text-sm text-[#606266]">
                  <label class="text-[#909399] text-xs font-500 mr-2">最低教師等級</label><span class="text-[#303133] font-500">Lv. {{ pref.min_teacher_level }}</span>
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
      <el-dialog
        v-model="dialogVisible" 
        :title="dialogType === 'add' ? '新增偏好設定' : '編輯偏好設定'" 
        width="500px"
        body-class="min-h-200px"
        append-to-body 
        destroy-on-close
      >
        <el-form label-position="top" size="small">
          <el-form-item label="偏好類型">
            <el-radio-group v-model="formData.type" @change="handleTypeChange">
              <div class="flex gap-1">
                <el-radio value="specify_teacher" label="specify_teacher" border class="h-46px! w-160px">
                  <span class="flex flex-col gap-1.5 px-1">
                    <span class="leading-none">指定主要教師</span>
                    <span class="text-10px leading-none text-[#909399]">直接指定可預約的老師</span>
                  </span>
                </el-radio>
                <el-radio value="min_level" label="min_level" border class="h-46px! w-160px">
                  <span class="flex flex-col gap-1.5 px-1">
                    <span class="leading-none">設定最高等級</span>
                    <span class="text-10px leading-none text-[#909399]">依教師等級過濾</span>
                  </span>
                </el-radio>
              </div>
            </el-radio-group>
          </el-form-item>

          <template v-if="formData.type === 'specify_teacher'">
            <el-row>
              <el-col :span="24">
                <el-form-item label="主要教師">
                  <el-select 
                    v-if="dialogType === 'add'"
                    v-model="formData.primary_teacher_ids" 
                    placeholder="請選擇老師 (可複選)" 
                    filterable 
                    multiple
                    class="w-full"
                  >
                    <el-option 
                      v-for="teacher in teachers" 
                      :key="teacher.id" 
                      :label="teacher.name" 
                      :value="teacher.id" 
                      :disabled="existingPrimaryTeacherIds.has(teacher.id)"
                    />
                  </el-select>
                  <el-select 
                    v-else
                    v-model="formData.primary_teacher_id" 
                    placeholder="請選擇老師" 
                    filterable 
                    class="w-full"
                  >
                    <el-option label="不指定" :value="null" />
                    <el-option v-for="teacher in teachers" :key="teacher.id" :label="teacher.name" :value="teacher.id" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
          </template>

          <template v-else-if="formData.type === 'min_level'">
            <el-row>
              <el-col :span="10">
                <el-form-item label="適用課程">
                  <el-select v-model="formData.course_id" placeholder="請選擇課程" class="w-full" :loading="coursesLoading2">
                    <el-option label="全域課程" :value="null" />
                    <el-option v-for="course in courses" :key="course.id" :label="course.course_name" :value="course.id" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="10" :push="2">
                <el-form-item label="最低教師等級">
                  <template #label>
                    <span class="flex items-baseline gap-1.5">
                      <span>最高教師等級</span>
                      <span class="text-10px color-[#909399]">(最大值Lv.99)</span>
                    </span>
                  </template>
                  <el-input-number v-model="formData.min_teacher_level" :min="1" :max="99" :step="1" class="h-30px!" />
                </el-form-item>
              </el-col>
            </el-row>
          </template>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button round size="small" class="px-5! h-30px!" @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" round size="small" class="px-5! h-30px!" @click="handleSave" :loading="saving">確定</el-button>
          </span>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { usePermissionStore } from '@/stores/permission';
import {
  deleteStudentCourse,
  getCourseOptions,
  createStudentCourse,
  getStudentCoursesByStudentId,
  type CourseOption,
  type StudentCourseResponse
} from '@/api/studentCourse';
import { 
  getStudentTeacherPreferences, 
  createStudentTeacherPreference, 
  updateStudentTeacherPreference, 
  deleteStudentTeacherPreference,
  getPreferenceTeacherOptions,
  getPreferenceCourseOptions,
  type StudentTeacherPreferenceResponse,
  type StudentTeacherPreferenceCreate,
  type StudentTeacherPreferenceUpdate,
  type PreferenceTeacherOption,
  type PreferenceCourseOption,
} from '@/api/studentTeacherPreference';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
const props = defineProps<{
  studentId: string;
}>();

const permissionStore = usePermissionStore();
const hasPermission = (permission: string) => permissionStore.hasPermission(permission);

// ─── Student Courses State ───────────────────────────────────────────────────
const coursesLoading = ref(false);
const studentCourses = ref<StudentCourseResponse[]>([]);

const courseDialogVisible = ref(false);
const courseSaving = ref(false);

const selectedCourseId = ref<string | null>(null);
const courseOptions = ref<CourseOption[]>([]);
const courseOptionsLoading = ref(false);
const pendingCourses = ref<{ id: string; course_name: string }[]>([]);
// Courses shown in the dialog right panel (mirrors currently enrolled, for in-dialog deletes)
const dialogEnrolledCourses = ref<StudentCourseResponse[]>([]);
const deletingCourseIds = ref<Set<string>>(new Set());

// Set of enrolled course IDs for quick look-up (main list)
const enrolledCourseIds = computed(() => new Set(studentCourses.value.map((e) => e.course_id)));

/** Returns true if courseId is already enrolled or pending to be added */
const isInDialogList = (courseId: string): boolean => {
  return (
    dialogEnrolledCourses.value.some((e) => e.course_id === courseId) ||
    pendingCourses.value.some((p) => p.id === courseId)
  );
};

/** Legacy alias used by old code paths (kept for safety) */
const isPendingOrEnrolled = isInDialogList;

const loadStudentCourses = async () => {
  console.log(props.studentId)
  if (!props.studentId) return;
  coursesLoading.value = true;
  try {
    const res = assertApiSuccess(await getStudentCoursesByStudentId(props.studentId), '載入已選課程失敗');
    studentCourses.value = res.data || [];
  } catch (err) {
    console.error(err);
    ElMessage.error(getApiErrorMessage(err, '載入已選課程失敗'));
  } finally {
    coursesLoading.value = false;
  }
};

const loadCourseOptions = async () => {
  courseOptionsLoading.value = true;
  try {
    const res = assertApiSuccess(await getCourseOptions(), '載入課程選單失敗');
    courseOptions.value = res.data || [];
  } catch (err) {
    console.error(err);
    ElMessage.error(getApiErrorMessage(err, '載入課程選單失敗'));
  } finally {
    courseOptionsLoading.value = false;
  }
};

const openCourseDialog = (_type: 'add') => {
  // Snapshot current enrolled courses into the dialog list so user can delete inline
  dialogEnrolledCourses.value = [...studentCourses.value];
  pendingCourses.value = [];
  selectedCourseId.value = null;
  loadCourseOptions();
  courseDialogVisible.value = true;
};

/** Delete an already-enrolled course directly from within the dialog */
const handleDialogDeleteEnrolled = async (item: StudentCourseResponse) => {
  deletingCourseIds.value = new Set([...deletingCourseIds.value, item.id]);
  try {
    const res = assertApiSuccess(await deleteStudentCourse(item.id), '移除失敗');
    dialogEnrolledCourses.value = dialogEnrolledCourses.value.filter((e) => e.id !== item.id);
    // Also update main list immediately
    studentCourses.value = studentCourses.value.filter((e) => e.id !== item.id);
    ElMessage.success(res.message || '移除成功');
  } catch (err) {
    console.error(err);
    ElMessage.error(getApiErrorMessage(err, '移除失敗'));
  } finally {
    const next = new Set(deletingCourseIds.value);
    next.delete(item.id);
    deletingCourseIds.value = next;
  }
};

const handleCourseSelect = (courseId: string | null) => {
  if (!courseId) return;
  if (isPendingOrEnrolled(courseId)) {
    selectedCourseId.value = null;
    return;
  }
  const option = courseOptions.value.find((o) => o.id === courseId);
  if (option) {
    pendingCourses.value.push({ id: option.id, course_name: option.course_name });
  }
  // Clear select immediately so user can pick next course
  selectedCourseId.value = null;
};

const removePending = (courseId: string) => {
  pendingCourses.value = pendingCourses.value.filter((p) => p.id !== courseId);
};

const handleConfirmAddCourses = async () => {
  if (pendingCourses.value.length === 0) {
    ElMessage.warning('請先搜尋並選擇至少一門新課程');
    return;
  }
  courseSaving.value = true;
  try {
    const requests = pendingCourses.value.map((course) =>
      createStudentCourse({ student_id: props.studentId, course_id: course.id })
    );
    const results = await Promise.allSettled(requests);
    const failed = results.filter((r) => r.status === 'rejected' || (r.status === 'fulfilled' && r.value.success === false)).length;
    if (failed === 0) {
      ElMessage.success('選課新增成功');
    } else {
      ElMessage.warning(`已處理 ${results.length} 筆，其中 ${failed} 筆新增失敗，請確認是否重複選課`);
    }
    pendingCourses.value = [];
    courseDialogVisible.value = false;
    loadStudentCourses();
  } catch (err) {
    console.error(err);
    ElMessage.error('新增選課失敗');
  } finally {
    courseSaving.value = false;
  }
};

const handleCourseDelete = (enrollmentId: string) => {
  ElMessageBox.confirm('確定要移除此課程嗎？', '警告', {
    confirmButtonText: '確定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        const res = assertApiSuccess(await deleteStudentCourse(enrollmentId), '移除失敗');
        ElMessage.success(res.message || '移除成功');
        loadStudentCourses();
      } catch (err) {
        console.error(err);
        ElMessage.error(getApiErrorMessage(err, '移除失敗'));
      }
    })
    .catch(() => {});
};

// ─── Teacher Preferences State ───────────────────────────────────────────────
const loading = ref(false);
const preferences = ref<StudentTeacherPreferenceResponse[]>([]);

const existingPrimaryTeacherIds = computed(() => {
  const ids = new Set<string>();
  preferences.value.forEach(p => {
    if (p.primary_teacher_id) {
      ids.add(p.primary_teacher_id);
    }
  });
  return ids;
});

const dialogVisible = ref(false);
const dialogType = ref<'add' | 'edit'>('add');
const saving = ref(false);
const currentEditId = ref<string | null>(null);

const formData = reactive({
  type: 'specify_teacher' as 'specify_teacher' | 'min_level',
  primary_teacher_id: null as string | null,
  primary_teacher_ids: [] as string[],
  course_id: null as string | null,
  min_teacher_level: 1 as number | null
});

const teachers = ref<PreferenceTeacherOption[]>([]);
const courses = ref<PreferenceCourseOption[]>([]);

const loadPreferences = async () => {
  if (!props.studentId) return;
  loading.value = true;
  try {
    const res = assertApiSuccess(await getStudentTeacherPreferences(props.studentId), '載入偏好設定失敗');
    preferences.value = res.data || [];
  } catch (err) {
    console.error(err);
    ElMessage.error(getApiErrorMessage(err, '載入偏好設定失敗'));
  } finally {
    loading.value = false;
  }
};

const loadOptions = async () => {
  try {
    const [teacherRes, courseRes] = await Promise.all([
      getPreferenceTeacherOptions(),
      getPreferenceCourseOptions(props.studentId)
    ]);
    teachers.value = assertApiSuccess(teacherRes).data || [];
    courses.value = assertApiSuccess(courseRes).data || [];
  } catch (err) {
    console.error(err);
    ElMessage.error(getApiErrorMessage(err, '載入選項失敗'));
  }
};

const coursesLoading2 = ref(false);
const reloadCourseOptions = async () => {
  coursesLoading2.value = true;
  try {
    const res = assertApiSuccess(await getPreferenceCourseOptions(props.studentId), '載入課程選單失敗');
    courses.value = res.data || [];
  } catch (err) {
    console.error(err);
    ElMessage.error(getApiErrorMessage(err, '載入課程選單失敗'));
  } finally {
    coursesLoading2.value = false;
  }
};

const handleTypeChange = () => {
  if (formData.type === 'specify_teacher') {
    formData.course_id = null;
    formData.min_teacher_level = null;
  } else {
    formData.primary_teacher_id = null;
    formData.primary_teacher_ids = [];
    // defaults
    if (!formData.min_teacher_level) {
      formData.min_teacher_level = 1;
    }
    // Reload course options to get latest data
    reloadCourseOptions();
  }
};

const openDialog = (type: 'add' | 'edit', item?: StudentTeacherPreferenceResponse) => {
  dialogType.value = type;
  if (type === 'add') {
    currentEditId.value = null;
    formData.type = 'specify_teacher';
    formData.primary_teacher_id = null;
    formData.primary_teacher_ids = [];
    formData.course_id = null;
    formData.min_teacher_level = 1;
  } else if (item) {
    currentEditId.value = item.id;
    if (item.primary_teacher_id) {
      formData.type = 'specify_teacher';
      formData.primary_teacher_id = item.primary_teacher_id;
      formData.primary_teacher_ids = [];
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
  if (formData.type === 'specify_teacher') {
    if (dialogType.value === 'add' && formData.primary_teacher_ids.length === 0) {
      ElMessage.warning('請選擇主要教師');
      return;
    }
    if (dialogType.value === 'edit' && !formData.primary_teacher_id) {
      ElMessage.warning('請選擇主要教師');
      return;
    }
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
        primary_teacher_ids: formData.type === 'specify_teacher' ? formData.primary_teacher_ids : null,
      };
      const res = assertApiSuccess(await createStudentTeacherPreference(payload), '新增失敗');
      ElMessage.success(res.message || '新增偏好設定成功');
    } else if (currentEditId.value) {
      const payload: StudentTeacherPreferenceUpdate = {
        course_id: formData.type === 'min_level' ? formData.course_id : null,
        min_teacher_level: formData.type === 'min_level' ? formData.min_teacher_level : null,
        primary_teacher_id: formData.type === 'specify_teacher' ? formData.primary_teacher_id : null,
      };
      const res = assertApiSuccess(await updateStudentTeacherPreference(currentEditId.value, payload), '更新失敗');
      ElMessage.success(res.message || '更新偏好設定成功');
    }
    dialogVisible.value = false;
    loadPreferences();
  } catch (err) {
    console.error(err);
    ElMessage.error(getApiErrorMessage(err, dialogType.value === 'add' ? '新增失敗' : '更新失敗'));
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
      const res = assertApiSuccess(await deleteStudentTeacherPreference(id), '刪除失敗');
      ElMessage.success(res.message || '刪除成功');
      loadPreferences();
    } catch (err) {
      console.error(err);
      ElMessage.error(getApiErrorMessage(err, '刪除失敗'));
    }
  }).catch(() => {});
};

onMounted(() => {
  loadStudentCourses();
  loadPreferences();
  loadOptions();
});
</script>

<style scoped>
.settings-container {
  min-height: 200px;
  :deep(.el-card) {
    .el-card__body {
      padding: 12px;
    }
  }
}

.panel-label {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 10px;
}

.panel-count {
  font-weight: 400;
  color: #909399;
}

.pending-panel {
  min-height: 120px;
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  overflow-y: auto;
  max-height: 240px;
}
</style>
