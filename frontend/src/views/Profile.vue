<script setup lang="ts">
import { computed } from 'vue';
import { useMockStore } from '../stores/mockStore';

const store = useMockStore();
const nickname = computed(() => store.currentUser?.nickname || 'User');
const role = computed(() => store.currentUser?.role === 'super_admin' ? 'Super Administrator' : 'Administrator');
</script>

<template>
  <div class="dashboard-container">
    <el-card class="welcome-card" shadow="hover">
      <div class="welcome-content">
        <el-avatar :size="80" :src="store.currentUser?.avatar || ''" />
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
