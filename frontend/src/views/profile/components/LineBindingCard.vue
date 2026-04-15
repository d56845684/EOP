<template>
  <el-card shadow="never" class="h-full">
    <template #header>
      <div class="flex items-center gap-2">
        <div class="i-hugeicons:link-square-02 text-lg color-[#00b900]" />
        <span class="font-medium">{{ $t('profile.line.title') }}</span>
      </div>
    </template>

    <el-skeleton v-if="loading" :rows="5" animated />

    <template v-else>
      <div class="rounded-xl px-4 py-4 bg-[#f8fafc]">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-sm text-[var(--el-text-color-secondary)] mb-1">{{ $t('profile.line.currentChannel') }}</div>
            <div class="font-medium">{{ channelLabel }} LINE</div>
          </div>
          <el-tag :type="binding?.is_bound ? 'success' : 'info'" size="small" effect="light">
            {{ binding?.is_bound ? $t('profile.line.bound') : $t('profile.line.unbound') }}
          </el-tag>
        </div>

        <div v-if="binding?.is_bound" class="mt-4">
          <div class="flex items-center gap-3">
            <el-avatar :size="48" :src="binding.line_picture_url || ''">
              <div class="i-hugeicons:user text-lg" />
            </el-avatar>
            <div>
              <div class="font-medium">{{ binding.line_display_name || $t('profile.line.defaultName') }}</div>
              <div class="text-xs text-[var(--el-text-color-secondary)] mt-1">
                {{ $t('profile.line.boundAt', { date: formatDate(binding.bound_at) }) }}
              </div>
            </div>
          </div>

          <div class="mt-4 flex gap-2">
            <el-button type="danger" plain round size="small" @click="$emit('unbind')">
              {{ $t('profile.line.unbind') }}
            </el-button>
          </div>
        </div>

        <div v-else class="mt-4">
          <p class="text-sm text-[var(--el-text-color-secondary)] mt-0 mb-4">
            {{ $t('profile.line.description') }}
          </p>
          <el-button type="success" round size="small" @click="$emit('bind')">
            <template #icon>
              <div class="i-hugeicons:link-square-02" />
            </template>
            {{ $t('profile.line.bindNow') }}
          </el-button>
        </div>
      </div>
    </template>
  </el-card>
</template>

<script setup lang="ts">
import dayjs from 'dayjs';
import { useI18n } from 'vue-i18n';
import type { LineBindingStatus } from '@/api/line';

useI18n();

defineProps<{
  loading: boolean;
  binding: LineBindingStatus | null;
  channelLabel: string;
}>();

defineEmits<{
  bind: [];
  unbind: [];
}>();

const formatDate = (value?: string | null) => {
  if (!value) return '-';
  return dayjs(value).format('YYYY-MM-DD HH:mm');
};
</script>
