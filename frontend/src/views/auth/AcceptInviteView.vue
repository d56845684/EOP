<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <h2 class="title">帳號驗證</h2>
      </template>

      <el-alert
        v-if="!token"
        class="mb-16"
        title="邀請連結無效，缺少 token"
        type="error"
        :closable="false"
        show-icon
      />

      <el-form :model="form" @submit.prevent="handleAcceptInvite">
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="新密碼"
            :prefix-icon="Lock"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>

        <el-form-item>
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="確認新密碼"
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
            完成帳號驗證
          </el-button>
        </el-form-item>
      </el-form>

      <div class="hints">
        <el-alert title="請設置新密碼" type="info" :closable="false" show-icon />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Lock } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { acceptInviteApi } from '@/api/auth';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';

const route = useRoute();
const router = useRouter();
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
    ElMessage.error('邀請連結無效，缺少 token');
    return false;
  }

  if (!form.password || !form.confirmPassword) {
    ElMessage.warning('請輸入並確認新密碼');
    return false;
  }

  if (form.password.length < 6) {
    ElMessage.warning('密碼至少需要 6 個字元');
    return false;
  }

  if (form.password !== form.confirmPassword) {
    ElMessage.warning('兩次輸入的密碼不一致');
    return false;
  }

  return true;
};

const handleAcceptInvite = async () => {
  if (loading.value || !validateForm()) return;

  loading.value = true;
  try {
    const res = assertApiSuccess(await acceptInviteApi(token.value, form.password), '帳號驗證失敗');
    ElMessage.success(res.message || '帳號驗證成功，請重新登入');
    router.push({ name: 'Login' });
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '帳號驗證失敗，請確認邀請連結是否有效'));
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
