<template>
  <div class="teacher-profile">
    <el-card>
      <template #header>
        <div class="header">
          <span class="title">{{ $t('teacherProfile.title') }}</span>
          <el-button type="primary" @click="saveProfile">{{ $t('teacherProfile.btnSave') }}</el-button>
        </div>
      </template>

      <el-form label-position="top">
        <!-- 1. Profile Photo -->
        <el-form-item :label="$t('teacherProfile.labelPhoto')">
            <el-upload
                class="avatar-uploader"
                action="#"
                :show-file-list="false"
                :auto-upload="false"
                :on-change="handleAvatarChange"
                accept="image/*"
            >
                <img v-if="form.avatar" :src="form.avatar" class="avatar" />
                <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
            </el-upload>
        </el-form-item>

        <!-- 2. Education & Experience -->
        <el-form-item :label="$t('teacherProfile.labelEdu')">
            <el-input 
                v-model="form.educationExperience" 
                type="textarea" 
                :rows="5"
                placeholder="List your academic background and work experience..." 
            />
        </el-form-item>

        <!-- 3. Teaching Specialty -->
        <el-form-item :label="$t('teacherProfile.labelSpecialty')">
            <el-input 
                v-model="form.teachingSpecialty" 
                type="textarea" 
                :rows="3"
            />
        </el-form-item>

        <!-- 4. Self Introduction -->
        <el-form-item :label="$t('teacherProfile.labelIntro')">
            <el-input 
                v-model="form.introduction" 
                type="textarea" 
                :rows="5"
            />
        </el-form-item>

        <!-- 5. Intro Video -->
        <el-form-item :label="$t('teacherProfile.labelVideo')">
            <div v-if="form.videoUrl" class="video-preview">
                <video controls :src="form.videoUrl" style="max-width: 100%; max-height: 300px; margin-bottom: 10px;"></video>
                <el-button type="danger" link @click="form.videoUrl = ''">Remove Video</el-button>
            </div>
            
            <el-upload
                v-else
                class="upload-demo"
                drag
                action="#"
                :auto-upload="false"
                :on-change="handleVideoChange"
                accept=".mp4"
            >
                <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                <div class="el-upload__text">
                    {{ $t('teacherProfile.uploadDragText') }}
                </div>
                <template #tip>
                    <div class="el-upload__tip">
                        {{ $t('teacherProfile.uploadTipVideo') }}
                    </div>
                </template>
            </el-upload>
        </el-form-item>

        <!-- 6. Certificates -->
        <el-form-item :label="$t('teacherProfile.labelCert')">
            <el-upload
                v-model:file-list="certFileList"
                list-type="picture-card"
                action="#"
                :auto-upload="false"
                :on-change="handleCertChange"
                :on-preview="handlePictureCardPreview"
                :on-remove="handleCertRemove"
                accept="image/*"
            >
                <el-icon><Plus /></el-icon>
            </el-upload>
        </el-form-item>

      </el-form>
    </el-card>

    <el-dialog v-model="dialogVisible">
        <img w-full :src="dialogImageUrl" alt="Preview Image" style="width: 100%" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMockStore } from '../../stores/mockStore';
import { ElMessage, type UploadFile, type UploadUserFile } from 'element-plus';
import { Plus, UploadFilled } from '@element-plus/icons-vue';

const { t } = useI18n();
const store = useMockStore();

// --- State ---
const currentUser = computed(() => store.currentUser);

const form = reactive({
    id: '', // Teacher ID
    avatar: '',
    educationExperience: '',
    teachingSpecialty: '',
    introduction: '',
    videoUrl: '',
    certs: [] as string[]
});

const certFileList = ref<UploadUserFile[]>([]);
const dialogImageUrl = ref('');
const dialogVisible = ref(false);

// --- Lifecycle ---
onMounted(() => {
    loadProfile();
});

const loadProfile = () => {
    if (!currentUser.value) return;
    
    // 1. Find the Teacher Profile associated with this User
    // Logic: Match by name or some link. 
    // In mockStore: u2 (Teacher A) -> t1 (Teacher A)
    let teacher = store.teachers.find(t => t.name === currentUser.value?.nickname);
    
    // Fallback: If logged in as u2 (Teacher A), manually link to t1 if names don't match perfectly, 
    // but in seed they do match 'Teacher A'.
    if (!teacher && currentUser.value.username === 'teacher.a') {
        teacher = store.teachers.find(t => t.id === 't1');
    }

    if (teacher) {
        form.id = teacher.id;
        form.avatar = teacher.avatar || currentUser.value.avatar || '';
        form.educationExperience = teacher.educationExperience || '';
        form.teachingSpecialty = teacher.teachingSpecialty || '';
        form.introduction = teacher.introduction || '';
        form.videoUrl = teacher.videoUrl || '';
        form.certs = teacher.certs || []; // String URLs

        // Populate file list for certs
        certFileList.value = form.certs.map((url, index) => ({
            name: `Cert ${index + 1}`,
            url: url
        }));
    }
};

// --- Handlers ---

// Avatar
const handleAvatarChange = (uploadFile: UploadFile) => {
    if (uploadFile.raw) {
        form.avatar = URL.createObjectURL(uploadFile.raw);
    }
};

// Video
const handleVideoChange = (uploadFile: UploadFile) => {
    if (uploadFile.raw) {
        const isMp4 = uploadFile.raw.type === 'video/mp4';
        if (!isMp4) {
            ElMessage.error(t('teacherProfile.uploadTipVideo'));
            return;
        }
        form.videoUrl = URL.createObjectURL(uploadFile.raw);
    }
};

// Certificates
const handleCertChange = (uploadFile: UploadFile) => {
     if (uploadFile.raw) {
        // Create URL and add to list implicitly via model, but we need to track it in form.certs eventually
        // But element-plus manages file-list. We will sync file-list to form.certs on save.
    }
};

const handleCertRemove = (uploadFile: UploadFile) => {
    // handled by v-model file-list
};

const handlePictureCardPreview = (uploadFile: UploadFile) => {
  dialogImageUrl.value = uploadFile.url!;
  dialogVisible.value = true;
};

// --- Save ---
const saveProfile = async () => {
    if (!form.id) {
         ElMessage.error('No teacher profile found linked to this user.');
         return;
    }

    // Sync certs from fileList
    // Note: uploadFile.url might be blob: or http: depending on if it's new or old.
    form.certs = certFileList.value.map(f => f.url!).filter(Boolean);

    // Update in Store
    const target = store.teachers.find(t => t.id === form.id);
    if (target) {
        target.avatar = form.avatar;
        target.educationExperience = form.educationExperience;
        target.teachingSpecialty = form.teachingSpecialty;
        target.introduction = form.introduction;
        target.videoUrl = form.videoUrl;
        target.certs = form.certs;
        
        // Also update User avatar if they match, so top-right corner updates?
        if (currentUser.value && (currentUser.value.username === 'teacher.a' || currentUser.value.nickname === target.name)) {
             const userTarget = store.users.find(u => u.id === currentUser.value?.id);
             if (userTarget) userTarget.avatar = form.avatar;
        }
        
        ElMessage.success(t('teacherProfile.msgSaved'));
    }
};

</script>

<style scoped lang="scss">
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    .title {
        font-size: 18px;
        font-weight: bold;
    }
}

.avatar-uploader .avatar {
  width: 120px;
  height: 120px;
  border-radius: 50%; /* Circular */
  display: block;
  object-fit: cover;
}

.avatar-uploader :deep(.el-upload) {
  border: 1px dashed var(--el-border-color);
  border-radius: 50%; /* Circular border */
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--el-transition-duration-fast);
  width: 120px;
  height: 120px;
}

.avatar-uploader :deep(.el-upload:hover) {
  border-color: var(--el-color-primary);
}

.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 120px;
  height: 120px;
  text-align: center;
}

.video-preview {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
}
</style>
