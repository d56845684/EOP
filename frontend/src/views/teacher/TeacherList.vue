<template>
  <div class="teacher-list-page pl-2 pr-4">
    <div class="flex justify-between items-center px-1 mb-2">
      <h3 class="my-0">{{ $t('teacher.title') }}</h3>
      <el-button
        v-permission="'accounts.create'"
        type="primary"
        round
        class="h-9 px-1"
        @click="openAddDialog"
      >
        <template #icon>
          <div class="i-hugeicons:plus-sign-square" />
        </template>
        {{ $t('teacher.add') }}
      </el-button>
    </div>

    <el-card shadow="never" class="mb-4">
      <el-form :inline="true" :model="queryParams" label-position="top" class="flex gap-4 items-end">
        <el-form-item label="關鍵字" class="mb-0">
          <el-input 
            v-model="queryParams.search" 
            placeholder="Name, Email, or Phone" 
            clearable 
            @clear="fetchTeachersList" 
            @keyup.enter="fetchTeachersList"
            style="width: 260px"
          >
            <template #prefix>
              <div class="i-hugeicons:search-01" />
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="狀態" class="mb-0">
          <el-select v-model="queryParams.is_active" style="width: 120px" @change="fetchTeachersList">
            <el-option label="全部" value="all" />
            <el-option label="啟用" :value="true" />
            <el-option label="停用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item class="mb-0">
          <el-button type="primary" round @click="fetchTeachersList">
            <template #icon>
              <div class="i-hugeicons:search-01" />
            </template>
            {{ $t('common.search') }}
          </el-button>
          <el-button round @click="handleReset">
            <template #icon>
              <div class="i-hugeicons:arrow-reload-horizontal" />
            </template>
            {{ $t('common.btnReset') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div v-loading="loading">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12" v-for="teacher in teachersData" :key="teacher.id" class="mb-4">
          <el-card shadow="hover" class="h-full relative flex flex-col h-full card-bg">
            <el-descriptions :title="teacher.name" :column="1" border size="small" class="flex-1">
              <el-descriptions-item label="編號 (No.)">{{ teacher.teacher_no || '-' }}</el-descriptions-item>
              <el-descriptions-item label="Email">{{ teacher.email }}</el-descriptions-item>
              <el-descriptions-item label="電話 (Phone)">{{ teacher.phone || '-' }}</el-descriptions-item>
              <el-descriptions-item label="狀態 (Status)">
                <el-switch 
                  v-model="teacher.is_active" 
                  inline-prompt
                  active-text="啟用" 
                  inactive-text="停用" 
                  size="small"
                  :before-change="() => handleToggleStatus(teacher)"
                />
              </el-descriptions-item>
            </el-descriptions>
            <div class="flex justify-end mt-4 gap-2">
              <el-button type="success" plain round size="small">{{ $t('common.contracts') }}</el-button>
              <el-button type="primary" plain round size="small" @click="openManageDrawer(teacher)">
                {{ $t('common.viewDetails') }}
              </el-button>
              <el-button 
                v-permission="'teachers.delete'" 
                type="danger" 
                link 
                size="small" 
                @click="handleDelete(teacher)"
              >
                <div class="i-hugeicons:delete-02 mr-2px" />
                {{ $t('common.delete') }}
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <el-empty v-if="teachersData.length === 0" description="No Teachers Found" />
    </div>

    <div class="flex justify-end mt-4">
      <el-pagination
        v-model:current-page="queryParams.page"
        v-model:page-size="queryParams.per_page"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="totalTeachers"
        @size-change="fetchTeachersList"
        @current-change="fetchTeachersList"
      />
    </div>

    <!-- Inner Drawer Component -->
    <TeacherDetailDrawer 
      v-model="drawerVisible" 
      :teacherId="selectedTeacherId" 
      @saved="fetchTeachersList" 
    />

    <!-- Add Teacher Dialog -->
    <el-dialog v-model="addDialogVisible" :title="$t('teacher.add')" width="500px" @closed="resetAddForm">
      <el-form ref="addFormRef" :model="addForm" :rules="addRules" label-width="120px">
        <el-form-item :label="$t('common.name')" prop="name">
          <el-input v-model="addForm.name" />
        </el-form-item>
        <el-form-item :label="$t('common.email')" prop="email">
          <el-input v-model="addForm.email" />
        </el-form-item>
        <el-form-item :label="$t('common.phone')" prop="phone">
          <el-input v-model="addForm.phone" />
        </el-form-item>
        <el-form-item :label="'Teacher Level'" prop="teacher_level">
          <el-input-number v-model="addForm.teacher_level" :min="1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer flex justify-end">
          <el-button @click="addDialogVisible = false" round>{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" :loading="addingFile" @click="handleAdd" round>{{ $t('common.save') }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { getTeacherList, createTeacher, updateTeacher, deleteTeacher, type TeacherListParams, type TeacherResponse, type TeacherCreate } from '@/api/teacher';
import TeacherDetailDrawer from './components/TeacherDetailDrawer.vue';

const teachersData = ref<TeacherResponse[]>([]);
const totalTeachers = ref(0);
const loading = ref(false);

const queryParams = reactive({
  page: 1,
  per_page: 20,
  search: '',
  is_active: 'all' as 'all' | boolean
});

const drawerVisible = ref(false);
const selectedTeacherId = ref<string | null>(null);

const addDialogVisible = ref(false);
const addingFile = ref(false);
const addFormRef = ref<FormInstance>();
const addForm = reactive<TeacherCreate>({
  name: '',
  email: '',
  phone: '',
  teacher_level: 1,
  is_active: true
});

const addRules = reactive<FormRules>({
  name: [{ required: true, message: 'Name is required', trigger: 'blur' }],
  email: [{ required: true, message: 'Email is required', trigger: 'blur', type: 'email' }]
});

const fetchTeachersList = async () => {
  loading.value = true;
  try {
    const params: TeacherListParams = {
      page: queryParams.page,
      per_page: queryParams.per_page,
      search: queryParams.search || undefined,
      is_active: queryParams.is_active === 'all' ? undefined : queryParams.is_active
    };
    const res = await getTeacherList(params);
    if (res.success) {
      teachersData.value = res.data;
      totalTeachers.value = res.total;
    }
  } catch (e: any) {
    ElMessage.error(e.message || 'Failed to fetch teachers');
  } finally {
    loading.value = false;
  }
};

const handleReset = () => {
  queryParams.search = '';
  queryParams.is_active = 'all';
  queryParams.page = 1;
  fetchTeachersList();
};

onMounted(() => {
  fetchTeachersList();
});

const openManageDrawer = (teacher: TeacherResponse) => {
  selectedTeacherId.value = teacher.id;
  drawerVisible.value = true;
};

const openAddDialog = () => {
  addDialogVisible.value = true;
};

const resetAddForm = () => {
  if (addFormRef.value) addFormRef.value.resetFields();
  addForm.name = '';
  addForm.email = '';
  addForm.phone = '';
  addForm.teacher_level = 1;
  addForm.is_active = true;
};

const handleAdd = async () => {
  if (!addFormRef.value) return;
  await addFormRef.value.validate(async (valid) => {
    if (valid) {
      addingFile.value = true;
      try {
        await createTeacher(addForm);
        ElMessage.success('Teacher added successfully');
        addDialogVisible.value = false;
        fetchTeachersList();
        // optionally open drawer for newly created teacher if API returned it:
        // if (res.data?.id) { selectedTeacherId.value = res.data.id; drawerVisible.value = true; }
      } catch (e: any) {
        ElMessage.error('Failed to add teacher');
      } finally {
        addingFile.value = false;
      }
    }
  });
};

const handleToggleStatus = (teacher: TeacherResponse): Promise<boolean> => {
  return new Promise((resolve, reject) => {
    ElMessageBox.confirm(`確定要${teacher.is_active ? '停用' : '啟用'}此教師嗎？`, 'Warning', {
      confirmButtonText: 'Confirm',
      cancelButtonText: 'Cancel',
      type: 'warning',
    }).then(async () => {
      try {
        await updateTeacher(teacher.id, { is_active: !teacher.is_active });
        ElMessage.success('Status updated');
        resolve(true);
      } catch (e) {
        ElMessage.error('Failed to update status');
        reject(false);
      }
    }).catch(() => {
      reject(false);
    });
  });
};

const handleDelete = async (teacher: TeacherResponse) => {
  try {
    await ElMessageBox.confirm(`Are you sure you want to delete teacher ${teacher.name}?`, 'Warning', {
      type: 'warning'
    });
    await deleteTeacher(teacher.id);
    ElMessage.success('Teacher deleted');
    fetchTeachersList();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('Delete failed');
  }
};
</script>

<style scoped>
.card-bg {
  background-color: #fff;
}
</style>
