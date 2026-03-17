<script setup lang="ts">
import { computed, ref } from 'vue';
import { useAuthStore } from '@/stores/auth';
import adminAvatar from '@/assets/avatars/admin.svg?url';
import teacherAvatar from '@/assets/avatars/teacher.svg?url';
import studentAvatar from '@/assets/avatars/student.svg?url';
import defaultAvatar from '@/assets/avatars/default.svg?url';

const isError = ref(false)

const store = useAuthStore();
const nickname = computed(() => store.profile?.name || 'User');
const role = computed(() => {
  switch (store.profile?.role) {
    case 'admin':
      return 'Administrator';
    case 'teacher':
      return 'Teacher';
    case 'student':
      return 'Student';
    default:
      return store.profile?.role;
  }
});
const avatarUrl = computed(() => {
  if (isError.value) return defaultAvatar

  let avatar = '';
  switch (store.profile?.role) {
    case 'admin':
      avatar = adminAvatar;
      break;
    case 'teacher':
      avatar = teacherAvatar;
      break;
    case 'student':
      avatar = studentAvatar;
      break;
    default:
      avatar = defaultAvatar;
  }
  return store.profile?.avatar_url || avatar;
});

const handleAvatarError = () => {
  isError.value = true;
};
</script>

<template>
  <div class="dashboard-container">
    <el-card class="welcome-card" shadow="hover">
      <div class="welcome-content">
        <el-avatar class="user-avatar" :size="80" :src="avatarUrl" fit="contain" @error="handleAvatarError" />
        <div class="welcome-text">
          <h1>Welcome, {{ nickname }}!</h1>
          <p>You are logged in as <el-tag>{{ role }}</el-tag></p>
          <div class="quick-actions">
             <p class="sub-text">Select a module from the sidebar to get started.</p>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.dashboard-container {
  padding: 20px;
}
.welcome-card {
  max-width: 800px;
  margin: 0 auto;
  margin-top: 50px;
}
.welcome-content {
  display: flex;
  align-items: center;
  gap: 30px;
  padding: 20px;
}
.user-avatar {
  flex: 0 0 80px;
}
.welcome-text h1 {
  margin: 0 0 10px 0;
  font-size: 24px;
}
.welcome-text p {
  margin: 0 0 10px 0;
  color: #606266;
}
.sub-text {
    font-size: 14px;
    color: #909399;
}
</style>
