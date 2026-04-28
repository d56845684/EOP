<template>
  <div class="account-list pl-2 pr-4">
    <section class="flex justify-between items-center px-1 mb-2">
      <h3 class="text-lg my-0">{{ $t('account.title') }}</h3>
    </section>

    <el-card shadow="never" class="filter-card mb-14px">
      <el-form
        :inline="true"
        :model="queryParams"
        size="small"
        label-position="top"
        class="filter-form flex items-end"
        @submit.prevent="handleSearch"
      >
        <el-form-item :label="$t('common.searchKeyword')">
          <el-input
            v-model="queryParams.search"
            :placeholder="$t('account.searchPlaceholder')"
            clearable
            class="w-260px h-30px!"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <div class="i-hugeicons:search-01" />
            </template>
          </el-input>
        </el-form-item>

        <el-form-item :label="$t('account.role')">
          <el-select
            v-model="queryParams.role"
            :placeholder="$t('common.all')"
            clearable
            class="w-150px"
            @clear="handleSearch"
            @change="handleSearch"
          >
            <el-option v-for="role in roleList" :key="role.id" :label="role.name" :value="role.key" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('common.status')">
          <el-select
            v-model="queryParams.is_active"
            :placeholder="$t('common.all')"
            clearable
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
      <el-table :data="accounts" size="small" class="w-full" v-loading="loading">
        <el-table-column prop="email" min-width="260" :label="$t('account.account')" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <el-tooltip v-if="row.is_protected" :content="$t('account.protectedAccount')" placement="top">
                <div class="i-hugeicons:lock-key text-amber" />
              </el-tooltip>
              <span class="truncate">{{ row.email }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="name" min-width="140" :label="$t('account.nickname')">
          <template #default="{ row }">
            {{ row.name || '-' }}
          </template>
        </el-table-column>

        <el-table-column prop="role" min-width="120" align="center" :label="$t('account.role')">
          <template #default="{ row }">
            <el-tag size="small" effect="light" :type="getRoleTagType(row.role)">
              {{ getRoleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="employee_subtype" min-width="120" align="center" :label="$t('account.employeeSubtype')">
          <template #default="{ row }">
            <!-- <el-tag
              v-if="row.employee_subtype"
              size="small"
              effect="plain"
              :type="EMPLOYEE_TYPE_TAG_MAP[row.employee_subtype as EmployeeType] || 'info'"
            >
              {{ formatEmployeeTypeLabel(row.employee_subtype as EmployeeType, row.employee_subtype, t) }}
            </el-tag> -->
            <span v-if="row.employee_subtype" :class="`color-${EMPLOYEE_TYPE_TAG_MAP[row.employee_subtype as EmployeeType] || 'info'}`">{{ formatEmployeeTypeLabel(row.employee_subtype as EmployeeType, row.employee_subtype, t) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column min-width="180" align="center" :label="$t('account.createdTime')">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('common.actions')" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div v-if="row.is_protected" class="flex items-center justify-center gap-1">
              <div class="i-hugeicons:square-lock-01 text-md text-gray-400" />
              <span class="text-12px text-[var(--el-text-color-secondary)]">{{ $t('account.protected') }}</span>
            </div>
            <div v-else class="flex items-center justify-center gap-1">
              <el-button
                v-if="hasPermission('employees.edit')"
                type="primary"
                link
                size="small"
                @click="openEditDrawer(row)"
              >
                {{ $t('common.edit') }}
              </el-button>

              <el-button
                v-if="canManageUserPages"
                type="success"
                plain
                round
                size="small"
                class="px-2! h-22px!"
                @click="openPermissionDrawer(row)"
              >
                <div class="flex items-center gap-0.5">
                  <div class="i-hugeicons:shield-key" />
                  {{ $t('account.permissionSettings') }}
                </div>
              </el-button>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('account.statusColumn')" width="75" fixed="right" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              :disabled="!canToggleAccountStatus(row)"
              :loading="statusUpdatingId === row.id"
              inline-prompt
              size="small"
              :before-change="() => handleStatusSwitch(row)"
            />
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
      v-model="editDrawerVisible"
      size="420px"
      :title="$t('account.editTitle')"
      @closed="resetEditForm"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editRules"
        size="small"
        label-position="top"
        v-loading="savingAccount"
      >
        <el-row>
          <el-col :span="24">
            <el-form-item :label="$t('account.account')">
              <el-input :model-value="editingAccount?.email || '-'" disabled class="w-full h-30px!" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('account.nickname')">
              <el-input :model-value="editingAccount?.name || '-'" disabled class="w-full h-30px!" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('account.role')" prop="role_id">
              <el-select v-model="editForm.role_id" class="w-full h-30px!" :placeholder="$t('account.role')">
                <el-option v-for="role in roleList" :key="role.id" :label="role.name" :value="role.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="12">
            <el-form-item v-if="shouldShowEmployeeSubtype" :label="$t('account.employeeSubtype')">
              <el-select v-model="editForm.employee_subtype" clearable class="w-full h-30px!">
                <el-option
                  v-for="type in employeeTypeOptions"
                  :key="type.value"
                  :label="type.label"
                  :value="type.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <div class="flex justify-end gap-2 mt-6">
          <el-button round size="small" class="h-30px! px-5!" @click="editDrawerVisible = false">
            {{ $t('common.cancel') }}
          </el-button>
          <el-button
            round
            size="small"
            class="h-30px! px-5!"
            type="primary"
            :loading="savingAccount"
            @click="handleSaveAccount"
          >
            {{ $t('common.save') }}
          </el-button>
        </div>
      </el-form>
    </el-drawer>

    <el-drawer
      v-model="permissionDrawerVisible"
      size="400px"
      :title="$t('account.pagePermissions')"
      @closed="resetPermissionDrawer"
    >
      <div v-if="permissionAccount" class="h-64px mb-4 rounded-2 bg-[var(--el-fill-color-light)] px-4 py-3">
        <div class="text-14px font-600 color-[var(--el-text-color-primary)]">{{ permissionAccount.email }}</div>
        <div class="text-12px color-[var(--el-text-color-secondary)] mt-1">
          {{ permissionAccount.name || '-' }} / {{ getRoleLabel(permissionAccount.role) }}
        </div>
      </div>

      <PermissionTreeEditor
        class="permission-tree-section"
        :pages="allPages"
        :checked-page-ids="effectivePermissionIds"
        :loading="permissionLoading"
        :saving="savingPermissions"
        :forced-page-keys="FORCED_PERMISSION_KEYS"
        @cancel="permissionDrawerVisible = false"
        @save="handleSavePermissions"
      />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import dayjs from 'dayjs';
import {
  deleteUserApi,
  getRolesApi,
  getUserPageOverridesApi,
  getUsersApi,
  updateUserApi,
  updateUserPageOverridesApi,
  type AccountInfo,
  type RoleInfo,
  type UserPageOverrideEntry,
} from '@/api/user';
import { getPagesApi, getRolePagesApi, type PageResponse } from '@/api/role';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { EMPLOYEE_TYPE_TAG_MAP, type DisplayTagType } from '@/constants/display';
import type { EmployeeType } from '@/api/employee';
import { usePermissionStore } from '@/stores/permission';
import { formatEmployeeTypeLabel, formatRoleLabel } from '@/utils/i18n-formatters';
import PermissionTreeEditor from './components/PermissionTreeEditor.vue';

type AccountStatusFilter = boolean | '';

interface QueryParams {
  page: number;
  per_page: number;
  search: string;
  role: string;
  is_active: AccountStatusFilter;
}

const { t } = useI18n();
const permissionStore = usePermissionStore();
const hasPermission = (permission: string) => permissionStore.hasPermission(permission);
const FORCED_PERMISSION_KEYS = ['dashboard'];

const accounts = ref<AccountInfo[]>([]);
const roles = ref<RoleInfo[]>([]);
const total = ref(0);
const loading = ref(false);
const statusUpdatingId = ref('');

const queryParams = reactive<QueryParams>({
  page: 1,
  per_page: 10,
  search: '',
  role: '',
  is_active: '',
});

const roleList = computed(() => roles.value);
const roleNameMap = computed(() => new Map(roles.value.map((role) => [role.key, role.name])));
const roleIdMap = computed(() => new Map(roles.value.map((role) => [role.id, role])));
const canManageUserPages = computed(() =>
  hasPermission('permissions.users') && hasPermission('permissions.pages') && hasPermission('permissions.roles')
);

const employeeTypeOptions = computed(() => {
  const types: EmployeeType[] = ['admin', 'full_time', 'part_time', 'intern'];
  return types.map((value) => ({
    label: formatEmployeeTypeLabel(value, value, t),
    value,
  }));
});

const editDrawerVisible = ref(false);
const savingAccount = ref(false);
const editFormRef = ref<FormInstance>();
const editingAccount = ref<AccountInfo | null>(null);
const editForm = reactive({
  role_id: '',
  employee_subtype: '' as EmployeeType | '',
  is_active: true,
});

const editRules = reactive<FormRules>({
  role_id: [{ required: true, message: t('account.roleRequired'), trigger: 'change' }],
});

const selectedEditRole = computed(() => roleIdMap.value.get(editForm.role_id));
const shouldShowEmployeeSubtype = computed(() => {
  const roleKey = selectedEditRole.value?.key;
  return roleKey === 'admin' || roleKey === 'employee' || Boolean(editingAccount.value?.employee_subtype);
});

const permissionDrawerVisible = ref(false);
const permissionLoading = ref(false);
const savingPermissions = ref(false);
const permissionAccount = ref<AccountInfo | null>(null);
const allPages = ref<PageResponse[]>([]);
const rolePageIds = ref<Set<string>>(new Set());
const pageOverrides = ref<Map<string, 'grant' | 'revoke'>>(new Map());
const pageById = computed(() => new Map(allPages.value.map((page) => [page.id, page])));

const isForcedPermissionPage = (pageId: string) => {
  const page = pageById.value.get(pageId);
  return page ? FORCED_PERMISSION_KEYS.includes(page.key) : false;
};

const effectivePermissionIds = computed(() => {
  const selected = new Set(rolePageIds.value);

  pageOverrides.value.forEach((accessType, pageId) => {
    if (accessType === 'grant') {
      selected.add(pageId);
    } else if (accessType === 'revoke') {
      selected.delete(pageId);
    }
  });

  allPages.value.forEach((page) => {
    if (FORCED_PERMISSION_KEYS.includes(page.key)) {
      selected.add(page.id);
    }
  });

  return Array.from(selected);
});

const formatTime = (time?: string | null) => (time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-');

const getRoleLabel = (role?: string | null) => {
  if (!role) return '-';
  return roleNameMap.value.get(role) || formatRoleLabel(role, role, t);
};

const getRoleTagType = (role?: string | null): DisplayTagType => {
  const tagMap: Record<string, DisplayTagType> = {
    admin: 'danger',
    employee: 'primary',
    teacher: 'success',
    student: 'warning',
  };
  return role ? tagMap[role] || 'info' : 'info';
};

const buildQueryParams = () => {
  const params: NonNullable<Parameters<typeof getUsersApi>[0]> = {
    page: queryParams.page,
    per_page: queryParams.per_page,
  };

  if (queryParams.search.trim()) params.search = queryParams.search.trim();
  if (queryParams.role) params.role = queryParams.role;
  if (queryParams.is_active !== '') params.is_active = queryParams.is_active;

  return params;
};

const fetchRoles = async () => {
  try {
    const res = assertApiSuccess(await getRolesApi(), t('account.loadRolesFailed'));
    roles.value = res.data || [];
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('account.loadRolesFailed')));
  }
};

const fetchAccounts = async () => {
  loading.value = true;
  try {
    const res = assertApiSuccess(await getUsersApi(buildQueryParams()), t('account.loadAccountsFailed'));
    accounts.value = sortProtectedAccountsFirst(res.data || []);
    total.value = res.total || 0;
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('account.loadAccountsFailed')));
  } finally {
    loading.value = false;
  }
};

const sortProtectedAccountsFirst = (accountList: AccountInfo[]) => {
  return [...accountList].sort((a, b) => Number(b.is_protected) - Number(a.is_protected));
};

const handleSearch = () => {
  queryParams.page = 1;
  fetchAccounts();
};

const resetQuery = () => {
  queryParams.search = '';
  queryParams.role = '';
  queryParams.is_active = '';
  handleSearch();
};

const openEditDrawer = (account: AccountInfo) => {
  editingAccount.value = account;
  editForm.role_id = account.role_id || '';
  editForm.employee_subtype = (account.employee_subtype || '') as EmployeeType | '';
  editForm.is_active = account.is_active;
  editDrawerVisible.value = true;
};

const resetEditForm = () => {
  editingAccount.value = null;
  editForm.role_id = '';
  editForm.employee_subtype = '';
  editForm.is_active = true;
  editFormRef.value?.clearValidate();
};

const handleSaveAccount = async () => {
  if (!editingAccount.value || !editFormRef.value) return;

  await editFormRef.value.validate(async (valid) => {
    if (!valid || !editingAccount.value) return;

    savingAccount.value = true;
    try {
      const employeeSubtype = shouldShowEmployeeSubtype.value ? editForm.employee_subtype || null : null;
      const res = assertApiSuccess(await updateUserApi(editingAccount.value.id, {
        role_id: editForm.role_id,
        employee_subtype: employeeSubtype,
        is_active: editForm.is_active,
      }), t('account.updateFailed'));

      ElMessage.success(res.message || t('account.updateSuccess'));
      editDrawerVisible.value = false;
      fetchAccounts();
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, t('account.updateFailed')));
    } finally {
      savingAccount.value = false;
    }
  });
};

const canToggleAccountStatus = (account: AccountInfo) => {
  if (account.is_protected || statusUpdatingId.value === account.id) return false;
  return account.is_active ? hasPermission('employees.delete') : hasPermission('employees.edit');
};

const handleStatusSwitch = async (account: AccountInfo) => {
  const nextActive = !account.is_active;
  try {
    await ElMessageBox.confirm(
      nextActive
        ? t('account.activateConfirmMessage', { email: account.email })
        : t('account.deactivateConfirmMessage', { email: account.email }),
      nextActive ? t('account.activateTitle') : t('account.deactivateTitle'),
      {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: nextActive ? 'info' : 'warning',
    });

    statusUpdatingId.value = account.id;
    const res = nextActive
      ? assertApiSuccess(await updateUserApi(account.id, { is_active: true }), t('account.activateFailed'))
      : assertApiSuccess(await deleteUserApi(account.id), t('account.deactivateFailed'));

    ElMessage.success(res.message || (nextActive ? t('account.activateSuccess') : t('account.deactivateSuccess')));
    fetchAccounts();
    return true;
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(getApiErrorMessage(error, nextActive ? t('account.activateFailed') : t('account.deactivateFailed')));
    }
    return false;
  } finally {
    statusUpdatingId.value = '';
  }
};

const openPermissionDrawer = async (account: AccountInfo) => {
  if (!account.role_id) {
    ElMessage.warning(t('account.noRoleWarning'));
    return;
  }

  permissionAccount.value = account;
  permissionDrawerVisible.value = true;
  permissionLoading.value = true;

  try {
    const [pagesRes, rolePagesRes, overridesRes] = await Promise.all([
      getPagesApi({ per_page: 200 }),
      getRolePagesApi(account.role_id),
      getUserPageOverridesApi(account.id),
    ]);

    const pages = assertApiSuccess(pagesRes, t('account.loadPagePermissionsFailed')).data || [];
    const rolePages = assertApiSuccess(rolePagesRes, t('account.loadRolePermissionsFailed')).pages || [];
    const overrides = assertApiSuccess(overridesRes, t('account.loadUserPermissionsFailed')).overrides || [];

    allPages.value = pages.filter((page) => page.is_active !== false);
    rolePageIds.value = new Set(rolePages.map((page) => page.id));
    pageOverrides.value = new Map(
      overrides
        .filter((override) => !isForcedPermissionPage(override.page_id))
        .map((override) => [override.page_id, override.access_type]),
    );
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('account.loadPagePermissionsFailed')));
  } finally {
    permissionLoading.value = false;
  }
};

const handleSavePermissions = async (pageIds: string[]) => {
  if (!permissionAccount.value) return;

  savingPermissions.value = true;
  try {
    const selectedPageIds = new Set(pageIds);
    const overrides: UserPageOverrideEntry[] = [];

    allPages.value.forEach((page) => {
      if (FORCED_PERMISSION_KEYS.includes(page.key)) return;

      const isSelected = selectedPageIds.has(page.id);
      const isRoleDefault = rolePageIds.value.has(page.id);

      if (isSelected && !isRoleDefault) {
        overrides.push({ page_id: page.id, access_type: 'grant' });
      } else if (!isSelected && isRoleDefault) {
        overrides.push({ page_id: page.id, access_type: 'revoke' });
      }
    });

    const res = assertApiSuccess(
      await updateUserPageOverridesApi(permissionAccount.value.id, overrides),
      t('account.savePagePermissionsFailed'),
    );

    ElMessage.success(res.message || t('account.savePagePermissionsSuccess'));
    permissionDrawerVisible.value = false;
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('account.savePagePermissionsFailed')));
  } finally {
    savingPermissions.value = false;
  }
};

const resetPermissionDrawer = () => {
  permissionAccount.value = null;
  allPages.value = [];
  rolePageIds.value = new Set();
  pageOverrides.value = new Map();
};

onMounted(() => {
  fetchRoles();
  fetchAccounts();
});
</script>

<style scoped>
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
  margin-top: 20px;
}

.permission-tree-section {
  height: calc(100% - 80px);
}
</style>
