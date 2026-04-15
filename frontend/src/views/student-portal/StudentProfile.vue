<template>
  <div class="student-profile">
    <div class="page-title">{{ $t('studentProfile.title') }}</div>

    <!-- Alert for First Login -->
    <el-alert
        v-if="isFirstLogin"
        :title="$t('studentProfile.alertFirstLogin')"
        type="warning"
        show-icon
        :closable="false"
        style="margin-bottom: 20px;"
    />

    <el-card class="profile-card">
        <el-form :model="form" label-position="top">
            
            <!-- Section A: Read-Only -->
            <el-row :gutter="20">
                <el-col :span="8">
                    <el-form-item :label="$t('studentProfile.labelName')">
                        <el-input v-model="form.name" disabled />
                    </el-form-item>
                </el-col>
                <el-col :span="8">
                    <el-form-item :label="$t('studentProfile.labelBirthday')">
                        <el-input v-model="form.birthday" disabled />
                    </el-form-item>
                </el-col>
                <el-col :span="8">
                    <el-form-item :label="$t('studentProfile.labelEmail')">
                        <el-input v-model="form.email" disabled />
                    </el-form-item>
                </el-col>
            </el-row>

            <el-divider />

            <!-- Section B: Editable Contact -->
            <el-row :gutter="20">
                <el-col :span="12">
                    <el-form-item :label="$t('studentProfile.labelPhone')" required>
                        <el-input v-model="form.phone" />
                    </el-form-item>
                </el-col>
                <el-col :span="12">
                    <el-form-item :label="$t('studentProfile.labelAddress')">
                        <el-input v-model="form.address" />
                    </el-form-item>
                </el-col>
                <el-col :span="12">
                    <el-form-item :label="$t('studentProfile.labelEmergencyContact')">
                        <el-input v-model="form.emergencyContactName" />
                    </el-form-item>
                </el-col>
                <el-col :span="12">
                    <el-form-item :label="$t('studentProfile.labelEmergencyPhone')">
                        <el-input v-model="form.emergencyContactPhone" />
                    </el-form-item>
                </el-col>
            </el-row>

            <el-divider />

            <!-- Section C: Security -->
            <el-form-item :label="$t('studentProfile.labelPassword')">
                <div class="password-row">
                    <el-input type="password" value="********" disabled style="width: 200px; margin-right: 10px;" />
                    <el-button type="primary" @click="passwordDialogVisible = true">
                        {{ $t('studentProfile.btnChangePassword') }}
                    </el-button>
                </div>
            </el-form-item>

            <div class="form-actions">
                <el-button type="primary" size="large" @click="saveProfile">
                    {{ $t('studentProfile.btnSave') }}
                </el-button>
            </div>

        </el-form>
    </el-card>

    <!-- Password Change Dialog -->
    <el-dialog v-model="passwordDialogVisible" :title="$t('studentProfile.dialogTitle')" width="400px">
        <el-form label-position="top">
            <el-form-item :label="$t('studentProfile.labelNewPassword')" required>
                <el-input v-model="passwordForm.newPassword" type="password" show-password />
            </el-form-item>
            <el-form-item :label="$t('studentProfile.labelConfirmPassword')" required>
                <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
            </el-form-item>
        </el-form>
        <template #footer>
            <el-button @click="passwordDialogVisible = false">{{ $t('common.cancel') }}</el-button>
            <el-button type="primary" @click="submitPasswordChange">{{ $t('common.confirm') }}</el-button>
        </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMockStore } from '../../stores/mockStore';
import { ElMessage } from 'element-plus';

const { t } = useI18n();
const store = useMockStore();

// --- State ---
const currentUser = computed(() => store.currentUser);
const currentStudent = computed(() => store.students.find(s => s.id === currentUser.value?.id));

const isFirstLogin = computed(() => currentStudent.value?.isFirstLogin || false);

const form = reactive({
    name: '',
    birthday: '',
    email: '',
    phone: '',
    address: '',
    emergencyContactName: '',
    emergencyContactPhone: ''
});

const passwordDialogVisible = ref(false);
const passwordForm = reactive({
    newPassword: '',
    confirmPassword: ''
});

// --- Lifecycle ---
onMounted(() => {
    loadProfile();
});

const loadProfile = () => {
    if (currentStudent.value) {
        const s = currentStudent.value;
        form.name = s.name;
        form.birthday = s.birthday;
        form.email = s.email;
        form.phone = s.phone;
        form.address = s.address;
        form.emergencyContactName = s.emergencyContactName;
        form.emergencyContactPhone = s.emergencyContactPhone;
    } else {
        // Fallback or handle missing student profile linked to user
        if (currentUser.value?.role === 'student') {
             // Mock default if exact id match fails
             form.name = currentUser.value.nickname;
        }
    }
};

// --- Actions ---
const saveProfile = async () => {
    if (currentStudent.value) {
        // Update store logic
        const target = store.students.find(s => s.id === currentStudent.value?.id);
        if (target) {
            target.phone = form.phone;
            target.address = form.address;
            target.emergencyContactName = form.emergencyContactName;
            target.emergencyContactPhone = form.emergencyContactPhone;
            ElMessage.success(t('studentProfile.msgUpdateSuccess'));
        }
    }
};

const submitPasswordChange = async () => {
    if (!passwordForm.newPassword || !passwordForm.confirmPassword) {
        ElMessage.warning('Please fill in all fields');
        return;
    }
    
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
        ElMessage.error(t('studentProfile.errorPasswordMismatch'));
        return;
    }
    
    // Update Store
    if (currentStudent.value) {
        const target = store.students.find(s => s.id === currentStudent.value?.id);
        if (target) {
            target.isFirstLogin = false; // Clear first login flag
        }
    }
    
    if (currentUser.value) {
        const userTarget = store.users.find(u => u.id === currentUser.value?.id);
        if (userTarget) {
            userTarget.password = passwordForm.newPassword;
        }
    }

    ElMessage.success(t('studentProfile.msgPasswordSuccess'));
    passwordDialogVisible.value = false;
    
    // Clear form
    passwordForm.newPassword = '';
    passwordForm.confirmPassword = '';
};

</script>

<style scoped lang="scss">
.student-profile {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 20px;
}

.page-title {
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 20px;
    align-self: flex-start;
}

.profile-card {
    width: 100%;
    max-width: 800px;
}

.password-row {
    display: flex;
    align-items: center;
}

.form-actions {
    margin-top: 30px;
    display: flex;
    justify-content: flex-end;
}
</style>
