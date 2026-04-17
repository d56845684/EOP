<template>
  <div class="min-h-screen flex items-center justify-center p-4 bg-[#f5f7fb]">
    <el-card shadow="never" class="max-w-420px w-full text-center">
      <div class="w-72px h-72px rounded-full bg-[#eaf8ef] flex items-center justify-center mx-auto mb-4">
        <div class="i-hugeicons:checkmark-badge-03 text-40px color-[#16a34a]" />
      </div>

      <h2 class="mt-0 mb-2 color-[#16a34a]">
        {{ isNewUser ? $t('authSuccess.registerTitle') : $t('authSuccess.bindTitle') }}
      </h2>
      <p class="text-sm text-[var(--el-text-color-secondary)] mb-4">
        {{ isNewUser ? $t('authSuccess.registerDesc') : $t('authSuccess.bindDesc') }}
      </p>
      <p class="text-xs text-[var(--el-text-color-secondary)] mb-5">
        {{ $t('authSuccess.redirect', { countdown }) }}
      </p>

      <el-button type="primary" round @click="router.push('/profile')">
        {{ $t('authSuccess.goProfile') }}
      </el-button>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const countdown = ref(3);
let timer: number | null = null;

const isNewUser = computed(() => route.query.new_user === 'true');

onMounted(() => {
  timer = window.setInterval(() => {
    countdown.value -= 1;
    if (countdown.value <= 0) {
      if (timer) window.clearInterval(timer);
      router.push('/profile');
    }
  }, 1000);
});

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer);
});
</script>
