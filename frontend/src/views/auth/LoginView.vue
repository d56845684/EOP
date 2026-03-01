<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <h2 class="title">{{ $t('login.title') }}</h2>
      </template>
      <el-form :model="form" @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="form.username" :placeholder="$t('login.username')" :prefix-icon="User" />
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
        <el-alert :title="$t('login.superAdminHint')" type="info" :closable="false" show-icon />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useMockStore } from '../../stores/mockStore';
import { User, Lock } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

const store = useMockStore();
const router = useRouter();
const loading = ref(false);

const form = ref({
  username: 'eopAdmin',
  password: 'eopsuper888',
});

const handleLogin = async () => {
  if (!form.value.username || !form.value.password) return;
  loading.value = true;
  try {
    await store.login(form.value.username, form.value.password);
    ElMessage.success('Login Successful');
    router.push('/');
  } catch (e: any) {
    ElMessage.error(e.message);
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
