<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <h2 class="title">{{ $t('login.title') }}</h2>
      </template>
      <el-form :model="form" @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="form.email" placeholder="Email" :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" :placeholder="$t('login.password')" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" class="w-100" @click="handleLogin">
            {{ $t('login.loginBtn') }}
          </el-button>
        </el-form-item>
      </el-form>
      <div class="hints">
        <el-alert title="Please login with your email" type="info" :closable="false" show-icon />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../../stores/auth';
import { User, Lock } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

const authStore = useAuthStore();
const router = useRouter();
const loading = ref(false);

const form = ref({
  email: '',
  password: '',
});

const handleLogin = async () => {
  if (!form.value.email || !form.value.password) return;
  loading.value = true;
  try {
    const res = await authStore.login({ email: form.value.email, password: form.value.password });
    if (res?.success) {
      ElMessage.success('Login Successful');
      if (res.user.role === 'teacher') {
        router.push('/teacher-portal/schedule');
      } else if (res.user.role === 'student') {
        router.push('/student-portal/booking');
      } else {
        router.push('/dashboard');
      }
    } else {
      ElMessage.error(res?.message || 'Login failed');
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || e.message || 'Login failed');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: var(--el-bg-color-page);
}
.login-card {
  width: 400px;
}
.title {
  text-align: center;
  margin: 0;
}
.w-100 {
  width: 100%;
}
.hints {
  margin-top: 20px;
}
</style>
