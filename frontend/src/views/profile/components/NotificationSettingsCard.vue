<template>
  <el-card shadow="never" class="h-full">
    <template #header>
      <div class="flex items-center gap-2">
        <div class="i-hugeicons:notification-03 text-lg color-[#f59e0b]" />
        <span class="font-medium">{{ $t('profile.notifications.title') }}</span>
      </div>
    </template>

    <el-skeleton v-if="loading" :rows="6" animated />

    <template v-else-if="preferences">
      <div class="space-y-3">
        <div class="flex items-center justify-between rounded-xl border border-solid border-[#ebeef5] px-4 py-3">
          <div>
            <div class="text-sm font-medium">{{ $t('profile.notifications.emailEnabledTitle') }}</div>
            <div class="text-xs text-[var(--el-text-color-secondary)] mt-1">
              {{ $t('profile.notifications.emailEnabledDesc') }}
            </div>
          </div>
          <el-switch
            :model-value="preferences.email_enabled"
            :loading="saving"
            size="small"
            @change="$emit('toggle', 'email_enabled')"
          />
        </div>

        <div class="flex items-center justify-between rounded-xl border border-solid border-[#ebeef5] px-4 py-3">
          <div>
            <div class="text-sm font-medium">{{ $t('profile.notifications.bookingConfirmedTitle') }}</div>
            <div class="text-xs text-[var(--el-text-color-secondary)] mt-1">
              {{ $t('profile.notifications.bookingConfirmedDesc') }}
            </div>
          </div>
          <el-switch
            :model-value="preferences.booking_confirmed"
            :disabled="!preferences.email_enabled"
            :loading="saving"
            size="small"
            @change="$emit('toggle', 'booking_confirmed')"
          />
        </div>

        <div class="flex items-center justify-between rounded-xl border border-solid border-[#ebeef5] px-4 py-3">
          <div>
            <div class="text-sm font-medium">{{ $t('profile.notifications.bookingCancelledTitle') }}</div>
            <div class="text-xs text-[var(--el-text-color-secondary)] mt-1">
              {{ $t('profile.notifications.bookingCancelledDesc') }}
            </div>
          </div>
          <el-switch
            :model-value="preferences.booking_cancelled"
            :disabled="!preferences.email_enabled"
            :loading="saving"
            size="small"
            @change="$emit('toggle', 'booking_cancelled')"
          />
        </div>

        <div class="flex items-center justify-between rounded-xl border border-solid border-[#ebeef5] px-4 py-3">
          <div>
            <div class="text-sm font-medium">{{ $t('profile.notifications.contractActivatedTitle') }}</div>
            <div class="text-xs text-[var(--el-text-color-secondary)] mt-1">
              {{ $t('profile.notifications.contractActivatedDesc') }}
            </div>
          </div>
          <el-switch
            :model-value="preferences.contract_activated"
            :disabled="!preferences.email_enabled"
            :loading="saving"
            size="small"
            @change="$emit('toggle', 'contract_activated')"
          />
        </div>

        <div class="flex items-center justify-between rounded-xl border border-solid border-[#ebeef5] px-4 py-3">
          <div>
            <div class="text-sm font-medium">{{ $t('profile.notifications.contractConvertedTitle') }}</div>
            <div class="text-xs text-[var(--el-text-color-secondary)] mt-1">
              {{ $t('profile.notifications.contractConvertedDesc') }}
            </div>
          </div>
          <el-switch
            :model-value="preferences.contract_converted"
            :disabled="!preferences.email_enabled"
            :loading="saving"
            size="small"
            @change="$emit('toggle', 'contract_converted')"
          />
        </div>

        <div class="flex items-center justify-between rounded-xl border border-solid border-[#ebeef5] px-4 py-3">
          <div>
            <div class="text-sm font-medium">{{ $t('profile.notifications.contractTerminatedTitle') }}</div>
            <div class="text-xs text-[var(--el-text-color-secondary)] mt-1">
              {{ $t('profile.notifications.contractTerminatedDesc') }}
            </div>
          </div>
          <el-switch
            :model-value="preferences.contract_terminated"
            :disabled="!preferences.email_enabled"
            :loading="saving"
            size="small"
            @change="$emit('toggle', 'contract_terminated')"
          />
        </div>
      </div>
    </template>

    <el-empty v-else :description="$t('profile.notifications.empty')" />
  </el-card>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import type { NotificationPreferenceKey, NotificationPreferences } from '@/api/notification';

useI18n();

defineProps<{
  loading: boolean;
  saving: boolean;
  preferences: NotificationPreferences | null;
}>();

defineEmits<{
  toggle: [key: NotificationPreferenceKey];
}>();
</script>
