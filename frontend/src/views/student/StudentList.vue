<template>
  <div class="student-list-page">
    <!-- Search / Filter Bar -->
    <div class="page-header">
      <h3>{{ $t('menu.student_mgmt') }}</h3>
      <el-button 
        type="primary" 
        :icon="Plus" 
        @click="openAddDrawer"
        v-permission="'students.create'"
      >
        {{ $t('student.add') }}
      </el-button>
    </div>
    <el-card class="filter-card mb-20">
      <el-form :inline="true" :model="queryParams" label-position="top" class="flex items-end">
        <el-form-item :label="$t('common.searchKeyword')">
          <el-input 
            v-model="queryParams.search" 
            :placeholder="$t('student.filter.keyword')" 
            class="filter-item" 
            clearable 
            :prefix-icon="Search" 
            style="width: 300px;" 
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item :label="$t('student.filter.status')">
          <el-select 
            v-model="queryParams.is_active" 
            :placeholder="$t('student.filter.status')" 
            class="filter-item" 
            style="width: 160px;"
            @change="handleSearch"
          >
            <el-option :label="$t('common.all')" value="all" />
            <el-option :label="$t('common.active')" :value="true" />
            <el-option :label="$t('common.inactive')" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('student.filter.identity')">
          <el-select 
            v-model="queryParams.student_type" 
            :placeholder="$t('student.filter.identity')" 
            class="filter-item" 
            style="width: 160px;"
            @change="handleSearch"
          >
            <el-option :label="$t('common.all')" value="all" />
            <el-option :label="$t('student.type.formal')" value="formal" />
            <el-option :label="$t('student.type.trial')" value="trial" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">{{ $t('common.search') }}</el-button>
          <el-button :icon="Refresh" @click="resetQuery">{{ $t('common.btnReset') }}</el-button>
        </el-form-item>

        <div class="spacer"></div>
      </el-form>
    </el-card>

    <!-- Student Table -->
    <el-card>
      <el-table :data="studentList" style="width: 100%" v-loading="loading" stripe>
        <!-- Student No -->
        <el-table-column prop="student_no" :label="$t('student.studentNo')" min-width="120" />
        
        <!-- Name -->
        <el-table-column prop="name" :label="$t('common.name')" min-width="160" />
        
        <!-- Email -->
        <el-table-column prop="email" :label="$t('common.email')" min-width="240" />

        <!-- Phone -->
        <el-table-column prop="phone" :label="$t('common.phone')" min-width="120" />

        <!-- Type -->
        <el-table-column :label="$t('student.filter.identity')" width="120">
           <template #default="{ row }">
             <el-tag :type="row.student_type === 'formal' ? 'success' : 'info'" effect="dark">
               {{ row.student_type === 'formal' ? $t('student.type.formal') : $t('student.type.trial') }}
             </el-tag>
           </template>
        </el-table-column>
        
        <!-- Status -->
        <el-table-column :label="$t('common.status')" width="100">
           <template #default="{ row }">
             <el-tag :type="row.is_active ? 'success' : 'danger'">
               {{ row.is_active ? $t('common.active') : $t('common.inactive') }}
             </el-tag>
           </template>
        </el-table-column>

        <!-- Actions -->
        <el-table-column :label="$t('common.actions')" width="280" fixed="right">
          <template #default="{ row }">
            <el-button v-permission="'students.edit'" size="small" :icon="Edit" @click="openManageDrawer(row)">
              {{ $t('student.detailsTitle') }}
            </el-button>
            <el-button 
              v-if="row.student_type === 'trial'"
              type="primary" 
              size="small" 
              link
              @click="openConvertToFormalDialog(row)"
              v-permission="'students.contracts'"
            >
              {{ $t('student.convertToFormal') }}
            </el-button>
            <el-button 
              type="danger" 
              size="small" 
              link
              @click="handleDelete(row)"
              v-permission="'students.delete'"
            >
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
            @size-change="fetchData"
            @current-change="fetchData"
         />
      </div>
    </el-card>

    <!-- Manage / Details Drawer -->
    <el-drawer
      v-model="drawerVisible"
      :title="isAddMode ? 'Add Student' : (currentStudent.name || 'Student Details')"
      size="600px"
    >
      <el-tabs v-model="activeTab" v-if="!isAddMode">
        <!-- Tab 1: Basic Info -->
        <el-tab-pane label="基本資料 (Basic Info)" name="basic">
          <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
              <el-form-item :label="$t('common.name')" prop="name">
                  <el-input v-model="form.name" />
              </el-form-item>
              <el-form-item :label="$t('common.email')" prop="email">
                  <el-input v-model="form.email" />
              </el-form-item>
              <el-form-item :label="$t('common.phone')" prop="phone">
                  <el-input v-model="form.phone" />
              </el-form-item>
              <el-form-item :label="$t('common.address')" prop="address">
                  <el-input v-model="form.address" />
              </el-form-item>
              <el-form-item :label="$t('common.birthday')" prop="birth_date">
                  <el-date-picker 
                      v-model="form.birth_date" 
                      type="date" 
                      value-format="YYYY-MM-DD" 
                  />
              </el-form-item>
              <el-form-item>
                  <el-button type="primary" @click="handleSaveBasicInfo" :loading="saving" v-permission="'students.edit'">
                      {{ $t('common.save') }}
                  </el-button>
              </el-form-item>
          </el-form>
      </el-tab-pane>

      <!-- Tab 2: Contracts -->
      <el-tab-pane label="合約管理 (Contracts)" name="contracts">
          <div class="skeleton-content">
              <p class="text-gray">Contract management under construction...</p>
          </div>
      </el-tab-pane>

      <!-- Tab 3: Courses -->
      <el-tab-pane label="選課紀錄 (Courses)" name="courses">
          <div class="skeleton-content">
              <p class="text-gray">Course records under construction...</p>
          </div>
      </el-tab-pane>
    </el-tabs>

    <!-- Add Form (when isAddMode is true) -->
    <el-form v-else :model="addForm" :rules="addRules" ref="addFormRef" label-width="120px">
          <el-form-item label="Student No" prop="student_no">
            <el-input v-model="addForm.student_no" />
        </el-form-item>
          <el-form-item :label="$t('common.name')" prop="name">
            <el-input v-model="addForm.name" />
        </el-form-item>
        <el-form-item :label="$t('common.email')" prop="email">
            <el-input v-model="addForm.email" />
        </el-form-item>
        <el-form-item :label="$t('common.phone')" prop="phone">
            <el-input v-model="addForm.phone" />
        </el-form-item>
        <el-form-item :label="$t('common.address')" prop="address">
            <el-input v-model="addForm.address" />
        </el-form-item>
        <el-form-item label="Birth Date" prop="birth_date">
            <el-date-picker 
                v-model="addForm.birth_date" 
                type="date" 
                value-format="YYYY-MM-DD" 
            />
        </el-form-item>
        <el-form-item label="Type" prop="student_type">
            <el-select v-model="addForm.student_type">
                <el-option label="Formal" value="formal" />
                <el-option label="Trial" value="trial" />
            </el-select>
        </el-form-item>
        <el-form-item label="Active" prop="is_active">
            <el-switch v-model="addForm.is_active" />
        </el-form-item>
        <el-form-item>
            <el-button type="primary" @click="handleCreateStudent" :loading="saving" v-permission="'students.create'">
                {{ $t('common.save') }}
            </el-button>
        </el-form-item>
      </el-form>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { Search, Plus, Edit, Refresh } from '@element-plus/icons-vue';
import { 
  getStudentList, 
  createStudent, 
  updateStudent, 
  deleteStudent,
  type StudentListParams,
  type StudentResponse,
  type StudentCreate,
  type StudentUpdate
} from '@/api/student';

// --- List State ---
const loading = ref(false);
const studentList = ref<StudentResponse[]>([]);
const total = ref(0);

const queryParams = reactive<StudentListParams>({
  page: 1,
  per_page: 10,
  search: '',
  is_active: 'all',
  student_type: 'all'
});

// --- Drawer State ---
const drawerVisible = ref(false);
const isAddMode = ref(false);
const activeTab = ref('basic');
const currentStudent = ref<Partial<StudentResponse>>({});
const saving = ref(false);

// Refs for forms
const formRef = ref<FormInstance>();
const addFormRef = ref<FormInstance>();

// --- Forms ---
// Basic Info Update Form
const form = reactive<StudentUpdate>({
  name: '',
  email: '',
  phone: '',
  address: '',
  birth_date: ''
});

const rules = reactive<FormRules>({
  name: [{ required: true, message: 'Name is required' }],
  email: [{ required: true, message: 'Email is required', type: 'email' }]
});

// Add Student Form
const addForm = reactive<StudentCreate>({
  student_no: '',
  name: '',
  email: '',
  phone: '',
  address: '',
  birth_date: '',
  student_type: 'formal',
  is_active: true
});

const addRules = reactive<FormRules>({
  student_no: [{ required: true, message: 'Student No is required' }],
  name: [{ required: true, message: 'Name is required' }],
  email: [{ required: true, message: 'Email is required', type: 'email' }]
});

// --- Methods ---

const fetchData = async () => {
  loading.value = true;
  try {
    const params: any = { ...queryParams };
    if (params.is_active === 'all') {
      delete params.is_active;
    }
    if (params.student_type === 'all') {
      delete params.student_type;
    }
    
    const res: any = await getStudentList(params);
    const data = res.data;
    
    studentList.value = data || [];
    total.value = data.total || 0;
  } catch (err) {
    console.error(err);
    ElMessage.error('Failed to fetch students');
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  queryParams.page = 1;
  fetchData();
};

const resetQuery = () => {
  queryParams.page = 1;
  queryParams.search = '';
  queryParams.is_active = 'all';
  queryParams.student_type = 'all';
  fetchData();
};

const openAddDrawer = () => {
  isAddMode.value = true;
  Object.assign(addForm, {
    student_no: '',
    name: '',
    email: '',
    phone: '',
    address: '',
    birth_date: '',
    student_type: 'formal',
    is_active: true
  });
  drawerVisible.value = true;
};

const openManageDrawer = (row: StudentResponse) => {
  isAddMode.value = false;
  activeTab.value = 'basic';
  currentStudent.value = row;
  
  Object.assign(form, {
    name: row.name,
    email: row.email,
    phone: row.phone,
    address: row.address,
    birth_date: row.birth_date
  });
  
  drawerVisible.value = true;
};

const handleCreateStudent = async () => {
  if (!addFormRef.value) return;
  await addFormRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true;
      try {
        await createStudent(addForm);
        ElMessage.success('Student created successfully');
        drawerVisible.value = false;
        fetchData();
      } catch (err) {
        console.error(err);
        ElMessage.error('Failed to create student');
      } finally {
        saving.value = false;
      }
    }
  });
};

const handleSaveBasicInfo = async () => {
  if (!formRef.value || !currentStudent.value.id) return;
  await formRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true;
      try {
        await updateStudent(currentStudent.value.id, form);
        ElMessage.success('Basic info updated');
        fetchData();
      } catch (err) {
        console.error(err);
        ElMessage.error('Failed to update student');
      } finally {
        saving.value = false;
      }
    }
  });
};

const handleDelete = (row: StudentResponse) => {
  ElMessageBox.confirm(
    `Are you sure you want to delete ${row.name}?`,
    'Warning',
    {
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      type: 'warning',
    }
  ).then(async () => {
    try {
      await deleteStudent(row.id);
      ElMessage.success('Student deleted');
      fetchData();
    } catch (err) {
      console.error(err);
      ElMessage.error('Failed to delete student');
    }
  }).catch(() => {});
};

const openConvertToFormalDialog = (row: StudentResponse) => {
  ElMessage.info('Convert to Formal dialog to be implemented');
};

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.student-list-page {
  padding: 0 10px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.pagination-footer { 
  display: flex; 
  justify-content: flex-end; 
  margin-top: 20px; 
}
.filter-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}
.filter-item {
  min-width: 150px;
}
.mb-20 { margin-bottom: 20px; }
.text-gray { color: #909399; }
.skeleton-content {
  padding: 20px;
  text-align: center;
}
</style>
