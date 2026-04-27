<template>
  <div class="profile-page pl-2 pr-4">
    <div class="px-1 mb-4">
      <h3 class="my-0">{{ $t('menu.profile') }}</h3>
      <!-- <p class="text-sm text-[var(--el-text-color-secondary)] mt-2 mb-0">
        {{ $t('profile.intro') }}
      </p> -->
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="14" class="mb-4">
        <ProfileSummaryCard
          :loading="profileLoading"
          :user-info="authStore.userInfo"
          :profile="authStore.profile"
          :avatar-url="authStore.userAvatar"
        />
      </el-col>

      <el-col :xs="24" :lg="10" class="mb-4">
        <LineBindingCard
          :loading="lineLoading"
          :binding="lineBinding"
          :channel-label="channelLabel"
          @bind="handleBindLine"
          @unbind="handleUnbindLine"
        />
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="14" class="mb-4">
        <NotificationSettingsCard
          :loading="notificationLoading"
          :saving="notificationSaving"
          :preferences="notificationPreferences"
          @toggle="handleNotificationToggle"
        />
      </el-col>

      <el-col :xs="24" :lg="10" class="mb-4">
        <el-card shadow="never" class="h-full">
          <template #header>
            <div class="flex items-center gap-2">
              <div class="i-hugeicons:information-circle text-lg color-[#2563eb]" />
              <span class="font-medium">{{ $t('profile.lineAboutTitle') }}</span>
            </div>
          </template>

          <div class="space-y-3 text-sm leading-6 text-[var(--el-text-color-regular)]">
            <p class="mt-0">
              {{ $t('profile.lineAboutDesc1') }}
            </p>
            <p class="m-0">
              {{ $t('profile.lineAboutDesc2') }}
            </p>
            <p class="m-0">
              {{ $t('profile.lineAboutDesc3') }}
            </p>

            <el-divider class="my-3!" />

            <div class="rounded-xl bg-[#f6f8fc] px-4 py-3">
              <div class="font-medium mb-2">{{ $t('profile.lineTipsTitle') }}</div>
              <ul class="pl-4 my-0">
                <li>{{ $t('profile.lineTips.first') }}</li>
                <li>{{ $t('profile.lineTips.second') }}</li>
                <li>{{ $t('profile.lineTips.third') }}</li>
              </ul>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import {
  getLineBindingStatusApi,
  getLineBindUrlApi,
  unbindLineApi,
  type LineBindingStatus,
} from '@/api/line';
import {
  getNotificationPreferencesApi,
  updateNotificationPreferencesApi,
  type NotificationPreferenceKey,
  type NotificationPreferences,
} from '@/api/notification';
import { formatRoleLabel } from '@/utils/i18n-formatters';
import ProfileSummaryCard from './components/ProfileSummaryCard.vue';
import LineBindingCard from './components/LineBindingCard.vue';
import NotificationSettingsCard from './components/NotificationSettingsCard.vue';

const authStore = useAuthStore();
const { t } = useI18n();

const profileLoading = ref(false);
const lineLoading = ref(false);
const notificationLoading = ref(false);
const notificationSaving = ref(false);

const lineBinding = ref<LineBindingStatus | null>(null);
const notificationPreferences = ref<NotificationPreferences | null>(null);

const channelLabel = computed(() => {
  const role = authStore.userInfo?.role || authStore.profile?.role || 'student';
  return formatRoleLabel(role);
});

const fetchProfileContext = async () => {
  profileLoading.value = true;
  try {
    if (!authStore.userInfo) {
      await authStore.checkAuth();
    }
    if (!authStore.profile) {
      await authStore.fetchProfile();
    }
  } finally {
    profileLoading.value = false;
  }
};

const fetchLineBinding = async () => {
  lineLoading.value = true;
  try {
    const res = assertApiSuccess(await getLineBindingStatusApi(), t('profile.line.loadStatusFailed'));
    lineBinding.value = res.data || null;
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('profile.line.loadStatusFailed')));
  } finally {
    lineLoading.value = false;
  }
};

const fetchNotificationPreferences = async () => {
  notificationLoading.value = true;
  try {
    const res = assertApiSuccess(await getNotificationPreferencesApi(), t('profile.notifications.loadFailed'));
    notificationPreferences.value = res.data;
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('profile.notifications.loadFailed')));
  } finally {
    notificationLoading.value = false;
  }
};

const handleBindLine = async () => {
  try {
    const res = assertApiSuccess(await getLineBindUrlApi(), t('profile.line.bindUrlFailed'));
    const bindUrl = res.data?.bind_url;

    if (!bindUrl) {
      ElMessage.warning(res.message || t('profile.line.bindUrlUnavailable'));
      return;
    }

    window.location.href = bindUrl;
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('profile.line.bindUrlFailed')));
  }
};

const handleUnbindLine = async () => {
  try {
    await ElMessageBox.confirm(t('profile.line.unbindConfirmMessage'), t('profile.line.unbindConfirmTitle'), {
      type: 'warning',
      confirmButtonText: t('profile.line.unbindConfirmAction'),
      cancelButtonText: t('common.cancel'),
    });

    const res = assertApiSuccess(await unbindLineApi(), t('profile.line.unbindFailed'));
    ElMessage.success(res.message || t('profile.line.unbindSuccess'));
    await fetchLineBinding();
  } catch (error) {
    if (error === 'cancel' || error === 'close') return;
    ElMessage.error(getApiErrorMessage(error, t('profile.line.unbindFailed')));
  }
};

const handleNotificationToggle = async (key: NotificationPreferenceKey) => {
  if (!notificationPreferences.value) return;

  const nextPreferences: NotificationPreferences = {
    ...notificationPreferences.value,
    [key]: !notificationPreferences.value[key],
  };

  if (key === 'email_enabled' && !nextPreferences.email_enabled) {
    nextPreferences.booking_confirmed = false;
    nextPreferences.booking_cancelled = false;
    nextPreferences.contract_activated = false;
    nextPreferences.contract_converted = false;
    nextPreferences.contract_terminated = false;
  }

  notificationPreferences.value = nextPreferences;
  notificationSaving.value = true;

  try {
    const res = assertApiSuccess(
      await updateNotificationPreferencesApi(nextPreferences),
      t('profile.notifications.updateFailed'),
    );
    notificationPreferences.value = res.data;
    ElMessage.success(res.message || t('profile.notifications.updated'));
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('profile.notifications.updateFailed')));
    await fetchNotificationPreferences();
  } finally {
    notificationSaving.value = false;
  }
};

onMounted(async () => {
  await fetchProfileContext();
  await Promise.all([fetchLineBinding(), fetchNotificationPreferences()]);
});
</script>
