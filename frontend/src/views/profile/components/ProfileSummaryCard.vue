<template>
  <el-card shadow="never" class="h-full">
    <template #header>
      <div class="flex items-center gap-2">
        <div class="i-hugeicons:user-account text-lg color-[#2563eb]" />
        <span class="font-medium">{{ $t('profile.summary.title') }}</span>
      </div>
    </template>

    <el-skeleton v-if="loading" :rows="6" animated />

    <template v-else>
      <div class="flex items-center gap-4 mb-5">
        <el-avatar :size="72" :src="avatarUrl || ''">
          <div class="i-hugeicons:user text-2xl" />
        </el-avatar>
        <div>
          <div class="text-xl font-semibold">{{ profile?.name || userInfo?.email || '-' }}</div>
          <div class="text-sm text-[var(--el-text-color-secondary)] mt-1">{{ userInfo?.email || '-' }}</div>
          <el-tag size="small" effect="plain" class="mt-2">
            {{ roleLabel }}
          </el-tag>
        </div>
      </div>

      <el-descriptions :column="1" border size="small">
        <el-descriptions-item :label="$t('profile.summary.accountStatus')">
          <el-tag :type="profile?.is_active ? 'success' : 'info'" size="small" effect="light">
            {{ profile?.is_active ? $t('profile.summary.active') : $t('profile.summary.inactive') }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('profile.summary.loginAccount')">
          {{ userInfo?.email || '-' }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('profile.summary.systemRole')">
          {{ roleLabel }}
        </el-descriptions-item>
        <!-- <el-descriptions-item :label="$t('profile.summary.entityId')">
          <span class="font-mono text-xs break-all">{{ entityId || userInfo?.id || '-' }}</span>
        </el-descriptions-item> -->
        <el-descriptions-item :label="$t('profile.summary.accountId')">
          <span class="font-mono text-xs break-all">{{ userInfo?.id || '-' }}</span>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('profile.summary.createdAt')">
          {{ formatDate(profile?.created_at) }}
        </el-descriptions-item>
      </el-descriptions>
    </template>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import dayjs from 'dayjs';
import type { UserInfo } from '@/api/auth';
import type { UserProfile } from '@/api/user';
import { formatRoleLabel } from '@/utils/i18n-formatters';

const props = defineProps<{
  loading: boolean;
  userInfo: UserInfo | null;
  profile: UserProfile | null;
  avatarUrl?: string;
}>();

const roleLabel = computed(() => {
  const role = props.userInfo?.role || props.profile?.role || '';
  return formatRoleLabel(role);
});

const entityId = computed(() => {
  return props.userInfo?.employee_id || props.userInfo?.teacher_id || props.userInfo?.student_id || null;
});

const formatDate = (value?: string | null) => {
  if (!value) return '-';
  return dayjs(value).format('YYYY-MM-DD HH:mm');
};
</script>
