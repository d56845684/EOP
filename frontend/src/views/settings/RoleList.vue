<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useMockStore, type RoleDef, PERMISSION_TREE_DATA } from '../../stores/mockStore';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { Plus, Delete, Edit } from '@element-plus/icons-vue';
import dayjs from 'dayjs';

// --- Store ---
const store = useMockStore();
// Ensure we fetch/sync roles mainly if needed, but they are in state. 
// We can reactively use store.roles

// --- State ---
const drawerVisible = ref(false);
const isEdit = ref(false);
const treeRef = ref<any>(null); // el-tree instance

const formRef = ref<FormInstance>();
const formData = reactive<RoleDef>({
  id: '',
  name: '',
  note: '',
  status: true,
  permissions: [],
  updatedAt: '',
});

const rules = reactive<FormRules>({
  name: [{ required: true, message: 'Role Name is required', trigger: 'blur' }],
});

// --- Actions ---

const handleAdd = () => {
  isEdit.value = false;
  formData.id = '';
  formData.name = '';
  formData.note = '';
  formData.status = true;
  formData.permissions = [];
  formData.updatedAt = '';
  drawerVisible.value = true;
  // Reset tree checking
  if (treeRef.value) {
    treeRef.value.setCheckedKeys([]);
  }
};

const handleEdit = (row: RoleDef) => {
  if (row.id === 'super_admin') return; // Safety check
  isEdit.value = true;
  Object.assign(formData, row);
  drawerVisible.value = true;
  // Set tree checking
  // We need to wait for drawer render or use nextTick, but pure v-model on tree works if data bound? 
  // el-tree setCheckedKeys is more reliable
  setTimeout(() => {
    if (treeRef.value) {
      treeRef.value.setCheckedKeys(row.permissions);
    }
  }, 100);
};

const handleDelete = async (row: RoleDef) => {
  if (row.id === 'super_admin') return;
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to delete role "${row.name}"?`,
      'Warning',
      { type: 'warning' }
    );
    await store.deleteRole(row.id);
  } catch (e) {
    // cancelled
  }
};

const handleStatusChange = async (row: RoleDef, val: boolean) => {
  if (row.id === 'super_admin') {
     row.status = true; // Revert visually if somehow triggered
     return;
  }
  // We should update the store
  await store.saveRole({ ...row, status: val });
};

const handleSave = async (formEl: FormInstance | undefined) => {
  if (!formEl) return;
  await formEl.validate(async (valid) => {
    if (valid) {
      // Get permissions from tree
      const checkedKeys = treeRef.value?.getCheckedKeys() || [];
      const halfCheckedKeys = treeRef.value?.getHalfCheckedKeys() || [];
      // Usually we want both or just checked/leafs depending on logic.
      // Requirements said "checks parent checks children" (standard behavior).
      // If we only store checked keys, el-tree restores fine.
      
      const rolePayload: RoleDef = {
        ...formData,
        permissions: [...checkedKeys, ...halfCheckedKeys], // Storing all implies full restoration strategy logic? 
        // Actually, standard el-tree :default-checked-keys expects leaf nodes mostly, 
        // or just all checked ids. Let's just store all checked.
      };

      try {
        await store.saveRole(rolePayload);
        drawerVisible.value = false;
      } catch (e: any) {
        ElMessage.error(e.message || 'Error saving role');
      }
    }
  });
};

// --- Tree Actions ---
const handleCheck = (data: any, { checkedKeys }: { checkedKeys: string[] }) => {
  if (!treeRef.value) return;

  const id = data.id as string;
  
  // Logic 1: If Edit is checked, View MUST be checked.
  if (id.endsWith(':edit')) {
     const isChecked = checkedKeys.includes(id);
     if (isChecked) {
         const viewId = id.replace(':edit', ':view');
         if (!checkedKeys.includes(viewId)) {
             treeRef.value.setChecked(viewId, true, false);
         }
     }
  }

  // Logic 2: If View is unchecked, Edit MUST be unchecked.
  if (id.endsWith(':view')) {
      const isChecked = checkedKeys.includes(id);
      if (!isChecked) {
           const editId = id.replace(':view', ':edit');
           if (checkedKeys.includes(editId)) {
               treeRef.value.setChecked(editId, false, false);
           }
      }
  }
};

const handleSelectAll = () => {
  if (treeRef.value) {
    treeRef.value.setCheckedNodes(PERMISSION_TREE_DATA);
  }
};

const handleDeselectAll = () => {
  if (treeRef.value) {
    treeRef.value.setCheckedKeys([]);
  }
};

// --- Styles ---
const tableRowClassName = ({ row }: { row: RoleDef }) => {
  if (row.id === 'super_admin') {
    return 'super-admin-row';
  }
  return '';
};

const formatTime = (iso: string) => dayjs(iso).format('YYYY-MM-DD HH:mm');

</script>

<template>
  <div class="role-list-page">
    <div class="page-header">
      <h2>{{ $t('role.title') }}</h2>
      <el-button type="primary" :icon="Plus" @click="handleAdd">{{ $t('role.add') }}</el-button>
    </div>

    <el-card shadow="never">
      <el-table 
        :data="store.roles" 
        style="width: 100%" 
        :row-class-name="tableRowClassName" 
        border
      >
        <el-table-column prop="name" :label="$t('role.roleName')" width="200" />
        <el-table-column prop="note" :label="$t('role.note')" min-width="250" />
        <el-table-column :label="$t('common.status')" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              :disabled="row.id === 'super_admin'"
              @change="(val: boolean) => handleStatusChange(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.lastUpdated')" width="180">
          <template #default="{ row }">
            {{ formatTime(row.updatedAt) }}
          </template>
        </el-table-column>
        
        <el-table-column :label="$t('common.actions')" width="200" fixed="right">
          <template #default="{ row }">
            <div v-if="row.id !== 'super_admin'">
              <el-button link type="primary" :icon="Edit" @click="handleEdit(row)">
                {{ $t('role.settings') }}
              </el-button>
              <el-button link type="danger" :icon="Delete" @click="handleDelete(row)">
                {{ $t('common.delete') }}
              </el-button>
            </div>
            <div v-else>
              <el-tag type="info" size="small">System Locked</el-tag>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Role Drawer -->
    <el-drawer
      v-model="drawerVisible"
      :title="isEdit ? $t('role.editTitle') : $t('role.addTitle')"
      size="500px"
      append-to-body
    >
      <el-form ref="formRef" :model="formData" :rules="rules" layout="vertical" label-position="top">
        <el-form-item :label="$t('role.roleName')" prop="name">
          <el-input v-model="formData.name" placeholder="e.g. Finance Manager" />
        </el-form-item>
        
        <el-form-item :label="$t('role.description')" prop="note">
          <el-input 
            v-model="formData.note" 
            type="textarea" 
            :rows="2" 
            placeholder="Role responsibilities..." 
          />
        </el-form-item>
        
        <el-form-item :label="$t('role.permissions')">
           <div class="tree-tools">
              <el-button size="small" @click="handleSelectAll">{{ $t('role.selectAll') }}</el-button>
              <el-button size="small" @click="handleDeselectAll">{{ $t('role.deselectAll') }}</el-button>
           </div>
           <div class="tree-container">
             <el-tree
                ref="treeRef"
                :data="PERMISSION_TREE_DATA"
                show-checkbox
                node-key="id"
                default-expand-all
                :expand-on-click-node="false"
                @check="handleCheck"
             />
           </div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="drawer-footer">
          <el-button @click="drawerVisible = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="handleSave(formRef)">{{ $t('common.confirm') }}</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.tree-tools {
  margin-bottom: 10px;
}
.tree-container {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  max-height: 300px;
  overflow-y: auto;
}
.drawer-footer {
  display: flex;
  justify-content: flex-end;
}

/* Super Admin Highlight */
/* Super Admin Highlight */
:deep(.super-admin-row) {
  --super-admin-bg: #fdfdfd;
  background-color: var(--super-admin-bg) !important;
}

html.dark :deep(.super-admin-row) {
  --super-admin-bg: #1d1e1f; /* Dark background matching Element fast dark theme */
  background-color: var(--super-admin-bg) !important;
}

:deep(.super-admin-row:hover > td) {
  background-color: rgba(0, 0, 0, 0.05) !important;
}

html.dark :deep(.super-admin-row:hover > td) {
  background-color: rgba(255, 255, 255, 0.05) !important;
}
</style>
