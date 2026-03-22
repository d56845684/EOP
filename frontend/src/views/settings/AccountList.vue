<template>
  <div class="account-list pl-2 pr-4">
    <div class="flex justify-between items-center px-1 mb-2">
      <h3 class="my-0">{{ $t('menu.account_settings') }}</h3>
      <el-button
        v-permission="'accounts.create'"
        type="primary"
        round
        class="h-9 px-1"
        @click="openDrawer(null, 'add')"
      >
        <template #icon>
          <div class="i-hugeicons:plus-sign-square" />
        </template>
        {{ $t('account.add') }}
      </el-button>
    </div>
    <el-card class="filter-card mb-14px">
      <!-- Area A: Filter Section -->
      <el-form :inline="true" :model="queryParams" label-position="top" class="filter-form flex items-end" @submit.prevent="handleSearch">
        <el-form-item :label="$t('common.searchKeyword')">
          <el-input
            v-model="queryParams.search"
            :placeholder="$t('account.searchPlaceholder')"
            clearable
            class="w-240px"
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
            :placeholder="$t('account.role')" 
            clearable
            class="w-120px"
            @clear="handleSearch"
            @change="handleSearch"
          >
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.key" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('common.status')">
          <el-select
            v-model="queryParams.is_active"
            :placeholder="$t('common.status')"
            clearable
            class="w-120px"
            @clear="handleSearch"
            @change="handleSearch"
          >
            <el-option :label="$t('common.all')" value="all" />
            <el-option :label="$t('common.active')" :value="true" />
            <el-option :label="$t('common.inactive')" :value="false" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" round @click="handleSearch">
            <template #icon>
              <div class="i-hugeicons:search-01" />
            </template>
            {{ $t('common.search') }}
          </el-button>
          <el-button round @click="resetQuery">
            <template #icon>
              <div class="i-hugeicons:arrow-reload-horizontal" />
            </template>
            {{ $t('common.btnReset') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <!-- Area B: Data Table -->
      <el-table :data="users" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" min-width="120" :label="$t('account.nickname')" />
        <el-table-column prop="email" min-width="200" :label="$t('account.account')" />
        <!-- <el-table-column prop="role" :label="$t('account.role')" /> -->
        <el-table-column prop="employee_subtype" min-width="120" :label="$t('account.employeeSubtype')">
          <template #default="{ row }">
            {{ row.employee_subtype || '-' }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('account.createdTime')" width="180">
           <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('common.status')" align="center">
           <template #default="{ row }">
              <!-- <el-tag size="small" :type="row.is_active ? 'success' : 'info'" effect='plain' class="w-50px">
                {{ row.is_active ? $t('common.active') : $t('common.inactive') }}
              </el-tag> -->
              <el-switch 
                v-model="row.is_active" 
                :disabled="row.is_protected"
                inline-prompt
                active-text="啟用" 
                inactive-text="停用" 
                size="small"
                :before-change="() => handleDeactivate(row)"
              />
           </template>
        </el-table-column>
        
        <el-table-column :label="$t('common.actions')" width="100" fixed="right" align="center">
            <template #default="{ row }">
              <el-button
                type="primary" 
                plain
                round
                size="small"
                @click="openDrawer(row, 'edit')" 
                :disabled="row.is_protected"
              >
                  {{ $t('common.edit') }}
              </el-button>
            </template>
        </el-table-column>
      </el-table>
      
      <!-- Area C: Pagination -->
      <div class="pagination-footer">
          <el-pagination
            v-model:current-page="queryParams.page"
            v-model:page-size="queryParams.per_page"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="total"
            @size-change="fetchUsers"
            @current-change="fetchUsers"
          />
      </div>
    </el-card>

    <!-- Area D: Edit Drawer -->
     <EditEmployeeDrawer
      v-model="drawerVisible"
      :editUserId="editUserId"
      :current-user="currentUser"
      :roles="roles"
      @fetch-users="fetchUsers"
      @clear-user="clearUser"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import dayjs from 'dayjs';
import { getUsersApi, getRolesApi, updateUserApi, deleteUserApi, type AccountInfo, type RoleInfo } from '@/api/user';
import EditEmployeeDrawer from './components/EditEmployeeDrawer.vue';

// State
const users = ref<AccountInfo[]>([]);
const roles = ref<RoleInfo[]>([]);
const total = ref(0);
const loading = ref(false);

interface QueryParams {
  page?: number;
  per_page?: number;
  search?: string;
  role?: string;
}

const queryParams = reactive<QueryParams>({
  page: 1,
  per_page: 10,
  search: '',
  role: 'employee'
});

// Drawer State
const drawerVisible = ref(false);
const editUserId = ref('');

const currentUser = reactive<AccountInfo>({
  id: '',
  email: '',
  name: null,
  role: '',
  role_id: '',
  employee_subtype: null,
  is_active: false,
  is_protected: false,
  created_at: ''
});

// Helpers
const formatTime = (t: string) => t ? dayjs(t).format('YYYY-MM-DD HH:mm') : '-';

// API Calls
const fetchRoles = async () => {
  try {
    const res = await getRolesApi();
    if (res.data && Array.isArray(res.data)) {
      roles.value = res.data;
    } else if (res.data && Array.isArray((res.data as any).data)) {
      roles.value = (res.data as any).data;
    } else if (Array.isArray(res)) {
      roles.value = res as any;
    }
  } catch (error) {
    ElMessage.error('Failed to load roles');
  }
};

const fetchUsers = async () => {
  loading.value = true;
  try {
    const dataToSend = { ...queryParams };
    if (!dataToSend.search) delete dataToSend.search;
    if (!dataToSend.role) delete dataToSend.role;

    const res = await getUsersApi(dataToSend);
    
    // Adjust based on actual API wrapper
    if (res.data && res.data.items !== undefined) {
      users.value = res.data.items;
      total.value = res.data.total;
    } else if (res.data && res.data.data && res.data.data.items !== undefined) {
      users.value = res.data.data.items;
      total.value = res.data.data.total;
    } else if (res.items !== undefined) {
      users.value = (res as any).items;
      total.value = (res as any).total;
    } else {
      users.value = res.data || res || [];
      total.value = users.value.length;
    }
  } catch (error) {
    ElMessage.error('Failed to load users');
  } finally {
    loading.value = false;
  }
};

// Handlers
const handleSearch = () => {
  queryParams.page = 1;
  fetchUsers();
};

const resetQuery = () => {
  queryParams.search = '';
  queryParams.role = '';
  handleSearch();
};

const openDrawer = (row: AccountInfo | null, type: string) => {
  if (type === 'edit' && row) {
    editUserId.value = row.id;
    Object.assign(currentUser, row);
  }
  drawerVisible.value = true;
};

const clearUser = () => {
  Object.assign(currentUser, {
    id: '',
    email: '',
    name: null,
    role: '',
    role_id: '',
    employee_subtype: null,
    is_active: false,
    is_protected: false,
    created_at: ''
  })
}

const handleDeactivate = (row: AccountInfo): Promise<boolean> => {
  return new Promise((resolve, reject) => {
    ElMessageBox.confirm(`確定要${row.is_active ? '停用' : '啟用'}此帳號嗎？`, 'Warning', {
      confirmButtonText: '確定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(async () => {
      try {
        if (row.is_active) {
          await deleteUserApi(row.id);
        } else {
          await updateUserApi(row.id, {
            is_active: true
          });
        }
        ElMessage.success('更新成功');
        fetchUsers();
        resolve(true)
      } catch (error) {
        ElMessage.error('更新失敗');
        reject(false)
      }
    }).catch(() => {reject(false)});
  });
};

onMounted(() => {
  fetchRoles();
  fetchUsers();
});
</script>

<style scoped>
.pagination-footer { display: flex; justify-content: flex-end; margin-top: 20px; }
</style>
