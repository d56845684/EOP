<template>
  <div class="min-h-screen flex items-center justify-center p-4 bg-[#f5f7fb]">
    <el-card shadow="never" class="max-w-480px w-full text-center">
      <div class="w-72px h-72px rounded-full bg-[#fdecec] flex items-center justify-center mx-auto mb-4">
        <div class="i-hugeicons:cancel-circle text-40px color-[#dc2626]" />
      </div>

      <h2 class="mt-0 mb-2 color-[#dc2626]">{{ $t('authError.title') }}</h2>
      <p class="text-sm text-[var(--el-text-color-regular)] mb-2">
        {{ errorMessage }}
      </p>
      <p v-if="description" class="text-xs text-[var(--el-text-color-secondary)] break-all mb-5">
        {{ description }}
      </p>

      <div class="flex justify-center gap-2">
        <el-button round @click="router.push('/login')">{{ $t('authError.backLogin') }}</el-button>
        <el-button type="primary" round @click="router.push('/profile')">{{ $t('authError.goProfile') }}</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const errorMessageMap: Record<string, string> = {
  missing_params: 'authError.messages.missing_params',
  invalid_state: 'authError.messages.invalid_state',
  line_auth_failed: 'authError.messages.line_auth_failed',
  line_already_bound: 'authError.messages.line_already_bound',
  access_denied: 'authError.messages.access_denied',
  unknown_error: 'authError.messages.unknown_error',
};

const errorMessage = computed(() => {
  const error = String(route.query.error || 'unknown_error');
  return t(errorMessageMap[error] || errorMessageMap.unknown_error);
});

const description = computed(() => {
  const raw = route.query.description;
  return raw ? decodeURIComponent(String(raw)) : '';
});
</script>
