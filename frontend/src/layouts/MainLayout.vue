<template>
  <el-container class="layout-container">
    <SideBar />
    <el-container direction="vertical">
      <NavBar @logout="handleLogout" />

      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <!-- Keep Alive could go here -->
            <component :is="Component" />
          </transition>
        </router-view>
        <el-footer height="40px" class="footer !border-t-none">
          <span class="text-gray">© 2026 EOP System Prototype</span>
        </el-footer>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import NavBar from './NavBar.vue';
import SideBar from './SideBar.vue';

// i18n
const router = useRouter();
const authStore = useAuthStore();

// Auto-logout
import { useIdle } from '@vueuse/core';
const { idle } = useIdle(10 * 60 * 1000); 

watch(idle, (isIdle) => {
  if (isIdle && authStore.userInfo) {
    handleLogout();
  }
});

const handleLogout = async () => {
    authStore.logout();
    router.push('/login');
};
</script>

<style scoped lang="scss">
.layout-container {
  height: 100vh;
}

.header {
  background-color: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.main-content {
  background-color: #f3f5fa;
  padding: 20px 20px 0;
}

.footer {
    display: flex;
    align-items: center;
    justify-content: center;
    border-top: 1px solid var(--el-border-color);
    color: var(--el-text-color-secondary);
    font-size: 12px;
}
</style>
