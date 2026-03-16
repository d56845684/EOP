<template>
  <div class="student-list-page">
    <!-- Search / Filter Bar -->
    <div class="page-header">
      <h3 class="my-0">{{ $t('menu.student_mgmt') }}</h3>
      <el-button 
        type="primary" 
        @click="openDrawer(null, 'add')"
        v-permission="'students.create'"
      >
        <template #icon>
          <div class="i-hugeicons:plus-sign-square" />
        </template>
        {{ $t('student.add') }}
      </el-button>
    </div>
    <el-card class="filter-card mb-20px">
      <el-form :inline="true" :model="queryParams" label-position="top" class="filter-form flex items-end">
        <el-form-item :label="$t('common.searchKeyword')">
          <el-input 
            v-model="queryParams.search" 
            :placeholder="$t('student.filter.keyword')" 
            class="filter-item" 
            clearable 
            style="width: 300px;" 
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <div class="i-hugeicons:search-list-02" />
            </template>
          </el-input>
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
          <el-button type="primary" @click="handleSearch">
            <template #icon>
              <div class="i-hugeicons:search-list-02" />
            </template>
            {{ $t('common.search') }}
          </el-button>
          <el-button @click="resetQuery">
            <template #icon>
              <div class="i-hugeicons:arrow-reload-horizontal" />
            </template>
            {{ $t('common.btnReset') }}
          </el-button>
        </el-form-item>

        <div class="spacer"></div>
      </el-form>
    </el-card>

    <!-- Student Table -->
    <el-card>
      <el-table :data="studentList" class="w-full" v-loading="loading" stripe>
        <!-- Student No -->
        <el-table-column prop="student_no" :label="$t('student.studentNo')" min-width="120" />
        
        <!-- Name -->
        <el-table-column prop="name" :label="$t('common.name')" width="180">
          <template #default="{ row }">
            <div class="flex items-center justify-between gap-2">
              <span>{{ row.name }}</span>
              <el-tag 
                :type="row.student_type === 'formal' ? 'success' : 'info'" 
                :color="row.student_type === 'formal' ? '#d5f0e1' : '#dfe0f2'" 
                effect="dark" 
                size="small"
                :style="{ 
                  borderColor: row.student_type === 'formal'? '#91b5a1' : '#afb0c4' ,
                  color: row.student_type === 'formal'? '#288a52' : '#707187' 
                }"
              >
               {{ row.student_type === 'formal' ? $t('student.type.formal') : $t('student.type.trial') }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <!-- Type -->
        <!-- <el-table-column :label="$t('student.filter.identity')" width="100" align="center">
           <template #default="{ row }">
             <el-tag :type="row.student_type === 'formal' ? 'success' : 'info'" :color="row.student_type === 'formal' ? '#66c18c' : '#a7a8bd'" effect="dark">
               {{ row.student_type === 'formal' ? $t('student.type.formal') : $t('student.type.trial') }}
             </el-tag>
           </template>
        </el-table-column> -->
        
        <!-- Email -->
        <el-table-column prop="email" :label="$t('common.email')" min-width="240" />

        <!-- Phone -->
        <el-table-column prop="phone" :label="$t('common.phone')" min-width="120" />
        
        <!-- Status -->
        <el-table-column :label="$t('common.status')" width="90" align="center">
           <template #default="{ row }">
             <el-tag :type="row.is_active ? 'success' : 'warning'">
               {{ row.is_active ? $t('common.active') : $t('common.inactive') }}
             </el-tag>
           </template>
        </el-table-column>

        <!-- Actions -->
        <el-table-column :label="$t('common.actions')" width="240" fixed="right" class-name="action-column">
          <template #default="{ row }">
            <div>
              <el-button v-permission="'students.edit'" size="small" @click="openDrawer(row, 'manage')">
                <template #icon>
                  <div class="i-hugeicons:pencil-edit-01" />
                </template>
                {{ $t('student.detailsTitle') }}
              </el-button>
              <el-button 
                v-if="row.student_type === 'trial' && !row._contract_id"
                type="primary" 
                size="small" 
                link
                @click="openConvertToFormalDialog(row)"
                v-permission="'students.contracts'"
              >
                轉正
              </el-button>
              <el-button
                v-if="row.student_type === 'formal'"
                v-permission="'students.contracts'"
                color="#82aa57"
                size="small"
                plain
                @click="openDrawer(row, 'contract')"
              >
                <template #icon>
                  <div class="i-hugeicons:legal-document-02" />
                </template>
                合約
              </el-button>
            </div>
            <el-button 
              type="danger" 
              size="large" 
              link
              @click="handleDelete(row)"
              v-permission="'students.delete'"
            >
              <div class="i-hugeicons:delete-02" />
              <!-- {{ $t('common.delete') }} -->
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
      :title="drawerType !== 'add' ? (currentStudent.student_no + ' - ' + currentStudent.name || $t('student.detailsTitle')) : $t('student.addTitle')"
      :size="drawerType === 'add' ? '480px' : '620px'"
      class="student-drawer"
    >
      <template v-if="drawerType === 'manage'">
        <el-tabs v-model="activeTab"  @tab-change="loadContent">
          <!-- Tab 1: Basic Info -->
          <el-tab-pane :label="$t('student.basicInfo')" name="basic">
            <BaseInfo
              :form="form"
              :rules="rules"
              :saving="saving"
              @saveBasicInfo="handleSaveBasicInfo"
            />
          </el-tab-pane>

          <!-- Tab 2: Courses -->
          <el-tab-pane v-permission="'bookings.list'" :label="$t('student.courses')" name="courses">
            <BookingList 
              v-if="activeTab === 'courses' && currentStudent?.id" 
              :student-id="currentStudent.id" 
            />
          </el-tab-pane>
        </el-tabs>
      </template>
      <template v-if="drawerType === 'add'">
        <CreateStudent
          :saving="saving"
          @createStudent="handleCreateStudent"
        />
      </template>
      <template v-else-if="drawerType === 'contract'">
        <ContractManagement
          v-if="contract"
          :contract="contract" 
          :contractLoading="contractLoading"
          :leaveRecords="leaveRecords"
          :contractDetails="contractDetails"
          @updateContractDetails="fetchContractDependencies"
          @saveContractData="saveContractData"
          @updateContent="loadContent"
        />
        <div v-else class="skeleton-content">
          <p class="text-[#909399]" v-if="!contractLoading">目前無合約紀錄</p>
          <el-button type="primary" @click="openConvertToFormalDialog(currentStudent as StudentResponse)">
            <template #icon><div class="i-hugeicons:add-square" /></template>
            新增合約
          </el-button>
        </div>
      </template>
    </el-drawer>

    <!-- Convert to Formal Dialog -->
     <CreateContractDialog
       v-model:convertVisible="convertVisible"
       :currentStudent="currentConvertStudent"
       :bookingOptions="bookingOptions"
       :teacherOptions="teacherOptions"
     />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox, type FormRules } from 'element-plus';
import { 
  getStudentList, 
  createStudent, 
  updateStudent, 
  deleteStudent,
  type StudentListParams,
  type StudentResponse,
  type StudentCreate,
  type StudentUpdate,
} from '@/api/student';
import {
  getStudentContracts,
  updateStudentContract,
  getContractDetails,
  getContractLeaveRecords,
  getContractTeacherOptions,
  type StudentContract,
  type StudentContractUpdate,
  type StudentContractDetail,
  type StudentContractLeaveRecord,
} from '@/api/contract';
import { getBookingList, type BookingItem } from '@/api/booking';
import BaseInfo from './components/BaseInfo.vue';
import BookingList from './components/BookingList.vue';
import ContractManagement from './components/ContractManagement.vue';
import CreateStudent from './components/CreateStudent.vue';
import CreateContractDialog from './components/CreateContractDialog.vue';

const { t } = useI18n();

// --- List State ---
const loading = ref(false);
const studentList = ref<any[]>([]);
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
const drawerType = ref('manage');
const activeTab = ref('basic');
const currentStudent = ref<Partial<StudentResponse>>({});
const saving = ref(false);

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
  email: [{ required: true, message: 'Email is required', type: 'email' }],
  birth_date: [{ required: true, message: 'Birth Date is required' }],
});


// --- Contracts Feature State ---
const contract = ref<StudentContract | null>(null);
const contractLoading = ref(false);
const savingContract = ref(false);

const contractDetails = ref<StudentContractDetail[]>([]);
const leaveRecords = ref<StudentContractLeaveRecord[]>([]);

// --- Booking Feature State ---
const booking = ref<BookingItem | null>(null);
const bookingLoading = ref(false);
const bookingForm = reactive<Partial<BookingItem>>({});


// --- Convert to Formal State ---
const convertVisible = ref(false);
const currentConvertStudent = ref<StudentResponse | null>(null);

const bookingOptions = ref<any[]>([]);
const teacherOptions = ref<any[]>([]);

// --- Methods ---

const fetchData = async () => {
  loading.value = true;
  try {
    const params: any = { ...queryParams };
    if (params.is_active === 'all') delete params.is_active;
    if (params.student_type === 'all') delete params.student_type;
    
    const res: any = await getStudentList(params);
    
    studentList.value = res?.data?.items || res?.data || [];
    total.value = res?.total || 0;
  } catch (err) {
    console.error(err);
    ElMessage.error('獲取學生列表失敗');
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

const openDrawer = async (row: StudentResponse | null, type: string) => {
  drawerType.value = type;
  if (row) {
    currentStudent.value = row;
  }

  if (type === 'manage' && row) {
    activeTab.value = 'basic';
    Object.assign(form, {
      name: row.name,
      email: row.email,
      phone: row.phone,
      address: row.address,
      birth_date: row.birth_date
    });
  }

  if (type === 'contract' && row) {
    await loadContent('contracts');
  }

  drawerVisible.value = true;
}

const handleCreateStudent = async (data: StudentCreate) => {
  saving.value = true;
  try {
    await createStudent(data);
    ElMessage.success('新增學生操作成功');
    drawerVisible.value = false;
    fetchData();
  } catch (err: any) {
    console.error(err);
    ElMessage.error('新增學生操作失敗');
  } finally {
    saving.value = false;
  }
};

const handleSaveBasicInfo = async () => {
  if (!currentStudent.value.id) return;
  saving.value = true;
  try {
    await updateStudent(currentStudent.value.id!, form);
    ElMessage.success('更新學生資料成功');
    fetchData();
  } catch (err) {
    console.error(err);
    ElMessage.error('更新學生資料失敗');
  } finally {
    saving.value = false;
  }
};

const handleDelete = (row: StudentResponse) => {
  ElMessageBox.confirm(
    `Are you sure you want to delete ${row.student_no}-${row.name}?`,
    'Warning',
    {
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    }
  ).then(async () => {
    try {
      await deleteStudent(row.id);
      ElMessage.success('刪除操作成功');
      fetchData();
    } catch (err) {
      console.error(err);
      ElMessage.error('刪除操作失敗');
    }
  }).catch(() => {});
};

// --- Convert To Formal API ---
const openConvertToFormalDialog = async (row: StudentResponse) => {
  currentConvertStudent.value = row;
  convertVisible.value = true;
  
  try {
    const [bookRes, teacherRes] = await Promise.all([
      getBookingList({ student_id: row.id, booking_status: 'completed' }),
      getContractTeacherOptions()
    ]);
    bookingOptions.value = (bookRes.data as any)?.data || [];
    teacherOptions.value = (teacherRes.data as any) || [];
  } catch (err) {
    console.error(err);
  }
};

// --- Contract Tab API ---
const loadContent = async (tabName: string | number) => {
  switch (tabName) {
    case 'contracts':
      await loadContract()
      break;
    case 'records':
      await loadBookingList()
      break;
  
    default:
      break;
  }
};

const loadContract = async () => {
  if (!currentStudent.value?.id) return;
  contractLoading.value = true;
  try {
    const res: any = await getStudentContracts({ student_id: currentStudent.value.id });
    const contracts = res.data || [];
    if (contracts.length > 0) {
      contract.value = contracts[0];
      await fetchContractDependencies(contract.value!.id);
    } else {
      contract.value = null;
    }
  } catch (err) {
    console.error(err);
    ElMessage.error('載入合約失敗');
  } finally {
    contractLoading.value = false;
  }
}

const loadBookingList = async () => {
  if (!currentStudent.value?.id) return;
  bookingLoading.value = true;
  try {
    const res: any = await getBookingList({ student_id: currentStudent.value.id });
    const bookings = res.data || [];
    if (bookings.length > 0) {
      booking.value = bookings[0];
      Object.assign(bookingForm, booking.value);
    } else {
      booking.value = null;
    }
  } catch (err) {
    console.error(err);
    ElMessage.error('載入預約失敗');
  } finally {
    bookingLoading.value = false;
  }
}

const fetchContractDependencies = async (contractId: string) => {
  try {
     const [detailsRes, leavesRes] = await Promise.all([
         getContractDetails(contractId),
         getContractLeaveRecords(contractId)
     ]);
     contractDetails.value = (detailsRes.data as any) || [];
     leaveRecords.value = (leavesRes.data as any) || [];
  } catch(err) {
     console.error("載入合約失敗", err);
     ElMessage.error('載入合約失敗');
  }
};

const saveContractData = async (data: StudentContractUpdate) => {
   if(!contract.value) return;
   savingContract.value = true;
   try {
     const payload: StudentContractUpdate = {
       contract_status: data.contract_status,
       is_recurring: data.is_recurring,
       start_date: data.start_date,
       end_date: data.end_date,
       total_lessons: data.total_lessons,
       total_amount: data.total_amount,
       total_leave_allowed: data.total_leave_allowed,
       notes: data.notes
     };
     await updateStudentContract(contract.value.id, payload);
     ElMessage.success('更新合約成功');
     
     // Refresh exactly the loaded tab state to see updated leave limits, etc
     await loadContent('contracts');
   } catch(err) {
     ElMessage.error('更新合約失敗');
   } finally {
     savingContract.value = false;
   }
};

onMounted(() => {
  fetchData();
});
</script>

<style lang="scss" scoped>
.student-list-page {
  padding: 0 10px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
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
.skeleton-content {
  padding: 20px;
  text-align: center;
}
:deep(.filter-form) {
  gap: 20px;
   .el-form-item {
     margin-right: 0;
     margin-bottom: 5px;
   }
}
:deep(.el-table) {
  .action-column {
    .cell {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }
}
// :deep(.el-drawer__header) {
//   margin-bottom: 10px !important;
// }
</style>
