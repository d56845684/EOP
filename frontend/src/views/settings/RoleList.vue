<template>
  <div class="role-list pl-2 pr-4">
    <div class="flex justify-between items-center px-1 mb-2">
      <h3 class="my-0 text-lg">{{ $t('menu.role_settings') }}</h3>
      <el-button
        v-if="hasPermission('permissions.roles')"
        type="primary"
        size="small"
        round
        class="h-30px! px-2"
        @click="handleCreate"
      >
        <template #icon>
          <div class="i-hugeicons:plus-sign-square" />
        </template>
        {{ $t('role.add') }}
      </el-button>
    </div>
    <el-card shadow="never">
      <el-table 
        :data="tableData" 
        size="small" 
        class="w-full" 
        v-loading="loading" 
        border 
        stripe
      >
        <el-table-column 
          prop="name" 
          :label="$t('role.roleName')" 
          min-width="80" 
        />
        <el-table-column 
          prop="key" 
          :label="$t('role.roleKey')" 
          width="120" 
          align="center"
        >
          <template #default="{ row }">
            <el-tag 
              size="small" 
              :type="roleColor[row.key] || 'info'" 
              class="font-size-10px"
            >
              <div class="flex items-center gap-1">
                <i v-if="row.is_system" class="i-hugeicons:security-lock font-size-11px" />
                {{ row.key }}
              </div>
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" :label="$t('role.description')" min-width="200" />
        <!-- <el-table-column :label="$t('role.pageCount')" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.page_count ? 'success' : 'info'">{{ row.page_count || 0 }}</el-tag>
          </template>
        </el-table-column> -->
        <!-- <el-table-column :label="$t('role.systemRole')" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_system" type="danger" effect="dark">{{ $t('common.yes') }}</el-tag>
            <span v-else class="text-gray-400">-</span>
          </template>
        </el-table-column> -->
        <el-table-column 
          :label="$t('common.actions')" 
          min-width="200" 
          fixed="right" 
          align="center"
        >
          <template #default="{ row }">
            <el-space 
              v-if="!needLock(row)" 
              :size="10" 
              style="width: 100%; justify-content: center;"
            >
              <div class="flex justify-center gap-1">
                <el-button
                  v-if="hasPermission('permissions.roles')"
                  round
                  size="small"
                  type="success"
                  plain
                  @click="handlePermission(row)"
                >
                  <template #icon><div class="i-hugeicons:shield-key" /></template>
                  {{ $t('role.settings') }}
                </el-button>
                <el-button
                  v-if="hasPermission('permissions.roles')"
                  size="small"
                  type="primary"
                  link
                  @click="handleEdit(row)"
                >
                  {{ $t('common.edit') }}
                </el-button>
              </div>
              <!-- <el-popconfirm
                :title="$t('common.confirm') + $t('common.delete') + '?'"
                @confirm="handleDelete(row)"
              >
                <template #reference>
                  <el-button 
                    v-if="hasPermission('permissions.roles')" 
                    link 
                    size="small" 
                    type="danger" 
                  >
                    <div class="i-hugeicons:delete-02 mr-2px" />
                    {{ $t('common.delete') }}
                  </el-button>
                </template>
              </el-popconfirm> -->
            </el-space>
            <div v-else class="flex items-center justify-center gap-1">
              <div class="i-hugeicons:square-lock-01 text-md text-gray-400" />
              <span class="text-12px text-[var(--el-text-color-secondary)]">{{ $t('role.protected') }}</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Role Form Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? $t('role.editTitle') : $t('role.addTitle')"
      width="500px"
      @closed="resetForm"
    >
      <el-form 
        ref="formRef" 
        :model="form" 
        size="small" 
        :rules="rules" 
        label-width="100px"
      >
        <el-form-item :label="$t('role.roleKey')" prop="key">
          <el-input 
            v-model="form.key" 
            :disabled="isEdit" 
            :placeholder="$t('role.placeholder.roleKey')"
            class="h-30px!" 
          />
        </el-form-item>
        <el-form-item :label="$t('role.roleName')" prop="name">
          <el-input 
            v-model="form.name" 
            :placeholder="$t('role.placeholder.roleName')"
            class="h-30px!" 
          />
        </el-form-item>
        <el-form-item :label="$t('role.description')" prop="description">
          <el-input 
            v-model="form.description" 
            type="textarea" 
            :rows="3" 
            :placeholder="$t('role.placeholder.description')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button 
            size="small" 
            round 
            class="h-30px! px-4!" 
            @click="dialogVisible = false"
          >
            {{ $t('common.cancel') }}
          </el-button>
          <el-button 
            size="small" 
            round 
            class="h-30px! px-4!" 
            type="primary" 
            :loading="submitLoading" 
            @click="submitForm"
          >
            {{ $t('common.confirm') }}
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Permission Drawer -->
    <el-drawer
      v-model="drawerVisible"
      :title="`${$t('role.settings')} - ${currentRole?.name}`"
      size="400px"
      destroy-on-close
    >
      <PermissionTreeEditor
        :pages="permissionPages"
        :checked-page-ids="checkedPageIds"
        :loading="treeLoading"
        :saving="saveTreeLoading"
        :forced-page-keys="FORCED_CHECKED_KEYS"
        @cancel="drawerVisible = false"
        @save="savePermissions"
      />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import type { FormInstance, FormRules } from 'element-plus';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import {
  getRolesApi, createRoleApi, updateRoleApi, deleteRoleApi,
  getPagesApi, getRolePagesApi, updateRolePagesApi
} from '@/api/role';
import type { RoleInfo, RoleCreate, RoleUpdate, PageResponse } from '@/api/role';
import PermissionTreeEditor from './components/PermissionTreeEditor.vue';
import { usePermissionStore } from '@/stores/permission';

const { t } = useI18n();

const permissionStore = usePermissionStore();
const hasPermission = (permission: string) => permissionStore.hasPermission(permission);

// --- Role List State ---
const loading = ref(false);
const tableData = ref<RoleInfo[]>([]);
const roleColor: Record<string, string> = {
  'admin': 'danger',
  'teacher': 'success',
  'student': 'warning',
  'employee': 'primary',
}

// --- Form State ---
const dialogVisible = ref(false);
const isEdit = ref(false);
const submitLoading = ref(false);
const formRef = ref<FormInstance>();
const form = reactive<RoleCreate & { id?: string }>({
  key: '',
  name: '',
  description: '',
});

const rules = reactive<FormRules>({
  key: [{ required: true, message: t('role.required'), trigger: 'blur' }],
  name: [{ required: true, message: t('role.required'), trigger: 'blur' }],
});

// --- Permission Tree State ---
const drawerVisible = ref(false);
const treeLoading = ref(false);
const saveTreeLoading = ref(false);
const currentRole = ref<RoleInfo | null>(null);
const permissionPages = ref<PageResponse[]>([]);
const checkedPageIds = ref<string[]>([]);

const FORCED_CHECKED_KEYS = ['dashboard'];

// --- Methods ---

const needLock = (row: RoleInfo) => {
  return ['admin', 'teacher', 'student', 'employee'].includes(row.key)
}

const fetchRoles = async () => {
  loading.value = true;
  try {
    const res = assertApiSuccess(await getRolesApi(), t('role.loadFailed'));
    tableData.value = res.data || [];
  } catch (error) {
    console.error('Failed to fetch roles:', error);
    ElMessage.error(getApiErrorMessage(error, t('role.loadFailed')));
  } finally {
    loading.value = false;
  }
};

const handleCreate = () => {
  isEdit.value = false;
  dialogVisible.value = true;
};

const handleEdit = (row: RoleInfo) => {
  isEdit.value = true;
  form.id = row.id;
  form.key = row.key;
  form.name = row.name;
  form.description = row.description || '';
  dialogVisible.value = true;
};

// const handleDelete = async (row: RoleInfo) => {
//   try {
//     const res = assertApiSuccess(await deleteRoleApi(row.id), t('role.deleteFailed'));
//     ElMessage.success(res.message || t('common.done'));
//     fetchRoles();
//   } catch (error) {
//     console.error('Failed to delete role:', error);
//     ElMessage.error(getApiErrorMessage(error, t('role.deleteFailed')));
//   }
// };

const resetForm = () => {
  if (formRef.value) formRef.value.resetFields();
  form.id = undefined;
  form.key = '';
  form.name = '';
  form.description = '';
};

const submitForm = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true;
      try {
        if (isEdit.value && form.id) {
          const updateData: RoleUpdate = {
            name: form.name,
            description: form.description,
          };
          const res = assertApiSuccess(await updateRoleApi(form.id, updateData), t('role.updateFailed'));
          ElMessage.success(res.message || t('common.done'));
        } else {
          const res = assertApiSuccess(await createRoleApi(form), t('role.createFailed'));
          ElMessage.success(res.message || t('common.done'));
        }
        dialogVisible.value = false;
        fetchRoles();
      } catch (error) {
        console.error('Failed to save role:', error);
        ElMessage.error(getApiErrorMessage(error, t('role.saveFailed')));
      } finally {
        submitLoading.value = false;
      }
    }
  });
};

const handlePermission = async (row: RoleInfo) => {
  currentRole.value = row;
  permissionPages.value = [];
  checkedPageIds.value = [];
  drawerVisible.value = true;
  treeLoading.value = true;
  try {
    const pagesRes = assertApiSuccess(await getPagesApi(), t('role.loadPagePermissionsFailed'));
    permissionPages.value = pagesRes.data || [];

    const rolePagesRes = assertApiSuccess(await getRolePagesApi(row.id), t('role.loadRolePermissionsFailed'));
    const existingPages = rolePagesRes?.pages || [];
    checkedPageIds.value = existingPages.map((page) => page.id);

  } catch (error) {
    console.error('Failed to load permissions:', error);
    ElMessage.error(getApiErrorMessage(error, t('role.loadPagePermissionsFailed')));
  } finally {
    treeLoading.value = false;
  }
};

const savePermissions = async (pageIds: string[]) => {
  if (!currentRole.value) return;
  
  saveTreeLoading.value = true;
  try {
    const res = assertApiSuccess(await updateRolePagesApi({
      role_id: currentRole.value.id,
      page_ids: pageIds,
    }), t('role.savePermissionsFailed'));
    
    ElMessage.success(res.message || t('common.done'));
    drawerVisible.value = false;
    fetchRoles(); // Refresh table to update page_count
  } catch (error) {
    console.error('Failed to save permissions:', error);
    ElMessage.error(getApiErrorMessage(error, t('role.savePermissionsFailed')));
  } finally {
    saveTreeLoading.value = false;
  }
};

onMounted(() => {
  fetchRoles();
});
</script>

<style scoped>
</style>
