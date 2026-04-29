<template>
  <el-drawer v-model="isVisible" :title="drawerTitle" size="550px" @closed="handleClosed">
    <div v-loading="loading" class="min-h-full">
      <!-- Basic Info Form ------------------------------------------------>
      <el-form ref="basicFormRef" :model="basicForm" :rules="basicRules" size="small" label-position="top" label-width="120px">
        <el-row>
          <el-col :span="24">
            <!-- Avatar --------------------------------------------------------->
            <div class="flex items-center gap-4 mb-6">
              <div class="relative group w-20 h-20 flex-shrink-0">
                <el-image
                  :src="uploadAvatar.url || avatarUrl || ''"
                  fit="cover"
                  class="w-20 h-20 rounded-full border-2 border-[#e4e6ef] object-cover"
                >
                  <template #error>
                    <div class="w-20 h-20 rounded-full bg-[#f3f4f8] flex items-center justify-center">
                      <div class="i-hugeicons:user text-3xl color-[#b5b5c3]" />
                    </div>
                  </template>
                </el-image>
                <el-upload
                  ref="avatarUploadRef"
                  v-model:file-list="avatarFileList"
                  class="absolute inset-0 rounded-full overflow-hidden"
                  action="#"
                  :limit="1"
                  :multiple="false"
                  accept=".jpg,.jpeg,.png,.webp"
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="handleUploadAvatar"
                  :on-exceed="handleAvatarExceed"
                >
                  <div
                    class="w-20 h-20 rounded-full flex flex-col items-center justify-center
                          bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                  >
                    <div v-if="uploadingAvatar" class="i-hugeicons:loading-03 animate-spin text-white text-xl" />
                    <template v-else>
                      <div class="i-hugeicons:camera-02 text-white text-xl" />
                      <span class="text-white text-10px mt-1">{{ $t('teacherDetailDrawer.editAvatar') }}</span>
                    </template>
                  </div>
                </el-upload>
              </div>
              <div class="flex flex-col gap-1 text-xs color-[#7e8299]">
                <span>{{ $t('teacherDetailDrawer.supportedFormats') }}</span>
                <span>{{ $t('teacherDetailDrawer.sizeLimit') }}</span>
              </div>
            </div>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="10">
            <el-form-item :label="$t('common.name')" prop="name">
              <el-input v-model="basicForm.name" class="h-30px!" />
            </el-form-item>
          </el-col>
          <el-col :span="10" :push="2">
            <el-form-item :label="$t('common.phone')" prop="phone">
              <el-input v-model="basicForm.phone" class="h-30px!" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="14">
            <el-form-item :label="$t('common.email')" prop="email">
              <el-input v-model="basicForm.email" class="h-30px!" />
            </el-form-item>
          </el-col>
          <el-col :span="8" :push="2">
            <el-form-item :label="$t('teacherDetailDrawer.teacherLevel')" prop="teacher_level">
              <el-input-number v-model="basicForm.teacher_level" :min="1" class="h-30px! w-128px!" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item :label="$t('common.address')" prop="address">
          <el-input v-model="basicForm.address" class="h-30px!" />
        </el-form-item>
        <el-form-item :label="$t('teacher.introduction')" prop="bio">
          <el-input v-model="basicForm.bio" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" round size="small" class="h-30px! px-5!" :loading="saving" @click="saveBasicInfo">
            {{ $t('common.save') }}
          </el-button>
        </el-form-item>
      </el-form>

      <template v-if="isEdit">
        <!-- Teacher Details ---------------------------------------------- -->
        <el-divider content-position="left" class="mt-8 mb-2">
          <span class="text-13px color-[#1d2d44]">{{ $t('teacherDetailDrawer.relatedInfo') }}</span>
        </el-divider>
        <div class="flex justify-end">
          <el-button type="primary" round text size="small" class="mb-2" @click="openDetailDialog()">
            <template #icon><div class="i-hugeicons:add-square" /></template>
            {{ $t('teacherDetailDrawer.addInfo') }}
          </el-button>
        </div>

        <!-- Detail list -->
        <div class="mb-2 flex flex-col gap-2">
          <div
            v-for="item in teacherDetails"
            :key="item.id"
            class="flex items-start justify-between px-3 py-2 rounded-lg border border-[#ebedf3] bg-white hover:bg-[#f8f9fb] transition-colors"
          >
            <!-- Left -->
            <div class="flex flex-col gap-0.5 min-w-0 mr-3">
              <div class="flex items-center gap-1.5 mb-0.5">
                <el-tag size="small" :type="detailTagType(item.detail_type)" class="text-10px px-5px h-16px!">
                  {{ DETAIL_TYPE_MAP[item.detail_type] || item.detail_type }}
                </el-tag>
              </div>
              <span class="text-13px text-[#3f4254cc]">{{ item.content || '-' }}</span>
              <div class="flex gap-3 mt-0.5">
                <span v-if="item.issue_date" class="text-11px color-gray-400">{{ $t('teacherDetailDrawer.issuedAt') }}：{{ item.issue_date }}</span>
                <span v-if="item.expiry_date" class="text-11px color-gray-400">{{ $t('teacherDetailDrawer.expiresAt') }}：{{ item.expiry_date }}</span>
              </div>
              <div v-if="item.file_name" class="text-11px color-[#626aef] mt-0.5 flex items-center gap-1">
                <div class="i-hugeicons:file-02" />{{ item.file_name }}
              </div>
            </div>
            <!-- Right -->
            <div class="flex items-center gap-1 flex-shrink-0">
              <el-tooltip :content="$t('common.edit')" effect="dark">
                <el-button link type="primary" @click="openDetailDialog(item)">
                  <div class="i-hugeicons:edit-02" />
                </el-button>
              </el-tooltip>
              <el-tooltip :content="$t('common.delete')" effect="dark">
                <el-button link type="danger" @click="handleDeleteDetail(item.id)">
                  <div class="i-hugeicons:delete-02" />
                </el-button>
              </el-tooltip>
            </div>
          </div>
          <div v-if="!teacherDetails.length" class="text-center text-12px color-gray-400 py-4">{{ $t('teacherDetailDrawer.noDetails') }}</div>
        </div>
      </template>
    </div>
  </el-drawer>

  <!-- Detail Dialog ---------------------------------------------------- -->
  <el-dialog
    v-model="showDetailDialog"
    :title="editingDetailId ? $t('teacherDetailDrawer.editInfoTitle') : $t('teacherDetailDrawer.addInfoTitle')"
    width="440px"
    top="12vh"
    append-to-body
    destroy-on-close
    @closed="resetDetailForm"
  >
    <el-form ref="detailFormRef" :model="detailForm" :rules="detailRules" label-position="top" size="small">
      <!-- 類型 -->
      <el-row>
        <el-col :span="10">
          <el-form-item :label="$t('teacherDetailDrawer.detailType')" prop="detail_type">
            <el-select v-model="detailForm.detail_type" :placeholder="$t('teacherDetailDrawer.selectDetailType')" class="w-full">
              <el-option :label="$t('teacherDetailDrawer.types.qualification')" value="qualification" />
              <el-option :label="$t('teacherDetailDrawer.types.certificate')" value="certificate" />
              <el-option :label="$t('teacherDetailDrawer.types.video')" value="video" />
              <el-option :label="$t('teacherDetailDrawer.types.experience')" value="experience" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="24">
          <!-- 內容 -->
          <el-form-item :label="detailForm.detail_type === 'video' ? $t('teacherDetailDrawer.videoLabel') : $t('teacherDetailDrawer.contentLabel')" prop="content">
            <el-input 
              v-model="detailForm.content"
              type="textarea" :rows="4" 
              :placeholder="detailForm.detail_type === 'video' ? $t('teacherDetailDrawer.videoPlaceholder') : $t('teacherDetailDrawer.contentPlaceholder')"
            />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="11">
          <!-- 發證日期：僅 certificate -->
          <el-form-item v-if="detailForm.detail_type === 'certificate'" :label="$t('teacherDetailDrawer.issueDate')" prop="issue_date">
            <el-date-picker
              v-model="detailForm.issue_date"
              type="date"
              value-format="YYYY-MM-DD"
              :placeholder="$t('teacherDetailDrawer.selectIssueDate')"
              class="w-full! h-30px!"
            />
          </el-form-item>
        </el-col>
        <el-col :span="11" :push="2">
          <!-- 到期日期：僅 certificate -->
          <el-form-item v-if="detailForm.detail_type === 'certificate'" :label="$t('teacherDetailDrawer.expiryDate')" prop="expiry_date">
            <el-date-picker
              v-model="detailForm.expiry_date"
              type="date"
              value-format="YYYY-MM-DD"
              :placeholder="$t('teacherDetailDrawer.selectExpiryDate')"
              class="w-full! h-30px!"
            />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col>
          <!-- 上傳檔案：certificate 或 video -->
          <el-form-item
            v-if="detailForm.detail_type === 'certificate'"
            :label="$t('teacherDetailDrawer.uploadFile')"
            class="w-full upload-field"
          >
            <el-upload
              action="#"
              :limit="1"
              :multiple="false"
              :auto-upload="false"
              :show-file-list="true"
              accept=".pdf, .jpg, .jpeg, .png"
              :on-change="(f: any) => { detailPendingFile = f.raw || null }"
              :on-remove="() => { detailPendingFile = null }"
            >
              <el-button size="small" round plain>
                <template #icon><div class="i-hugeicons:upload-01" /></template>
                {{ $t('teacherDetailDrawer.chooseFile') }}
              </el-button>
            </el-upload>
            <div v-if="existingFileName && !detailPendingFile" class="text-11px color-[#626aef] mt-1 flex items-center gap-1">
              <div class="i-hugeicons:file-02" />
              <span class="text-wrap break-all">{{ existingFileName }}</span>
            </div>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
    <template #footer>
      <div class="flex justify-end gap-2">
        <el-button round size="small" class="py-3!" @click="showDetailDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" round size="small" class="py-3!" :loading="savingDetail" @click="saveDetail">
          {{ editingDetailId ? $t('common.save') : $t('teacherDetailDrawer.addAction') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type UploadInstance, type UploadUserFile } from 'element-plus';
import { getTeacherById, createTeacher, updateTeacher, type TeacherCreate, type TeacherUpdate } from '@/api/teacher';
import {
  getTeacherDetails,
  createTeacherDetail,
  updateTeacherDetail,
  deleteTeacherDetail,
  type TeacherDetail,
} from '@/api/teacherDetails';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { uploadTeacherAvatar, uploadDetailFile } from '@/utils/upload';

type DetailType = 'qualification' | 'certificate' | 'video' | 'experience';
const { t } = useI18n();

const DETAIL_TYPE_MAP = computed<Record<string, string>>(() => ({
  qualification: t('teacherDetailDrawer.types.qualification'),
  certificate: t('teacherDetailDrawer.types.certificate'),
  video: t('teacherDetailDrawer.types.video'),
  experience: t('teacherDetailDrawer.types.experience'),
}));

const detailTagType = (type: string) => {
  if (type === 'qualification') return 'primary';
  if (type === 'certificate') return 'success';
  if (type === 'video') return 'warning';
  if (type === 'experience') return 'info';
  return '';
};

const props = defineProps<{
  modelValue: boolean;
  teacherId: string | null;
}>();

const emit = defineEmits(['update:modelValue', 'saved']);

const isVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const isEdit = computed(() => !!props.teacherId);

// UI State
const loading = ref(false);
const saving = ref(false);
const uploadingAvatar = ref(false);
const avatarUrl = ref<string | null>(null);
const avatarUploadRef = ref<UploadInstance>();
const avatarFileList = ref<UploadUserFile[]>([]);

const drawerTitle = computed(() => {
  if (!isEdit.value) return t('teacherDetailDrawer.createTitle');
  if (basicForm.teacher_no && basicForm.name) return `${basicForm.teacher_no} - ${basicForm.name}`;
  return basicForm.name || t('teacherDetailDrawer.fallbackTitle');
});

// --- Basic Info Form ---
const basicFormRef = ref<FormInstance>();
const basicForm = reactive<TeacherUpdate & { teacher_no?: string }>({
  teacher_no: '',
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

// --- Teacher Details ---
const teacherDetails = ref<TeacherDetail[]>([]);
const showDetailDialog = ref(false);
const savingDetail = ref(false);
const editingDetailId = ref<string | null>(null);
const detailPendingFile = ref<File | null>(null);
const existingFileName = ref<string | null>(null);
const detailFormRef = ref<FormInstance>();

const detailForm = reactive({
  detail_type: 'qualification' as DetailType,
  content: '',
  issue_date: null as string | null,
  expiry_date: null as string | null,
});

const detailRules = reactive<FormRules>({
  detail_type: [{ required: true, message: t('teacherDetailDrawer.typeRequired'), trigger: 'change' }],
});

const openDetailDialog = (item?: TeacherDetail) => {
  if (item) {
    editingDetailId.value = item.id;
    detailForm.detail_type = (item.detail_type as DetailType) || 'qualification';
    detailForm.content = item.content || '';
    detailForm.issue_date = item.issue_date || null;
    detailForm.expiry_date = item.expiry_date || null;
    existingFileName.value = item.file_name || null;
  } else {
    editingDetailId.value = null;
    detailForm.detail_type = 'qualification';
    detailForm.content = '';
    detailForm.issue_date = null;
    detailForm.expiry_date = null;
    existingFileName.value = null;
  }
  detailPendingFile.value = null;
  showDetailDialog.value = true;
};

const resetDetailForm = () => {
  detailFormRef.value?.resetFields();
  editingDetailId.value = null;
  detailPendingFile.value = null;
  existingFileName.value = null;
  detailForm.detail_type = 'qualification';
  detailForm.content = '';
  detailForm.issue_date = null;
  detailForm.expiry_date = null;
};

const saveDetail = async () => {
  const tId = props.teacherId;
  if (!detailFormRef.value || !tId) return;
  await detailFormRef.value.validate(async (valid) => {
    if (!valid) return;
    savingDetail.value = true;
    try {
      let savedId: string;
      if (editingDetailId.value) {
        // Update
        const res = await updateTeacherDetail(editingDetailId.value, {
          content: detailForm.content || null,
          issue_date: detailForm.detail_type === 'certificate' ? detailForm.issue_date : null,
          expiry_date: detailForm.detail_type === 'certificate' ? detailForm.expiry_date : null,
        });
        savedId = assertApiSuccess(res, t('teacherDetailDrawer.updateDetailFailed')).data.id;
        ElMessage.success(res.message || t('teacherDetailDrawer.detailUpdated'));
      } else {
        // Create
        const res = await createTeacherDetail({
          teacher_id: tId,
          detail_type: detailForm.detail_type,
          content: detailForm.content || null,
          issue_date: detailForm.detail_type === 'certificate' ? detailForm.issue_date : null,
          expiry_date: detailForm.detail_type === 'certificate' ? detailForm.expiry_date : null,
        });
        savedId = assertApiSuccess(res, t('teacherDetailDrawer.createDetailFailed')).data.id;
        ElMessage.success(res.message || t('teacherDetailDrawer.detailCreated'));
      }

      // Upload file if pending
      if (detailPendingFile.value && (detailForm.detail_type === 'certificate' || detailForm.detail_type === 'video')) {
        try {
          await uploadDetailFile(savedId, detailPendingFile.value);
        } catch (e) {
          ElMessage.warning(t('teacherDetailDrawer.detailUploadWarning'));
        }
      }

      showDetailDialog.value = false;
      await loadDetails();
    } catch (e) {
      console.error(e);
      ElMessage.error(getApiErrorMessage(e, editingDetailId.value ? t('teacherDetailDrawer.updateDetailFailed') : t('teacherDetailDrawer.createDetailFailed')));
    } finally {
      savingDetail.value = false;
    }
  });
};

const handleDeleteDetail = async (detailId: string) => {
  try {
    await ElMessageBox.confirm(t('teacherDetailDrawer.deleteDetailConfirm'), t('teacherDetailDrawer.deleteDetailTitle'), {
      type: 'warning',
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
    });
    const res = assertApiSuccess(await deleteTeacherDetail(detailId), t('teacherDetailDrawer.deleteDetailFailed'));
    ElMessage.success(res.message || t('teacherDetailDrawer.detailDeleted'));
    await loadDetails();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(getApiErrorMessage(e, t('teacherDetailDrawer.deleteFailed')));
  }
};

// --- Data Loading ---
const loadDetails = async () => {
  const tId = props.teacherId;
  if (!tId) return;
  try {
    const res = assertApiSuccess(await getTeacherDetails(tId), t('teacherDetailDrawer.loadDetailFailed'));
    teacherDetails.value = res.data || [];
  } catch (e) {
    ElMessage.error(getApiErrorMessage(e, t('teacherDetailDrawer.loadDetailFailed')));
  }
};

const fetchData = async () => {
  if (!props.teacherId) return;
  loading.value = true;
  try {
    const [teacherRes] = await Promise.all([
      getTeacherById(props.teacherId),
      loadDetails(),
    ]);
    const target = assertApiSuccess(teacherRes, t('teacherDetailDrawer.loadTeacherFailed')).data;
    if (target) {
      basicForm.teacher_no = target.teacher_no;
      basicForm.name = target.name;
      basicForm.email = target.email;
      basicForm.phone = target.phone || '';
      basicForm.address = target.address || '';
      basicForm.bio = target.bio || '';
      basicForm.teacher_level = target.teacher_level;
      avatarUrl.value = target.avatar_url || null;
    }
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('teacherDetailDrawer.loadTeacherFailed')));
  } finally {
    loading.value = false;
  }
};

const uploadAvatar = ref({
  file: null as any,
  url: '',
})

const handleUploadAvatar = (uploadFile: any) => {
  const MAX_SIZE_MB = 2;
  if (uploadFile.raw.size > MAX_SIZE_MB * 1024 * 1024) {
    ElMessage.warning(t('teacherDetailDrawer.avatarSizeWarning', { size: MAX_SIZE_MB }));
    return;
  }
  uploadAvatar.value.file = uploadFile;
  uploadAvatar.value.url = URL.createObjectURL(uploadFile.raw);
  if (isEdit.value) {
    handleAvatarChange(uploadFile);
  }
}

const handleAvatarExceed = () => {
  avatarUploadRef.value?.clearFiles();
};

const handleAvatarChange = async (uploadFile: any, teacherId?: string) => {
  const tId = props.teacherId || teacherId;
  if (!tId || !uploadFile.raw) return;
  uploadingAvatar.value = true;
  try {
    await uploadTeacherAvatar(tId, uploadFile.raw);
    const res = assertApiSuccess(await getTeacherById(tId), t('teacherDetailDrawer.loadTeacherFailed'));
    avatarUrl.value = res.data.avatar_url || null;
    ElMessage.success(t('teacherDetailDrawer.avatarUpdated'));
    if (isEdit.value) {
      emit('saved');
    }
  } catch (e) {
    console.error(e);
    ElMessage.error(getApiErrorMessage(e, t('teacherDetailDrawer.avatarUploadFailed')));
  } finally {
    uploadingAvatar.value = false;
    avatarFileList.value = [];
    avatarUploadRef.value?.clearFiles();
  }
};

const saveBasicInfo = async () => {
  if (!basicFormRef.value) return;
  await basicFormRef.value.validate(async (valid) => {
    if (valid) {
      const tId = props.teacherId;
      saving.value = true;
      try {
        if (isEdit.value && tId) {
          const res = assertApiSuccess(await updateTeacher(tId, basicForm), t('teacherDetailDrawer.saveFailed'));
          ElMessage.success(res.message || t('teacherDetailDrawer.basicSaved'));
        } else {
          const { teacher_no: _teacherNo, ...createPayload } = basicForm;
          const res = assertApiSuccess(await createTeacher(createPayload as TeacherCreate), t('teacherDetailDrawer.createdFailed'));
          ElMessage.success(res.message || t('teacherDetailDrawer.basicCreated'));
          if (uploadAvatar.value.file) {
            await handleAvatarChange(uploadAvatar.value.file, res.data.id);
          }
          isVisible.value = false;
        }
        emit('saved');
      } catch (e) {
        ElMessage.error(getApiErrorMessage(e, isEdit.value ? t('teacherDetailDrawer.saveFailed') : t('teacherDetailDrawer.createdFailed')));
      } finally {
        saving.value = false;
      }
    }
  });
};

const handleClosed = () => {
  avatarUrl.value = null;
  teacherDetails.value = [];
  uploadAvatar.value.file = null;
  uploadAvatar.value.url = '';
  avatarFileList.value = [];
  avatarUploadRef.value?.clearFiles();
  basicFormRef.value?.resetFields();
  basicForm.teacher_no = '';
  basicForm.name = '';
  basicForm.email = '';
  basicForm.phone = '';
  basicForm.address = '';
  basicForm.bio = '';
  basicForm.teacher_level = 1;
};

watch(() => props.modelValue, (val) => {
  if (val && props.teacherId) {
    fetchData();
  }
});
</script>

<style scoped>
:deep(.upload-field) {
  .el-form-item__content {
    & > div {
      width: 100%;
      .el-upload-list {
        width: 60%;
        .el-upload-list__item {
          &:hover {
            border-radius: 5px;
          }
          .el-upload-list__item-file-name {
            max-width: calc(100% - 20px);
          }
        }
      }
    }
  }
}
</style>
