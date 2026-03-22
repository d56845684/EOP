<template>
  <div class="role-list">
    <div class="flex justify-between items-center px-1 mb-2">
      <h3 class="my-0">{{ $t('menu.role_settings') }}</h3>
      <el-button
        v-permission="'roles.create'"
        type="primary"
        round
        class="h-9 px-1"
        @click="handleCreate"
      >
        <template #icon>
          <div class="i-hugeicons:plus-sign-square" />
        </template>
        {{ $t('role.add') }}
      </el-button>
    </div>
    <el-card>
      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column prop="name" :label="$t('role.roleName')" min-width="80" />
        <el-table-column prop="key" :label="$t('role.roleKey')" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="roleColor[row.key] || 'info'" class="font-size-10px">
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
        <el-table-column :label="$t('common.actions')" width="240" fixed="right" align="center">
          <template #default="{ row }">
            <el-space v-if="!needLock(row)" :size="10" style="width: 100%; justify-content: flex-end;">
              <div class="flex justify-end">
                <el-button
                  v-permission="'permissions.pages'"
                  round
                  size="small"
                  type="success"
                  plain
                  @click="handlePermission(row)"
                >
                  {{ $t('role.settings') }}
                </el-button>
                <el-button
                  v-permission="'permissions.roles'"
                  round
                  size="small"
                  type="primary"
                  plain
                  @click="handleEdit(row)"
                >
                  {{ $t('common.edit') }}
                </el-button>
              </div>
              <el-popconfirm
                :title="$t('common.confirm') + $t('common.delete') + '?'"
                @confirm="handleDelete(row)"
              >
                <template #reference>
                  <el-button v-permission="'permissions.roles'" round link size="small" type="danger" plain>
                    <div class="i-hugeicons:delete-02 mr-2px" />
                    {{ $t('common.delete') }}
                  </el-button>
                </template>
              </el-popconfirm>
            </el-space>
            <div v-else class="flex justify-center">
              <div class="i-hugeicons:square-lock-01 text-md text-gray-400" />
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
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item :label="$t('role.roleKey')" prop="key">
          <el-input v-model="form.key" :disabled="isEdit" :placeholder="$t('role.roleKeyPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('role.roleName')" prop="name">
          <el-input v-model="form.name" :placeholder="$t('role.roleNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('role.description')" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" :placeholder="$t('role.descriptionPlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" :loading="submitLoading" @click="submitForm">
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
      <div class="h-full flex flex-col" v-loading="treeLoading">
        <div class="flex-1 overflow-y-auto pr-2">
          <el-tree
            ref="treeRef"
            :data="permissionTree"
            show-checkbox
            node-key="id"
            :props="defaultProps"
            default-expand-all
            :expand-on-click-node="false"
          />
        </div>
        <div class="mt-4 pt-4 border-t flex justify-end gap-2">
          <el-button @click="drawerVisible = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" :loading="saveTreeLoading" @click="savePermissions">
            {{ $t('common.save') }}
          </el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import type { FormInstance, FormRules } from 'element-plus';
import {
  getRolesApi, createRoleApi, updateRoleApi, deleteRoleApi,
  getPagesApi, getRolePagesApi, updateRolePagesApi
} from '@/api/role';
import type { RoleInfo, RoleCreate, RoleUpdate, PageResponse } from '@/api/role';

const { t } = useI18n();

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
  key: [{ required: true, message: 'Required', trigger: 'blur' }],
  name: [{ required: true, message: 'Required', trigger: 'blur' }],
});

// --- Permission Tree State ---
const drawerVisible = ref(false);
const treeLoading = ref(false);
const saveTreeLoading = ref(false);
const treeRef = ref<any>(null);
const currentRole = ref<RoleInfo | null>(null);
const permissionTree = ref<any[]>([]);

const defaultProps = {
  children: 'children',
  label: 'name',
};

// --- Tree Building Logic ---
interface TreeNode extends PageResponse {
  children?: TreeNode[];
}

const buildTree = (pages: PageResponse[]): TreeNode[] => {
  const map = new Map<string, TreeNode>();
  const tree: TreeNode[] = [];

  // First pass: create node objects
  pages.forEach(page => {
    map.set(page.key, { ...page, children: [] });
  });

  // Second pass: attach to parents
  pages.forEach(page => {
    const node = map.get(page.key);
    if (node) {
      if (page.parent_key && map.has(page.parent_key)) {
        map.get(page.parent_key)!.children!.push(node);
      } else {
        tree.push(node);
      }
    }
  });

  return tree;
};

// --- Methods ---

const needLock = (row: RoleInfo) => {
  return ['admin', 'teacher', 'student', 'employee'].includes(row.key)
}

const fetchRoles = async () => {
  loading.value = true;
  try {
    const res = await getRolesApi();
    if (res?.data) {
      tableData.value = res?.data;
    }
  } catch (error) {
    console.error('Failed to fetch roles:', error);
    ElMessage.error('Failed to load roles');
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

const handleDelete = async (row: RoleInfo) => {
  try {
    await deleteRoleApi(row.id);
    ElMessage.success(t('common.done'));
    fetchRoles();
  } catch (error) {
    console.error('Failed to delete role:', error);
  }
};

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
          await updateRoleApi(form.id, updateData);
          ElMessage.success(t('common.done'));
        } else {
          await createRoleApi(form);
          ElMessage.success(t('common.done'));
        }
        dialogVisible.value = false;
        fetchRoles();
      } catch (error) {
        console.error('Failed to save role:', error);
      } finally {
        submitLoading.value = false;
      }
    }
  });
};

const handlePermission = async (row: RoleInfo) => {
  currentRole.value = row;
  drawerVisible.value = true;
  treeLoading.value = true;
  try {
    // 1. Fetch all pages and build tree
    const pagesRes = await getPagesApi();
    let allPages: PageResponse[] = [];
    if (pagesRes.data) {
      allPages = pagesRes.data;
      permissionTree.value = buildTree(allPages);
    }

    // 2. Fetch current role permissions
    const rolePagesRes = await getRolePagesApi(row.id);
    const existingPages = rolePagesRes?.pages || [];
    
    // We only want to set checked keys for leaf nodes in element-plus tree, 
    // otherwise parent nodes will auto-select all children.
    const parentKeys = new Set(allPages.map(p => p.parent_key).filter(Boolean));
    const leafIds = existingPages
        .filter(p => !parentKeys.has(p.key)) // only keys that are not parents of any other node
        .map(p => p.id);
    
    // Wait for the drawer and tree to be rendered
    nextTick(() => {
      // Element Plus Drawer might have a transition delay, so nextTick + small timeout is safest for treeRef
      setTimeout(() => {
        if (treeRef.value) {
          treeRef.value.setCheckedKeys(leafIds);
        }
      }, 50);
    });

  } catch (error) {
    console.error('Failed to load permissions:', error);
    ElMessage.error('Failed to load permissions');
  } finally {
    treeLoading.value = false;
  }
};

const savePermissions = async () => {
  if (!currentRole.value || !treeRef.value) return;
  
  saveTreeLoading.value = true;
  try {
    // Get both fully checked and half checked (indeterminate) keys
    const checkedKeys = treeRef.value.getCheckedKeys();
    const halfCheckedKeys = treeRef.value.getHalfCheckedKeys();
    const allPageIds = [...checkedKeys, ...halfCheckedKeys];

    await updateRolePagesApi({
      role_id: currentRole.value.id,
      page_ids: allPageIds,
    });
    
    ElMessage.success(t('common.done'));
    drawerVisible.value = false;
    fetchRoles(); // Refresh table to update page_count
  } catch (error) {
    console.error('Failed to save permissions:', error);
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
