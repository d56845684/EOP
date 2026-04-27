<template>
  <div class="zoom-account-settings pl-2 pr-4">
    <div class="flex justify-between items-center px-1 mb-2">
      <h3 class="my-0 text-lg">{{ $t('menu.zoom_account_settings') }}</h3>
      <el-button type="primary" round size="small" class="h-30px!" @click="openCreateDrawer">
        <template #icon>
          <div class="i-hugeicons:plus-sign" />
        </template>
        {{ $t('zoomSettings.add') }}
      </el-button>
    </div>

    <el-card shadow="never" class="filter-card mb-14px">
      <el-form
        :inline="true"
        :model="queryParams"
        size="small"
        label-position="top"
        class="filter-form flex items-end"
        @submit.prevent="handleSearch"
      >
        <el-form-item :label="$t('common.status')">
          <el-select
            v-model="queryParams.is_active"
            clearable
            :placeholder="$t('common.all')"
            class="w-130px"
            @clear="handleSearch"
            @change="handleSearch"
          >
            <el-option :label="$t('common.active')" :value="true" />
            <el-option :label="$t('common.inactive')" :value="false" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" round class="h-30px!" @click="handleSearch">
            <template #icon>
              <div class="i-hugeicons:search-01" />
            </template>
            {{ $t('common.search') }}
          </el-button>
          <el-button round class="h-30px!" @click="resetQuery">
            <template #icon>
              <div class="i-hugeicons:arrow-reload-horizontal" />
            </template>
            {{ $t('common.btnReset') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="accounts" size="small" class="w-full" :empty-text="$t('zoomSettings.noAccounts')">
        <el-table-column :label="$t('zoomSettings.accountName')" min-width="260" fixed="left" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="font-600 color-[var(--el-text-color-primary)]">{{ row.account_name }}</div>
            <div class="text-10px text-[var(--el-text-color-secondary)]">
              Account ID: {{ row.zoom_account_id }}
            </div>
          </template>
        </el-table-column>

        <el-table-column label="Zoom Email" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.zoom_user_email || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="Client ID" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.zoom_client_id }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('zoomSettings.tier')" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="getTierTagType(row.account_tier)" size="small" effect="plain">
              {{ getTierLabel(row.account_tier) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="$t('common.status')" width="90" align="center">
          <template #default="{ row }">
            <div
              class="flex justify-center items-center gap-1.5"
              :class="row.is_active ? 'color-[var(--el-color-success)]' : 'color-[var(--el-color-gray)]'"
            >
              <span class="text-lg">•</span>
              {{ row.is_active ? $t('zoomSettings.activeStatus') : $t('zoomSettings.inactiveStatus') }}
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('zoomSettings.dailyUsage')" width="120" align="center">
          <template #default="{ row }">
            {{ row.daily_meeting_count || 0 }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('common.lastUpdated')" width="165" align="center">
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at || row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('zoomSettings.connectionTest')" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              plain
              round
              type="success"
              size="small"
              :loading="testingId === row.id"
              @click="handleTestConnection(row)"
            >
              <template #icon>
                <div class="i-hugeicons:connect" />
              </template>
              {{ $t('zoomSettings.test') }}
            </el-button>
          </template>
        </el-table-column>

        <el-table-column :label="$t('common.actions')" width="120" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEditDrawer(row)">
              {{ $t('common.edit') }}
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              <template #icon>
                <div class="i-hugeicons:delete-02" />
              </template>
              {{ $t('common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-footer">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.per_page"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="fetchAccounts"
          @current-change="fetchAccounts"
        />
      </div>
    </el-card>

    <el-drawer
      v-model="drawerVisible"
      size="460px"
      :title="drawerMode === 'create' ? $t('zoomSettings.createTitle') : $t('zoomSettings.editTitle')"
      @closed="resetForm"
    >
      <el-form
        ref="formRef"
        v-loading="saving"
        :model="form"
        :rules="rules"
        size="small"
        label-position="top"
      >
        <el-form-item :label="$t('zoomSettings.accountName')" prop="account_name">
          <el-input v-model="form.account_name" maxlength="100" show-word-limit :placeholder="$t('zoomSettings.accountNamePlaceholder')" />
        </el-form-item>

        <el-form-item label="Zoom Account ID" prop="zoom_account_id">
          <el-input v-model="form.zoom_account_id" maxlength="100" :placeholder="$t('zoomSettings.accountIdPlaceholder')" />
        </el-form-item>

        <el-form-item label="Zoom Client ID" prop="zoom_client_id">
          <el-input v-model="form.zoom_client_id" maxlength="200" :placeholder="$t('zoomSettings.clientIdPlaceholder')" />
        </el-form-item>

        <el-form-item label="Zoom Client Secret" prop="zoom_client_secret">
          <el-input
            v-model="form.zoom_client_secret"
            type="password"
            maxlength="200"
            show-password
            :placeholder="drawerMode === 'create' ? $t('zoomSettings.clientSecretPlaceholder') : $t('zoomSettings.secretKeepPlaceholder')"
          />
        </el-form-item>

        <el-form-item label="Zoom User Email" prop="zoom_user_email">
          <el-input v-model="form.zoom_user_email" maxlength="255" :placeholder="$t('zoomSettings.userEmailPlaceholder')" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item :label="$t('zoomSettings.tierLabel')" prop="account_tier">
              <el-select v-model="form.account_tier" class="w-full">
                <el-option label="Basic" value="basic" />
                <el-option label="Pro" value="pro" />
                <el-option label="Business" value="business" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('common.status')" prop="is_active">
              <el-switch
                v-model="form.is_active"
                inline-prompt
                :active-text="$t('common.active')"
                :inactive-text="$t('common.inactive')"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item :label="$t('common.note')">
          <el-input v-model="form.notes" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>

        <div class="flex justify-end gap-2 mt-6">
          <el-button round size="small" class="h-30px! px-5!" @click="drawerVisible = false">
            {{ $t('common.cancel') }}
          </el-button>
          <el-button
            round
            size="small"
            class="h-30px! px-5!"
            type="primary"
            :loading="saving"
            @click="handleSave"
          >
            {{ $t('common.save') }}
          </el-button>
        </div>
      </el-form>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import type { FormInstance, FormRules } from 'element-plus';
import { ElMessage, ElMessageBox } from 'element-plus';
import dayjs from 'dayjs';
import {
  createZoomAccount,
  deleteZoomAccount,
  getZoomAccountList,
  testZoomAccount,
  updateZoomAccount,
  type CreateZoomAccountData,
  type UpdateZoomAccountData,
  type ZoomAccount,
  type ZoomAccountTier,
} from '@/api/zoom';
import { assertApiSuccess } from '@/api/response';
import { useApiError } from '@/composables/useApiError';

type DrawerMode = 'create' | 'edit';
type TagType = 'primary' | 'success' | 'warning' | 'info' | 'danger' | '';
const { showApiError } = useApiError();
const { t } = useI18n();

const loading = ref(false);
const saving = ref(false);
const drawerVisible = ref(false);
const drawerMode = ref<DrawerMode>('create');
const editingAccount = ref<ZoomAccount | null>(null);
const accounts = ref<ZoomAccount[]>([]);
const total = ref(0);
const testingId = ref('');
const formRef = ref<FormInstance>();

const queryParams = reactive({
  page: 1,
  per_page: 20,
  is_active: null as boolean | null,
});

const form = reactive({
  account_name: '',
  zoom_account_id: '',
  zoom_client_id: '',
  zoom_client_secret: '',
  zoom_user_email: '',
  account_tier: 'basic' as ZoomAccountTier,
  is_active: true,
  notes: '',
});

const validateSecret = (_rule: unknown, value: string, callback: (error?: Error) => void) => {
  if (drawerMode.value === 'create' && !value.trim()) {
    callback(new Error(t('zoomSettings.secretRequired')));
    return;
  }

  callback();
};

const rules: FormRules = {
  account_name: [{ required: true, message: t('zoomSettings.accountNameRequired'), trigger: 'blur' }],
  zoom_account_id: [{ required: true, message: t('zoomSettings.accountIdRequired'), trigger: 'blur' }],
  zoom_client_id: [{ required: true, message: t('zoomSettings.clientIdRequired'), trigger: 'blur' }],
  zoom_client_secret: [{ validator: validateSecret, trigger: 'blur' }],
  account_tier: [{ required: true, message: t('zoomSettings.tierRequired'), trigger: 'change' }],
};

function formatDateTime(value?: string | null) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-';
}

function getTierLabel(tier: ZoomAccountTier) {
  const map: Record<ZoomAccountTier, string> = {
    basic: 'Basic',
    pro: 'Pro',
    business: 'Business',
  };
  return map[tier] || tier;
}

function getTierTagType(tier: ZoomAccountTier): TagType {
  if (tier === 'business') return 'warning';
  if (tier === 'pro') return 'primary';
  return 'info';
}

async function fetchAccounts() {
  loading.value = true;
  try {
    const res = assertApiSuccess(await getZoomAccountList(queryParams), t('zoomSettings.loadFailed'));
    accounts.value = res.data || [];
    total.value = res.total || 0;
  } catch (error) {
    showApiError(error, t('zoomSettings.loadFailed'));
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  queryParams.page = 1;
  fetchAccounts();
}

function resetQuery() {
  queryParams.page = 1;
  queryParams.is_active = null;
  fetchAccounts();
}

function openCreateDrawer() {
  drawerMode.value = 'create';
  editingAccount.value = null;
  drawerVisible.value = true;
}

function openEditDrawer(account: ZoomAccount) {
  drawerMode.value = 'edit';
  editingAccount.value = account;
  form.account_name = account.account_name;
  form.zoom_account_id = account.zoom_account_id;
  form.zoom_client_id = account.zoom_client_id;
  form.zoom_client_secret = '';
  form.zoom_user_email = account.zoom_user_email || '';
  form.account_tier = account.account_tier || 'basic';
  form.is_active = account.is_active;
  form.notes = account.notes || '';
  drawerVisible.value = true;
}

function resetForm() {
  editingAccount.value = null;
  form.account_name = '';
  form.zoom_account_id = '';
  form.zoom_client_id = '';
  form.zoom_client_secret = '';
  form.zoom_user_email = '';
  form.account_tier = 'basic';
  form.is_active = true;
  form.notes = '';
  formRef.value?.clearValidate();
}

function buildCreatePayload(): CreateZoomAccountData {
  return {
    account_name: form.account_name.trim(),
    zoom_account_id: form.zoom_account_id.trim(),
    zoom_client_id: form.zoom_client_id.trim(),
    zoom_client_secret: form.zoom_client_secret.trim(),
    zoom_user_email: form.zoom_user_email.trim() || null,
    account_tier: form.account_tier,
    is_active: form.is_active,
    notes: form.notes.trim() || null,
  };
}

function buildUpdatePayload(): UpdateZoomAccountData {
  const payload: UpdateZoomAccountData = {
    account_name: form.account_name.trim(),
    zoom_account_id: form.zoom_account_id.trim(),
    zoom_client_id: form.zoom_client_id.trim(),
    zoom_user_email: form.zoom_user_email.trim() || null,
    account_tier: form.account_tier,
    is_active: form.is_active,
    notes: form.notes.trim() || null,
  };

  if (form.zoom_client_secret.trim()) {
    payload.zoom_client_secret = form.zoom_client_secret.trim();
  }

  return payload;
}

async function handleSave() {
  if (!formRef.value) return;

  await formRef.value.validate(async (valid) => {
    if (!valid) return;

    saving.value = true;
    try {
      const res = drawerMode.value === 'create'
        ? assertApiSuccess(await createZoomAccount(buildCreatePayload()), t('zoomSettings.createFailed'))
        : assertApiSuccess(await updateZoomAccount(editingAccount.value!.id, buildUpdatePayload()), t('zoomSettings.updateFailed'));

      ElMessage.success(res.message || t('zoomSettings.saved'));
      drawerVisible.value = false;
      fetchAccounts();
    } catch (error) {
      showApiError(error, t('zoomSettings.saveFailed'));
    } finally {
      saving.value = false;
    }
  });
}

async function handleDelete(account: ZoomAccount) {
  try {
    await ElMessageBox.confirm(t('zoomSettings.deleteConfirmMessage', { name: account.account_name }), t('zoomSettings.deleteTitle'), {
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    });
  } catch {
    return;
  }

  try {
    const res = assertApiSuccess(await deleteZoomAccount(account.id), t('zoomSettings.deleteFailed'));
    ElMessage.success(res.message || t('zoomSettings.deleted'));
    fetchAccounts();
  } catch (error) {
    showApiError(error, t('zoomSettings.deleteFailed'));
  }
}

async function handleTestConnection(account: ZoomAccount) {
  testingId.value = account.id;
  try {
    const res = assertApiSuccess(await testZoomAccount(account.id), t('zoomSettings.testFailed'));
    ElMessage.success(res.message || t('zoomSettings.testSuccess'));
  } catch (error) {
    showApiError(error, t('zoomSettings.testFailed'));
  } finally {
    testingId.value = '';
  }
}

onMounted(() => {
  fetchAccounts();
});
</script>

<style scoped lang="scss">
.zoom-account-settings {
  :deep(.filter-form) {
    gap: 20px;
    .el-form-item {
      margin-right: 0;
      margin-bottom: 5px;
    }
  }

  .pagination-footer {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
  }
}
</style>
