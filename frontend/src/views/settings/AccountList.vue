<template>
  <div class="account-list pl-2 pr-4">
    <div class="flex justify-between items-center px-1 mb-2">
      <h3 class="my-0">{{ $t('menu.account_settings') }}</h3>
      <el-button
        v-permission="'accounts.create'"
        type="primary"
        round
        size="small"
        class="h-30px! px-2"
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
            class="w-240px h-30px!"
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
            <el-option v-for="r in roleList" :key="r.id" :label="r.name" :value="r.key" />
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

    <el-card>
      <!-- Area B: Data Table -->
      <el-table :data="users" size="small" class="w-full" v-loading="loading">
        <el-table-column prop="name" min-width="140" :label="$t('account.nickname')" />
        <el-table-column prop="email" min-width="260" :label="$t('account.account')" />
        <!-- <el-table-column prop="role" :label="$t('account.role')" /> -->
        <el-table-column prop="employee_subtype" min-width="120" align="center" :label="$t('account.employeeSubtype')">
          <template #default="{ row }">
            {{ row.employee_subtype || '-' }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('account.createdTime')" width="160" align="center">
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
                link
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
      :roles="roleList"
      @fetch-users="fetchUsers"
      @clear-user="clearUser"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import dayjs from 'dayjs';
import { getUsersApi, getRolesApi, updateUserApi, deleteUserApi, type AccountInfo, type RoleInfo } from '@/api/user';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
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
  is_active?: boolean | string;
}

const queryParams = reactive<QueryParams>({
  page: 1,
  per_page: 10,
  search: '',
  role: 'employee',
  is_active: 'all'
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

const roleList = computed(() => {
  const exception = ['teacher', 'student']
  return roles.value.filter(r => !exception.includes(r.key));
});

// API Calls
const fetchRoles = async () => {
  try {
    const res = assertApiSuccess(await getRolesApi(), '載入角色失敗');
    roles.value = res.data || [];
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Failed to load roles'));
  }
};

const fetchUsers = async () => {
  loading.value = true;
  try {
    const dataToSend = { ...queryParams };
    if (!dataToSend.search) delete dataToSend.search;
    if (!dataToSend.role) delete dataToSend.role;
    if (dataToSend.is_active === 'all') delete dataToSend.is_active;

    const res = assertApiSuccess(await getUsersApi(dataToSend), '載入帳號失敗');
    users.value = res.data.items || [];
    total.value = res.data.total || 0;
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Failed to load users'));
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
          const res = assertApiSuccess(await deleteUserApi(row.id), '停用帳號失敗');
          ElMessage.success(res.message || '更新成功');
        } else {
          const res = assertApiSuccess(await updateUserApi(row.id, {
            is_active: true
          }), '啟用帳號失敗');
          ElMessage.success(res.message || '更新成功');
        }
        fetchUsers();
        resolve(true)
      } catch (error) {
        ElMessage.error(getApiErrorMessage(error, '更新失敗'));
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
