<template>
  <div class="employee-list-page pl-2 pr-4">
    <div class="flex justify-between items-center px-1 mb-2">
      <h3 class="my-0 text-lg">{{ $t('menu.employee_settings') }}</h3>
      <el-button
        v-if="hasPermission('employees.create')"
        type="primary"
        round
        size="small"
        class="h-30px! px-2"
        @click="openCreateDrawer"
      >
        <template #icon>
          <div class="i-hugeicons:plus-sign-square" />
        </template>
        {{ $t('employee.add') }}
      </el-button>
    </div>

    <el-card shadow="never" class="mb-14px">
      <el-form
        :inline="true"
        :model="queryParams"
        size="small"
        label-position="top"
        class="filter-form flex items-end"
        @submit.prevent="handleSearch"
      >
        <el-form-item :label="$t('common.searchKeyword')" class="mb-0">
          <el-input
            v-model="queryParams.search"
            :placeholder="$t('employee.searchPlaceholder')"
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
        <el-form-item :label="$t('employee.filter.type')">
          <el-select
            v-model="queryParams.employee_type"
            clearable
            class="w-150px"
            @clear="handleSearch"
            @change="handleSearch"
          >
            <el-option :label="$t('common.all')" value="" />
            <el-option
              v-for="option in employeeTypeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('common.status')">
          <el-select
            v-model="queryParams.is_active"
            class="w-120px"
            @change="handleSearch"
          >
            <el-option :label="$t('common.all')" value="all" />
            <el-option :label="$t('common.active')" :value="true" />
            <el-option :label="$t('common.inactive')" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item class="mb-0">
          <el-button type="primary" round class="h-30px!" @click="handleSearch">
            <template #icon>
              <div class="i-hugeicons:search-01" />
            </template>
            {{ $t('common.search') }}
          </el-button>
          <el-button round class="h-30px!" @click="handleReset">
            <template #icon>
              <div class="i-hugeicons:arrow-reload-horizontal" />
            </template>
            {{ $t('common.btnReset') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="employees" size="small" class="w-full">
        <el-table-column prop="employee_no" :label="$t('employee.employeeNo')" min-width="150" />
        <el-table-column prop="name" :label="$t('common.name')" min-width="160" />
        <el-table-column prop="email" :label="$t('common.email')" min-width="260">
          <template #default="{ row }">
            <div class="flex items-center gap-6px">
              <div class="i-hugeicons:mail-01 w-12px h-12px color-gray-500 flex-shrink-0" />
              <el-text class="text-xs" truncated>{{ row.email }}</el-text>
              <el-button type="text" size="small" round class="!px-1" @click="copyEmail(row.email)">
                <template #icon>
                  <div class="i-hugeicons:copy-01" />
                </template>
              </el-button>
            </div>

          </template>
        </el-table-column>
        <el-table-column :label="$t('employee.employeeType')" min-width="140" align="center">
          <template #default="{ row }">
            <el-tag :type="EMPLOYEE_TYPE_TAG_MAP[row.employee_type as EmployeeType] || 'info'" size="small" effect="light">
              {{ getEmployeeTypeLabel(row.employee_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('employee.role')" min-width="140" align="center">
          <template #default="{ row }">
            {{ row.role_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.verify')" min-width="140" align="center">
          <template #default="{ row }">
            <template v-if="row.email_verified_at">
              <div class="flex items-center justify-center gap-2px color-[var(--el-color-success)]">
                <div class="i-hugeicons:checkmark-badge-01 w-14px h-14px" />
                <span>{{ $t('common.verified') }}</span>
              </div>
            </template>
            <template v-else>
              <el-button
                v-if="hasPermission('employees.edit')"
                type="text"
                size="small"
                @click="handleVerify(row)"
              >
                {{ $t('common.verify') }}
              </el-button>
              <el-tag v-else size="small" type="info" effect="plain">
                {{ $t('common.unverified') }}
              </el-tag>
            </template>
          </template>
        </el-table-column>
        <el-table-column :label="$t('employee.hireDate')" min-width="140" align="center">
          <template #default="{ row }">
            {{ formatDate(row.hire_date) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')" width="100" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              v-if="hasPermission('employees.edit')"
              type="primary"
              link
              size="small"
              @click="openEditDrawer(row)"
            >
              {{ $t('common.edit') }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.status')" width="85" align="center" fixed="right">
          <template #default="{ row }">
            <el-switch
              v-if="hasPermission('employees.edit')"
              :model-value="row.is_active"
              size="small"
              :loading="statusChangingIds.has(row.id)"
              inline-prompt
              :before-change="() => handleToggleStatus(row)"
            />
            <el-tag v-else :type="row.is_active ? 'success' : 'info'" size="small" effect="light">
              {{ row.is_active ? $t('common.active') : $t('common.inactive') }}
            </el-tag>
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
          size="small"
          @size-change="fetchEmployees"
          @current-change="fetchEmployees"
        />
      </div>
    </el-card>

    <el-drawer
      v-model="drawerVisible"
      :title="drawerMode === 'create' ? $t('employee.addTitle') : `${$t('employee.editTitle')} - ${form.name}`"
      size="460px"
      destroy-on-close
      @closed="handleDrawerClosed"
    >
      <el-skeleton v-if="drawerLoading" :rows="8" animated />
      <el-form
        v-else
        ref="formRef"
        :model="form"
        :rules="rules"
        size="small"
        label-position="top"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('employee.employeeNo')" prop="employee_no">
              <el-input v-model="form.employee_no" :disabled="drawerMode === 'edit'" class="h-30px!" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('employee.employeeType')" prop="employee_type">
              <el-select v-model="form.employee_type" class="w-full!">
                <el-option
                  v-for="option in employeeTypeOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('common.name')" prop="name">
              <el-input v-model="form.name" class="h-30px!" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('common.email')" prop="email">
              <el-input v-model="form.email" class="h-30px!" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('common.phone')">
              <el-input v-model="form.phone" class="h-30px!" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('employee.hireDate')" prop="hire_date">
              <el-date-picker
                v-model="form.hire_date"
                type="date"
                value-format="YYYY-MM-DD"
                class="w-full! h-30px!"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item :label="$t('common.address')">
              <el-input v-model="form.address" class="h-30px!" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('employee.terminationDate')">
              <el-date-picker
                v-model="form.termination_date"
                type="date"
                value-format="YYYY-MM-DD"
                class="w-full! h-30px!"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('employee.role')">
              <el-select
                v-model="form.role_id"
                class="w-full!"
                :disabled="drawerMode === 'create' || !currentEmployee?.has_account"
                :placeholder="currentEmployee?.has_account ? $t('employee.rolePlaceholder') : $t('employee.noAccountPlaceholder')"
              >
                <el-option
                  v-for="role in roles"
                  :key="role.id"
                  :label="role.name"
                  :value="role.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button round size="small" class="h-30px! px-5!" @click="drawerVisible = false">
          {{ $t('common.cancel') }}
        </el-button>
        <el-button type="primary" round size="small" class="h-30px! px-5!" :loading="saving" @click="handleSave">
          {{ $t('common.save') }}
        </el-button>
      </template>
    </el-drawer>

    <el-dialog
      v-model="inviteDialogVisible"
      :title="$t('employee.inviteTitle')"
      width="520px"
      destroy-on-close
      @closed="handleInviteDialogClosed"
    >
      <template v-if="inviteTarget">
        <div class="mb-4">
          <div class="text-xs text-[#606266] mb-1">{{ $t('employee.inviteTarget') }}</div>
          <div class="font-medium text-sm">{{ inviteTarget.name }} ({{ inviteTarget.email }})</div>
        </div>

        <el-form label-position="top" size="small">
          <el-form-item :label="$t('employee.role')">
            <el-select
              v-model="inviteRoleId"
              clearable
              class="w-200px!"
              :placeholder="$t('employee.rolePlaceholder')"
            >
              <el-option
                v-for="role in roles"
                :key="role.id"
                :label="`${role.name} (${role.key})`"
                :value="role.id"
              />
            </el-select>
            <div class="text-xs text-[var(--el-text-color-secondary)] mt-1">
              {{ $t('employee.inviteRoleHelp') }}
            </div>
          </el-form-item>

          <el-form-item v-if="inviteUrl" :label="$t('employee.inviteLinkLabel')" class="mb-0">
            <el-input :model-value="inviteUrl" readonly class="h-30px!">
              <template #append>
                <el-button @click="handleCopyInviteLink" class="h-30px!">
                  <template #icon>
                    <div class="i-hugeicons:copy-01" />
                  </template>
                  {{ $t('common.copy') }}
                </el-button>
              </template>
            </el-input>
            <div class="text-xs text-[var(--el-text-color-secondary)] mt-1">
              {{ $t('employee.inviteExpiry') }}
            </div>
          </el-form-item>
        </el-form>
      </template>

      <template #footer>
        <el-button round size="small" class="h-30px! px-4!" @click="inviteDialogVisible = false">
          <template #icon>
            <div class="i-hugeicons:cancel-circle-half-dot" />
          </template>
          {{ $t('common.close') }}
        </el-button>
        <el-button
          v-if="inviteTarget"
          type="primary"
          round
          size="small"
          class="h-30px! px-4!"
          :loading="inviteLoading"
          @click="handleGenerateInvite"
        >
          {{ inviteUrl ? $t('employee.resendInvite') : $t('employee.inviteGenerate') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import dayjs from 'dayjs';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { generateInviteLinkApi } from '@/api/auth';
import {
  createEmployeeApi,
  deleteEmployeeApi,
  getEmployeeApi,
  getEmployeeRolesApi,
  getEmployeesApi,
  updateEmployeeApi,
  type Employee,
  type EmployeeCreate,
  type EmployeeRole,
  type EmployeeType,
  type EmployeeUpdate,
} from '@/api/employee';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { EMPLOYEE_TYPE_TAG_MAP } from '@/constants/display';
import { copyToClipboardUtil } from '@/utils/clipboard';
import { formatEmployeeTypeLabel } from '@/utils/i18n-formatters';
import { usePermissionStore } from '@/stores/permission';
import { useI18n } from 'vue-i18n';

type DrawerMode = 'create' | 'edit';
type QueryStatus = 'all' | boolean;

interface EmployeeForm {
  employee_no: string;
  employee_type: EmployeeType;
  name: string;
  email: string;
  phone: string;
  address: string;
  hire_date: string;
  termination_date: string;
  role_id: string;
  is_active: boolean;
}

const { t } = useI18n();
const permissionStore = usePermissionStore();
const hasPermission = (permission: string) => permissionStore.hasPermission(permission);

const employees = ref<Employee[]>([]);
const roles = ref<EmployeeRole[]>([]);
const total = ref(0);
const loading = ref(false);
const drawerVisible = ref(false);
const drawerLoading = ref(false);
const drawerMode = ref<DrawerMode>('create');
const saving = ref(false);
const currentEmployee = ref<Employee | null>(null);
const statusChangingIds = ref(new Set<string>());
const formRef = ref<FormInstance>();
const inviteDialogVisible = ref(false);
const inviteLoading = ref(false);
const inviteTarget = ref<Employee | null>(null);
const inviteRoleId = ref('');
const inviteUrl = ref('');

const queryParams = reactive({
  page: 1,
  per_page: 10,
  search: '',
  is_active: 'all' as QueryStatus,
  employee_type: '' as EmployeeType | '',
});

const form = reactive<EmployeeForm>({
  employee_no: '',
  employee_type: 'full_time',
  name: '',
  email: '',
  phone: '',
  address: '',
  hire_date: '',
  termination_date: '',
  role_id: '',
  is_active: true,
});

const rules = reactive<FormRules<EmployeeForm>>({
  employee_no: [{ required: true, message: t('employee.employeeNoRequired'), trigger: 'blur' }],
  employee_type: [{ required: true, message: t('employee.employeeTypeRequired'), trigger: 'change' }],
  name: [{ required: true, message: t('employee.nameRequired'), trigger: 'blur' }],
  email: [
    { required: true, message: t('employee.emailRequired'), trigger: 'blur' },
    { type: 'email', message: t('employee.emailInvalid'), trigger: ['blur', 'change'] },
  ],
  hire_date: [{ required: true, message: t('employee.hireDateRequired'), trigger: 'change' }],
});

const employeeTypeOptions = computed(() => [
  { label: formatEmployeeTypeLabel('admin', 'admin', t), value: 'admin' as EmployeeType },
  { label: formatEmployeeTypeLabel('full_time', 'full_time', t), value: 'full_time' as EmployeeType },
  { label: formatEmployeeTypeLabel('part_time', 'part_time', t), value: 'part_time' as EmployeeType },
  { label: formatEmployeeTypeLabel('intern', 'intern', t), value: 'intern' as EmployeeType },
]);

const getEmployeeTypeLabel = (type?: EmployeeType) => {
  return formatEmployeeTypeLabel(type, '-', t);
};

const formatDate = (value?: string | null) => (value ? dayjs(value).format('YYYY-MM-DD') : '-');

const normalizeText = (value?: string | null) => (value || '').trim();
const normalizeDate = (value?: string | null) => value || '';

const resetForm = () => {
  form.employee_no = '';
  form.employee_type = 'full_time';
  form.name = '';
  form.email = '';
  form.phone = '';
  form.address = '';
  form.hire_date = '';
  form.termination_date = '';
  form.role_id = '';
  form.is_active = true;
  currentEmployee.value = null;
  formRef.value?.clearValidate();
};

const fillForm = (employee: Employee) => {
  form.employee_no = employee.employee_no || '';
  form.employee_type = employee.employee_type || 'full_time';
  form.name = employee.name || '';
  form.email = employee.email || '';
  form.phone = employee.phone || '';
  form.address = employee.address || '';
  form.hire_date = employee.hire_date || '';
  form.termination_date = employee.termination_date || '';
  form.role_id = employee.role_id || '';
  form.is_active = employee.is_active;
};

const fetchRoles = async () => {
  try {
    const res = assertApiSuccess(await getEmployeeRolesApi(), t('employee.loadRolesFailed'));
    roles.value = res.data || [];
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('employee.loadRolesFailed')));
  }
};

const fetchEmployees = async () => {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {
      page: queryParams.page,
      per_page: queryParams.per_page,
      search: queryParams.search || undefined,
      is_active: queryParams.is_active === 'all' ? undefined : queryParams.is_active,
      employee_type: queryParams.employee_type || undefined,
    };

    const res = assertApiSuccess(await getEmployeesApi(params), t('employee.loadListFailed'));
    employees.value = res.data || [];
    total.value = res.total || 0;
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('employee.loadListFailed')));
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  queryParams.page = 1;
  fetchEmployees();
};

const handleReset = () => {
  queryParams.page = 1;
  queryParams.per_page = 10;
  queryParams.search = '';
  queryParams.is_active = 'all';
  queryParams.employee_type = '';
  fetchEmployees();
};

const openCreateDrawer = () => {
  drawerMode.value = 'create';
  drawerLoading.value = false;
  resetForm();
  drawerVisible.value = true;
};

const openEditDrawer = async (employee: Employee) => {
  drawerMode.value = 'edit';
  drawerVisible.value = true;
  drawerLoading.value = true;
  resetForm();

  try {
    const res = assertApiSuccess(await getEmployeeApi(employee.id), t('employee.loadDetailFailed'));
    currentEmployee.value = res.data;
    fillForm(res.data);
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('employee.loadDetailFailed')));
    drawerVisible.value = false;
  } finally {
    drawerLoading.value = false;
  }
};

const buildCreatePayload = (): EmployeeCreate => {
  const payload: EmployeeCreate = {
    employee_no: normalizeText(form.employee_no),
    employee_type: form.employee_type,
    name: normalizeText(form.name),
    email: normalizeText(form.email),
    hire_date: form.hire_date,
    is_active: form.is_active,
  };

  if (normalizeText(form.phone)) payload.phone = normalizeText(form.phone);
  if (normalizeText(form.address)) payload.address = normalizeText(form.address);
  if (normalizeDate(form.termination_date)) payload.termination_date = form.termination_date;

  return payload;
};

const buildUpdatePayload = (): EmployeeUpdate => {
  const employee = currentEmployee.value;
  if (!employee) return {};

  const payload: EmployeeUpdate = {};

  if (form.employee_type !== employee.employee_type) payload.employee_type = form.employee_type;
  if (normalizeText(form.name) !== normalizeText(employee.name)) payload.name = normalizeText(form.name);
  if (normalizeText(form.email) !== normalizeText(employee.email)) payload.email = normalizeText(form.email);
  if (normalizeText(form.phone) !== normalizeText(employee.phone)) payload.phone = normalizeText(form.phone) || undefined;
  if (normalizeText(form.address) !== normalizeText(employee.address)) payload.address = normalizeText(form.address) || undefined;
  if (normalizeDate(form.hire_date) !== normalizeDate(employee.hire_date)) payload.hire_date = form.hire_date || undefined;
  if (normalizeDate(form.termination_date) !== normalizeDate(employee.termination_date)) {
    payload.termination_date = form.termination_date || undefined;
  }
  if (form.is_active !== employee.is_active) payload.is_active = form.is_active;
  if (employee.has_account && form.role_id && form.role_id !== (employee.role_id || '')) {
    payload.role_id = form.role_id;
  }

  return payload;
};

const handleSave = async () => {
  if (!formRef.value) return;

  const isValid = await formRef.value.validate().catch(() => false);
  if (!isValid) return;

  saving.value = true;
  try {
    if (drawerMode.value === 'create') {
      const res = assertApiSuccess(await createEmployeeApi(buildCreatePayload()), t('employee.createFailed'));
      ElMessage.success(res.message || t('common.addSuccess'));
    } else if (currentEmployee.value) {
      const payload = buildUpdatePayload();
      if (Object.keys(payload).length === 0) {
        ElMessage.info(t('employee.noChanges'));
        return;
      }
      const res = assertApiSuccess(await updateEmployeeApi(currentEmployee.value.id, payload), t('employee.updateFailed'));
      ElMessage.success(res.message || t('common.updateSuccess'));
    }

    drawerVisible.value = false;
    fetchEmployees();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, drawerMode.value === 'create' ? t('employee.createFailed') : t('employee.updateFailed')));
  } finally {
    saving.value = false;
  }
};

const handleToggleStatus = async (employee: Employee) => {
  statusChangingIds.value.add(employee.id);
  try {
    const nextStatus = !employee.is_active;
    const res = assertApiSuccess(
      await updateEmployeeApi(employee.id, { is_active: nextStatus }),
      t('employee.updateStatusFailed'),
    );
    employee.is_active = res.data?.is_active ?? nextStatus;
    ElMessage.success(res.message || t('common.updateSuccess'));
    return true;
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('employee.updateStatusFailed')));
    return false;
  } finally {
    statusChangingIds.value.delete(employee.id);
  }
};

const copyEmail = (email: string) => {
  copyToClipboardUtil(email, 'Email 已複製');
}

const handleDrawerClosed = () => {
  drawerLoading.value = false;
  resetForm();
};

const openInviteDialog = (employee: Employee) => {
  inviteTarget.value = employee;
  inviteRoleId.value = employee.role_id || '';
  inviteUrl.value = '';
  inviteDialogVisible.value = true;
};

const handleVerify = (employee: Employee) => {
  openInviteDialog(employee);
};

const handleGenerateInvite = async () => {
  if (!inviteTarget.value) return;

  inviteLoading.value = true;
  try {
    const res = await generateInviteLinkApi({
      entity_type: 'employee',
      entity_id: inviteTarget.value.id,
      role_id: inviteRoleId.value || undefined,
    });

    if (res.success === false) {
      throw res;
    }

    inviteUrl.value = res.invite_url || '';
    ElMessage.success(res.message || t('employee.inviteCreated'));
    await fetchEmployees();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('employee.inviteFailed')));
  } finally {
    inviteLoading.value = false;
  }
};

const handleCopyInviteLink = () => {
  if (!inviteUrl.value) return;
  copyToClipboardUtil(inviteUrl.value, t('employee.inviteCopied'));
};

const handleInviteDialogClosed = () => {
  inviteLoading.value = false;
  inviteTarget.value = null;
  inviteRoleId.value = '';
  inviteUrl.value = '';
};

onMounted(() => {
  fetchRoles();
  fetchEmployees();
});
</script>

<style lang="scss" scoped>
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
</style>
