<template>
  <div class="account-list">
    <el-card>
      <template #header>
        <div class="header">
           <span>{{ $t('account.title') }}</span>
           <el-button type="primary" @click="openDrawer(null)">{{ $t('account.add') }}</el-button>
        </div>
      </template>
      
      <el-table :data="paginatedUsers" style="width: 100%">
        <el-table-column :label="$t('account.avatar')" width="80">
           <template #default="{ row }"><el-avatar :src="row.avatar" /></template>
        </el-table-column>
        <el-table-column prop="username" :label="$t('account.account')" />
        <el-table-column prop="nickname" :label="$t('account.nickname')" />
        <el-table-column prop="role" :label="$t('account.role')">
           <template #default="{ row }">
              <el-tag :type="row.role === 'super_admin' ? 'danger' : ''">{{ getRoleName(row.role) }}</el-tag>
           </template>
        </el-table-column>
        <el-table-column :label="$t('account.createdTime')" width="180">
           <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column :label="$t('common.status')">
           <template #default="{ row }">
              <el-switch v-model="row.status" :disabled="row.role === 'super_admin'" />
           </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')">
            <template #default="{ row }">
               <div v-if="row.role !== 'super_admin'">
                   <el-button link type="primary" @click="openDrawer(row)">{{ $t('common.edit') }}</el-button>
                   <el-button link type="danger" @click="handleDelete(row)">{{ $t('common.delete') }}</el-button>
               </div>
               <span v-else class="text-gray">Protected</span>
            </template>
        </el-table-column>
      </el-table>
      <div class="pagination-footer">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="users.length"
          />
      </div>
    </el-card>

    <el-drawer v-model="drawerVisible" :title="isEdit ? $t('account.editTitle') : $t('account.add')">
       <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
          <!-- 1. Nickname -->
          <el-form-item :label="$t('account.nickname')" prop="nickname">
             <el-input v-model="form.nickname" />
          </el-form-item>
          
          <!-- 2. Account (Username) -->
          <el-form-item :label="$t('account.account')" prop="username">
             <el-input v-model="form.username" :disabled="isEdit" />
          </el-form-item>
          
          <!-- 3. Password -->
          <el-form-item :label="$t('account.password')" prop="password" :required="!isEdit">
             <el-input 
                v-model="form.password" 
                show-password 
                :placeholder="isEdit ? 'Leave empty to keep unchanged' : 'Required'" 
             />
          </el-form-item>
          <el-form-item :label="$t('account.confirmPw')" prop="confirmPassword" :required="!isEdit || !!form.password">
              <el-input v-model="form.confirmPassword" show-password :placeholder="$t('account.confirmPw')" />
          </el-form-item>

          <!-- 4. Role -->
          <el-form-item :label="$t('account.role')" prop="role">
             <el-select v-model="form.role">
                 <el-option 
                    v-for="r in roles" 
                    :key="r.id" 
                    :label="r.name" 
                    :value="r.id" 
                    :disabled="r.id === 'super_admin'"
                 />
             </el-select>
          </el-form-item>

          <!-- 5. Avatar -->
          <el-form-item :label="$t('account.avatar')">
             <div class="avatar-select">
                <el-avatar 
                   v-for="url in PRESET_AVATARS" 
                   :key="url" 
                   :src="url" 
                   :class="{ selected: form.avatar === url }"
                   @click="form.avatar = url"
                   size="large"
                   style="cursor: pointer; margin-right: 15px"
                />
             </div>
          </el-form-item>
       </el-form>
       <template #footer>
          <el-button @click="drawerVisible = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="handleSave">{{ $t('common.save') }}</el-button>
       </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, nextTick } from 'vue';
import { useMockStore, type User } from '../../stores/mockStore';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import dayjs from 'dayjs';

const store = useMockStore();
const users = computed(() => store.users);
const roles = computed(() => store.roles);

// --- Pagination State ---
const currentPage = ref(1);
const pageSize = ref(10);
const paginatedUsers = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value;
    const end = start + pageSize.value;
    return users.value.slice(start, end);
});
const drawerVisible = ref(false);
const formRef = ref<FormInstance>();
const isEdit = ref(false);

const form = reactive({
    id: '',
    username: '',
    password: '',
    confirmPassword: '',
    nickname: '',
    avatar: '',
    role: '',
    status: true,
    createdAt: ''
});

const PRESET_AVATARS = [
    'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
    'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png',
    'https://cube.elemecdn.com/9/c2/f0ee8a3c7c9638a54940382568c9dpng.png',
    'https://cube.elemecdn.com/6/94/4d3ea53c084bad6931a56d5158a48jpeg.jpeg',
    'https://cube.elemecdn.com/f/17/92ae64b6b442b3b0409951336f333png.png'
];

const formatTime = (t: string) => t ? dayjs(t).format('YYYY-MM-DD HH:mm') : '-';
const getRoleName = (id: string) => roles.value.find(r => r.id === id)?.name || id;

// --- Validation Rules ---
// --- Validation Rules ---
const validatePass = (_rule: any, value: any, callback: any) => {
    if (!isEdit.value && !value) {
        callback(new Error('Password is required'));
    } else {
        if (form.confirmPassword !== '') {
            formRef.value?.validateField('confirmPassword');
        }
        callback();
    }
};

const validateConfirmPass = (_rule: any, value: any, callback: any) => {
    if (form.password && value !== form.password) {
        callback(new Error("Passwords do not match"));
    } else {
        callback();
    }
};

const rules = reactive<FormRules>({
    nickname: [{ required: true, message: 'Nickname is required', trigger: 'blur' }],
    username: [{ required: true, message: 'Account is required', trigger: 'blur' }],
    role: [{ required: true, message: 'Role is required', trigger: 'change' }],
    password: [{ validator: validatePass, trigger: 'blur' }],
    confirmPassword: [{ validator: validateConfirmPass, trigger: 'blur' }]
});


const openDrawer = (u: User | null) => {
    if (u) {
        isEdit.value = true;
        Object.assign(form, u);
        form.password = ''; // Don't show existing
        form.confirmPassword = '';
    } else {
        isEdit.value = false;
        Object.assign(form, {
            id: '',
            username: '',
            password: '',
            confirmPassword: '',
            nickname: '',
            avatar: PRESET_AVATARS[0] || '',
            role: 'admin',
            status: true,
            createdAt: ''
        });
    }
    drawerVisible.value = true;
    nextTick(() => {
        formRef.value?.clearValidate();
    });
};

const handleSave = async () => {
    if (!formRef.value) return;
    await formRef.value.validate((valid) => {
        if (valid) {
             if (isEdit.value) {
                const idx = store.users.findIndex(u => u.id === form.id);
                if (idx !== -1) {
                    const output = { ...form } as any;
                    delete output.confirmPassword;
                    // Preserve old password if not changed
                    const existing = store.users[idx];
                    if (existing && !output.password && existing.password) {
                        output.password = existing.password;
                    }
                    store.users[idx] = output;
                }
            } else {
                const newUser = { ...form } as any;
                delete newUser.confirmPassword;
                newUser.id = 'u' + Date.now();
                newUser.createdAt = dayjs().toISOString();
                store.users.push(newUser);
            }
            drawerVisible.value = false;
            ElMessage.success('Saved');
        }
    });
};

const handleDelete = (u: User) => {
     ElMessageBox.confirm('Delete user?', 'Warning', { type: 'warning' }).then(() => {
         store.users = store.users.filter(x => x.id !== u.id);
         ElMessage.success('Deleted');
     });
};
</script>

<style scoped>
.header { display: flex; justify-content: space-between; align-items: center; }
.selected { border: 3px solid var(--el-color-primary); box-shadow: 0 0 5px rgba(0,0,0,0.2); }
.pagination-footer { display: flex; justify-content: flex-end; margin-top: 20px; }
.text-gray { color: #909399; font-style: italic; }
.avatar-select { display: flex; flex-wrap: wrap; }
</style>
