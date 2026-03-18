<template>
  <el-header class="header flex justify-between items-center">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item :to="{ path: '/' }">{{ $t('common.home') }}</el-breadcrumb-item>
      <el-breadcrumb-item>{{ $t(getBreadcrumbLabel($route.name as string)) }}</el-breadcrumb-item>
    </el-breadcrumb>
    <el-space class="flex justify-end items-center" :size="10" :spacer="spacer">
      <el-dropdown :show-arrow="false" @command="handleLanguageChange" class="lang-dropdown cursor-pointer">
        <div class="el-dropdown-link w-52px flex items-center gap-6px hover:color-[#409EFF]">
          <div class="i-hugeicons:translation text-size-16px" />
          <span class="text-size-14px">{{ locale === 'en' ? ' EN' : '中文' }}</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="en" :disabled="locale === 'en'">English</el-dropdown-item>
            <el-dropdown-item command="zh-TW" :disabled="locale === 'zh-TW'">繁體中文</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-dropdown :show-arrow="false" @command="handleCommand">
        <div class="flex items-center gap-2 cursor-pointer">
          <el-avatar class="user-avatar" :size="30" :src="avatarUrl" fit="contain" @error="handleAvatarError" />
          <span class="nickname text-size-14px hover:color-[#409EFF]">{{ nickname }}</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">
              <div class="i-hugeicons:logout-01 text-size-16px" />
              <span class="px-2">{{ $t('common.logout') }}</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </el-space>
  </el-header>
</template>

<script setup lang="ts">
  import { h, ref, computed } from 'vue';
  import { getBreadcrumbLabel } from '@/utils/route';
  import { useI18n } from 'vue-i18n';
  import { useAuthStore } from '@/stores/auth';
  import defaultAvatar from '@/assets/avatars/default.svg?url';
  import { ElDivider } from 'element-plus'

  const authStore = useAuthStore();
  const { locale } = useI18n();
  const isError = ref(false);
  const spacer = h(ElDivider, { direction: 'vertical' })

  const emit = defineEmits(['logout']);

  const nickname = computed(() => authStore.profile?.name || 'User');
  const avatarUrl = computed(() => {
    if (isError.value) return defaultAvatar
    return authStore.userAvatar;
  });

  const handleLanguageChange = (lang: string) => {
    locale.value = lang;
    localStorage.setItem('eop_locale', lang);
  };

  const handleAvatarError = () => {
    isError.value = true;
  };

  const handleCommand = (command: string) => {
    if (command === 'logout') {
      emit('logout');
    }
  }


</script>

<style scoped lang="scss">
.locale-switch {
  :deep(.el-switch__core) {
    width: 30px;
    height: 24px;
    border-radius: 20px;
  }
}
</style>
