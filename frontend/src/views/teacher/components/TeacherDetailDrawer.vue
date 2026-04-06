<template>
  <el-drawer v-model="isVisible" :title="drawerTitle" size="600px" @closed="handleClosed">
    <div v-loading="loading" class="min-h-full">

      <!-- Avatar ------------------------------------------------------- -->
      <div class="flex items-center gap-5 mb-6">
        <div class="relative group w-20 h-20 flex-shrink-0">
          <el-image
            :src="avatarUrl || ''"
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
            class="absolute inset-0 rounded-full overflow-hidden"
            action="#"
            :limit="1"
            :multiple="false"
            accept=".jpg,.jpeg,.png,.webp"
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleAvatarChange"
          >
            <div
              class="w-20 h-20 rounded-full flex flex-col items-center justify-center
                     bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
            >
              <div v-if="uploadingAvatar" class="i-hugeicons:loading-03 animate-spin text-white text-xl" />
              <template v-else>
                <div class="i-hugeicons:camera-02 text-white text-xl" />
                <span class="text-white text-10px mt-1">編輯頭像</span>
              </template>
            </div>
          </el-upload>
        </div>
        <div class="flex flex-col gap-1 text-xs color-[#7e8299]">
          <span>支援格式：JPG、PNG、WebP</span>
          <span>限制10MB</span>
        </div>
      </div>

      <!-- Basic Info Form ---------------------------------------------- -->
      <el-form ref="basicFormRef" :model="basicForm" :rules="basicRules" size="small" label-position="top" label-width="120px">
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
          <el-col :span="10">
            <el-form-item :label="$t('common.email')" prop="email">
              <el-input v-model="basicForm.email" class="h-30px!" />
            </el-form-item>
          </el-col>
          <el-col :span="10" :push="2">
            <el-form-item label="教師等級" prop="teacher_level">
              <el-input-number v-model="basicForm.teacher_level" :min="1" class="h-30px!" />
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
          <el-button type="primary" round size="small" class="py-3!" :loading="saving" @click="saveBasicInfo">
            {{ $t('common.save') }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- Teacher Details ---------------------------------------------- -->
      <el-divider content-position="left" class="mt-8 mb-2">
        <span class="text-13px color-[#1d2d44]">教師相關資訊</span>
      </el-divider>
      <div class="flex justify-end">
        <el-button type="primary" round text size="small" class="mb-2" @click="openDetailDialog()">
          <template #icon><div class="i-hugeicons:add-square" /></template>
          新增教師資訊
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
              <el-tag size="small" :type="detailTagType(item.detail_type)" class="text-10px px-5px h-18px!">
                {{ DETAIL_TYPE_MAP[item.detail_type] || item.detail_type }}
              </el-tag>
            </div>
            <span class="text-12px text-[#3f4254]">{{ item.content || '-' }}</span>
            <div class="flex gap-3 mt-0.5">
              <span v-if="item.issue_date" class="text-11px color-gray-400">發證：{{ item.issue_date }}</span>
              <span v-if="item.expiry_date" class="text-11px color-gray-400">到期：{{ item.expiry_date }}</span>
            </div>
            <div v-if="item.file_name" class="text-11px color-[#626aef] mt-0.5 flex items-center gap-1">
              <div class="i-hugeicons:file-02" />{{ item.file_name }}
            </div>
          </div>
          <!-- Right -->
          <div class="flex items-center gap-1 flex-shrink-0">
            <el-tooltip content="編輯" effect="dark">
              <el-button link type="primary" @click="openDetailDialog(item)">
                <div class="i-hugeicons:edit-02" />
              </el-button>
            </el-tooltip>
            <el-tooltip content="刪除" effect="dark">
              <el-button link type="danger" @click="handleDeleteDetail(item.id)">
                <div class="i-hugeicons:delete-02" />
              </el-button>
            </el-tooltip>
          </div>
        </div>
        <div v-if="!teacherDetails.length" class="text-center text-12px color-gray-400 py-4">尚無教師明細</div>
      </div>
    </div>
  </el-drawer>

  <!-- Detail Dialog ---------------------------------------------------- -->
  <el-dialog
    v-model="showDetailDialog"
    :title="editingDetailId ? '編輯教師相關資訊' : '新增教師相關資訊'"
    width="440px"
    top="12vh"
    append-to-body
    destroy-on-close
    @closed="resetDetailForm"
  >
    <el-form ref="detailFormRef" :model="detailForm" :rules="detailRules" label-position="top" size="small">
      <!-- 類型 -->
      <el-form-item label="類型" prop="detail_type">
        <el-select v-model="detailForm.detail_type" placeholder="請選擇類型" class="w-full">
          <el-option label="學歷" value="qualification" />
          <el-option label="證照" value="certificate" />
          <el-option label="教學影片" value="video" />
          <el-option label="經歷" value="experience" />
        </el-select>
      </el-form-item>
      <!-- 內容 -->
      <el-form-item label="內容" prop="content">
        <el-input v-model="detailForm.content" type="textarea" :rows="4" placeholder="請輸入內容" />
      </el-form-item>
      <!-- 發證日期：僅 certificate -->
      <el-form-item v-if="detailForm.detail_type === 'certificate'" label="發證日期" prop="issue_date">
        <el-date-picker
          v-model="detailForm.issue_date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="請選擇發證日期"
          class="w-full! h-30px!"
        />
      </el-form-item>
      <!-- 到期日期：僅 certificate -->
      <el-form-item v-if="detailForm.detail_type === 'certificate'" label="到期日期" prop="expiry_date">
        <el-date-picker
          v-model="detailForm.expiry_date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="請選擇到期日期"
          class="w-full! h-30px!"
        />
      </el-form-item>
      <!-- 上傳檔案：certificate 或 video -->
      <el-form-item
        v-if="detailForm.detail_type === 'certificate' || detailForm.detail_type === 'video'"
        label="上傳檔案"
      >
        <el-upload
          action="#"
          :limit="1"
          :multiple="false"
          :auto-upload="false"
          :show-file-list="true"
          :on-change="(f: any) => { detailPendingFile = f.raw || null }"
          :on-remove="() => { detailPendingFile = null }"
        >
          <el-button size="small" round plain>
            <template #icon><div class="i-hugeicons:upload-01" /></template>
            選擇檔案
          </el-button>
        </el-upload>
        <div v-if="existingFileName && !detailPendingFile" class="text-11px color-[#626aef] mt-1 flex items-center gap-1">
          <div class="i-hugeicons:file-02" />{{ existingFileName }}（已上傳）
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="flex justify-end gap-2">
        <el-button round size="small" class="py-3!" @click="showDetailDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" round size="small" class="py-3!" :loading="savingDetail" @click="saveDetail">
          {{ editingDetailId ? $t('common.save') : '新增' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { getTeacherById, updateTeacher, type TeacherUpdate } from '@/api/teacher';
import {
  getTeacherDetails,
  createTeacherDetail,
  updateTeacherDetail,
  deleteTeacherDetail,
  type TeacherDetail,
} from '@/api/teacherDetails';
import { uploadTeacherAvatar, uploadDetailFile } from '@/utils/upload';

type DetailType = 'qualification' | 'certificate' | 'video' | 'experience';

const DETAIL_TYPE_MAP: Record<string, string> = {
  qualification: '學歷',
  certificate: '證照',
  video: '教學影片',
  experience: '經歷',
};

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

// UI State
const loading = ref(false);
const saving = ref(false);
const uploadingAvatar = ref(false);
const avatarUrl = ref<string | null>(null);

const drawerTitle = computed(() => {
  return (basicForm.name ? basicForm.name : 'Teacher Details') + ' 詳情';
});

// --- Basic Info Form ---
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
  detail_type: [{ required: true, message: '請選擇類型', trigger: 'change' }],
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
        savedId = res.data.id;
        ElMessage.success('教師明細已更新');
      } else {
        // Create
        const res = await createTeacherDetail({
          teacher_id: tId,
          detail_type: detailForm.detail_type,
          content: detailForm.content || null,
          issue_date: detailForm.detail_type === 'certificate' ? detailForm.issue_date : null,
          expiry_date: detailForm.detail_type === 'certificate' ? detailForm.expiry_date : null,
        });
        savedId = res.data.id;
        ElMessage.success('教師明細已新增');
      }

      // Upload file if pending
      if (detailPendingFile.value && (detailForm.detail_type === 'certificate' || detailForm.detail_type === 'video')) {
        try {
          await uploadDetailFile(savedId, detailPendingFile.value);
        } catch (e) {
          ElMessage.warning('明細已儲存，但檔案上傳失敗，請重新上傳');
        }
      }

      showDetailDialog.value = false;
      await loadDetails();
    } catch (e) {
      console.error(e);
      ElMessage.error(editingDetailId.value ? '更新教師明細失敗' : '新增教師明細失敗');
    } finally {
      savingDetail.value = false;
    }
  });
};

const handleDeleteDetail = async (detailId: string) => {
  try {
    await ElMessageBox.confirm('確定要刪除此明細嗎？', '刪除確認', {
      type: 'warning',
      confirmButtonText: '確定',
      cancelButtonText: '取消',
    });
    await deleteTeacherDetail(detailId);
    ElMessage.success('明細已刪除');
    await loadDetails();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('刪除失敗');
  }
};

// --- Data Loading ---
const loadDetails = async () => {
  const tId = props.teacherId;
  if (!tId) return;
  try {
    const res = await getTeacherDetails(tId);
    teacherDetails.value = res.data || [];
  } catch (e) {
    ElMessage.error('載入教師明細失敗');
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
    const target = teacherRes.data;
    if (target) {
      basicForm.name = target.name;
      basicForm.email = target.email;
      basicForm.phone = target.phone || '';
      basicForm.address = target.address || '';
      basicForm.bio = target.bio || '';
      basicForm.teacher_level = target.teacher_level;
      avatarUrl.value = (target as any).avatar_url || null;
    }
  } catch (error) {
    ElMessage.error('載入教師資料失敗');
  } finally {
    loading.value = false;
  }
};

const handleAvatarChange = async (uploadFile: any) => {
  const tId = props.teacherId;
  if (!tId || !uploadFile.raw) return;
  const MAX_SIZE_MB = 10;
  if (uploadFile.raw.size > MAX_SIZE_MB * 1024 * 1024) {
    ElMessage.warning(`檔案大小不可超過 ${MAX_SIZE_MB}MB，請重新選擇`);
    return;
  }
  uploadingAvatar.value = true;
  try {
    await uploadTeacherAvatar(tId, uploadFile.raw);
    const res = await getTeacherById(tId);
    avatarUrl.value = (res.data as any).avatar_url || null;
    ElMessage.success('頭像已更新');
  } catch (e) {
    console.error(e);
    ElMessage.error('頭像上傳失敗');
  } finally {
    uploadingAvatar.value = false;
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
        ElMessage.success('基本資料已儲存');
        emit('saved');
      } catch (e) {
        ElMessage.error('儲存失敗');
      } finally {
        saving.value = false;
      }
    }
  });
};

const handleClosed = () => {
  avatarUrl.value = null;
  teacherDetails.value = [];
};

watch(() => props.modelValue, (val) => {
  if (val && props.teacherId) {
    fetchData();
  }
});
</script>

<style scoped>
.h-full { height: 100%; }
</style>
