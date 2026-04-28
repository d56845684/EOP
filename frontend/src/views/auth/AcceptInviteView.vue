<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <h2 class="title">{{ $t('acceptInvite.title') }}</h2>
      </template>

      <el-alert
        v-if="!token"
        class="mb-16"
        :title="$t('acceptInvite.invalidToken')"
        type="error"
        :closable="false"
        show-icon
      />

      <el-form :model="form" @submit.prevent="handleAcceptInvite">
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            :placeholder="$t('acceptInvite.passwordPlaceholder')"
            :prefix-icon="Lock"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>

        <el-form-item>
          <el-input
            v-model="form.confirmPassword"
            type="password"
            :placeholder="$t('acceptInvite.confirmPasswordPlaceholder')"
            :prefix-icon="Lock"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            class="w-100"
            :disabled="!token"
            @click="handleAcceptInvite"
          >
            {{ $t('acceptInvite.submit') }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="hints">
        <el-alert :title="$t('acceptInvite.hint')" type="info" :closable="false" show-icon />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { Lock } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { acceptInviteApi } from '@/api/auth';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const loading = ref(false);

const token = computed(() => {
  const value = route.query.token;
  return Array.isArray(value) ? value[0] || '' : value || '';
});

const form = reactive({
  password: '',
  confirmPassword: '',
});

const validateForm = () => {
  if (!token.value) {
    ElMessage.error(t('acceptInvite.invalidToken'));
    return false;
  }

  if (!form.password || !form.confirmPassword) {
    ElMessage.warning(t('acceptInvite.passwordRequired'));
    return false;
  }

  if (form.password.length < 6) {
    ElMessage.warning(t('acceptInvite.passwordMin'));
    return false;
  }

  if (form.password !== form.confirmPassword) {
    ElMessage.warning(t('acceptInvite.passwordMismatch'));
    return false;
  }

  return true;
};

const handleAcceptInvite = async () => {
  if (loading.value || !validateForm()) return;

  loading.value = true;
  try {
    const res = assertApiSuccess(await acceptInviteApi(token.value, form.password), t('acceptInvite.failed'));
    ElMessage.success(res.message || t('acceptInvite.success'));
    router.push({ name: 'Login' });
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('acceptInvite.invalidInvite')));
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
}

.login-card {
  width: 400px;
}

.title {
  text-align: center;
}

.w-100 {
  width: 100%;
}

.hints {
  margin-top: 20px;
}

.mb-16 {
  margin-bottom: 16px;
}
</style>
