<template>
  <div class="student-list-page pl-2 pr-4">
    <!-- Search / Filter Bar -->
    <div class="flex justify-between items-center px-1 mb-2">
      <h3 class="text-lg my-0">{{ $t('menu.student_mgmt') }}</h3>
      <el-button
        v-if="hasPermission('students.create')"
        type="primary"
        round
        size="small"
        class="h-30px px-2"
        @click="openDrawer(null, drawerTypeMap.CREATE)"
      >
        <template #icon>
          <div class="i-hugeicons:plus-sign-square" />
        </template>
        {{ $t('student.add') }}
      </el-button>
    </div>
    <el-card class="filter-card mb-14px" shadow="never">
      <el-form :inline="true" :model="queryParams" size="small" label-position="top" class="filter-form flex items-end">
        <el-form-item :label="$t('common.searchKeyword')">
          <el-input 
            v-model="queryParams.search" 
            :placeholder="$t('student.filter.keyword')" 
            class="filter-item w-250px h-30px" 
            clearable 
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <div class="i-hugeicons:search-01" />
            </template>
          </el-input>
        </el-form-item>
        <el-form-item :label="$t('student.filter.status')">
          <el-select 
            v-model="queryParams.is_active" 
            :placeholder="$t('student.filter.status')" 
            class="filter-item" 
            style="width: 140px;"
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
            style="width: 140px;"
            @change="handleSearch"
          >
            <el-option :label="$t('common.all')" value="all" />
            <el-option :label="$t('student.type.formal')" value="formal" />
            <el-option :label="$t('student.type.trial')" value="trial" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" round class="h-30px" @click="handleSearch">
            <template #icon>
              <div class="i-hugeicons:search-01" />
            </template>
            {{ $t('common.search') }}
          </el-button>
          <el-button round class="h-30px" @click="resetQuery">
            <template #icon>
              <div class="i-hugeicons:arrow-reload-horizontal" />
            </template>
            {{ $t('common.btnReset') }}
          </el-button>
        </el-form-item>

        <div class="spacer"></div>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <StudentListTable
        :studentList="studentList"
        :loading="loading"
        @openDrawer="openDrawer"
        @openConvertToFormalDialog="openConvertToFormalDialog"
        @handleDelete="handleDelete"
        @handleStatusChange="handleStatusChange"
        @handleVerify="handleVerify"
        @copyEmail="copyEmail"
      />
      <div class="pagination-footer">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.per_page"
          size="small"
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
      :title="drawerType !== drawerTypeMap.CREATE ? (currentStudent.student_no + ' - ' + currentStudent.name || $t('student.detailsTitle')) : $t('student.addTitle')"
      :size="drawerType === drawerTypeMap.CREATE ? '480px' : '620px'"
      class="student-drawer"
    >
      <template v-if="drawerType === drawerTypeMap.MANAGE">
        <el-tabs v-model="activeTab"  @tab-change="loadContent">
          <!-- Tab 1: Basic Info -->
          <el-tab-pane :label="$t('common.basicInfo')" :name="tabType.BASIC">
            <BaseInfo
              :form="form"
              :rules="rules"
              :saving="saving"
              @saveBasicInfo="handleSaveBasicInfo"
            />
          </el-tab-pane>

          <!-- Tab 2: Settings -->
          <el-tab-pane 
            v-if="hasPermission('students.edit') && hasPermission('students.contracts')" 
            :label="$t('studentAdmin.preferenceSetting')" 
            :name="tabType.SETTINGS"
          >
            <Settings 
              v-if="activeTab === tabType.SETTINGS && currentStudent?.id" 
              :student-id="currentStudent.id" 
            />
          </el-tab-pane>

          <!-- Tab 3: Courses -->
          <el-tab-pane v-if="hasPermission('bookings.list')" :label="$t('common.courses')" :name="tabType.RECORDS">
            <BookingList 
              v-if="activeTab === tabType.RECORDS && currentStudent?.id" 
              :student-id="currentStudent.id" 
            />
          </el-tab-pane>
          
        </el-tabs>
      </template>
      <template v-if="drawerType === drawerTypeMap.CREATE">
        <CreateStudent
          :saving="saving"
          @createStudent="handleCreateStudent"
        />
      </template>
      <template v-else-if="drawerType === drawerTypeMap.CONTRACT">
        <ContractManagement
          v-if="contracts.length > 0"
          :contracts="contracts" 
          :contractLoading="contractLoading"
          :hasActive="(currentStudent.active_contracts || 0) > 0"
          :leaveRecords="leaveRecords"
          :contractDetails="contractDetails"
          @updateContractDetails="fetchContractDependencies"
          @saveContractData="saveContractData"
          @updateContent="loadContent"
          @openAddContractDialog="openConvertToFormalDialog(currentStudent as StudentResponse)"
        />
        <div v-else class="skeleton-content">
          <p class="text-[#909399]" v-if="!contractLoading">{{ $t('studentAdmin.noContractRecords') }}</p>
          <el-button v-if="hasPermission('contracts.create')" type="primary" @click="openConvertToFormalDialog(currentStudent as StudentResponse)">
            <template #icon><div class="i-hugeicons:add-square" /></template>
            {{ $t('contract.addContract') }}
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

     <VerifyInviteDialog
       v-model:inviteVisible="verifyInviteVisible"
       role="student"
       :name="currentStudent?.name || ''"
       :email="currentStudent?.email || ''"
       :inviteUrl="inviteUrl"
     />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox, type FormRules } from 'element-plus';
import { 
  getStudentOverviewList,
  getStudentView,
  createStudent, 
  updateStudent, 
  deleteStudent,
  type StudentOverviewListParams,
  type StudentResponse,
  type StudentOverviewListResponse,
  type StudentOverviewResponse,
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
} from '@/api/studentContract';
import { getBookingList, type BookingItem } from '@/api/booking';
import BaseInfo from './components/Drawer/BaseInfo.vue';
import BookingList from './components/Drawer/BookingList.vue';
import ContractManagement from './components/Drawer/ContractManagement.vue';
import CreateStudent from './components/Drawer/CreateStudent.vue';
import Settings from './components/Drawer/Settings.vue';
import CreateContractDialog from './components/Dialog/CreateContractDialog.vue';
import VerifyInviteDialog from '@/components/Auth/VerifyInviteDialog.vue';
import StudentListTable from './components/StudentListTable.vue';
import { generateInviteLinkApi } from '@/api/auth';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { usePermissionStore } from '@/stores/permission';
import { copyToClipboardUtil } from '@/utils/clipboard';

const OPTION_MAP = {
 ALL: 'all' 
} as const

const TAB_MAP = {
  BASIC: 'basic',
  RECORDS: 'records',
  CONTRACT: 'contract',
  SETTINGS: 'settings',
} as const;

// Alias to patch incomplete IDE rename operation
const tabType = TAB_MAP;

const DRAWER_TYPE_MAP = {
  CREATE: 'create',
  MANAGE: 'manage',
  CONTRACT: 'contract',
} as const;

// Alias to patch incomplete IDE rename operation
const drawerTypeMap = DRAWER_TYPE_MAP;

const permissionStore = usePermissionStore();
const hasPermission = (permission: string) => permissionStore.hasPermission(permission);

const { t } = useI18n();

// --- List State ---
const loading = ref(false);
const studentList = ref<any[]>([]);
const total = ref(0);

const queryParams = reactive<StudentOverviewListParams>({
  page: 1,
  per_page: 10,
  search: '',
  is_active: OPTION_MAP.ALL,
  student_type: OPTION_MAP.ALL,
  has_account: OPTION_MAP.ALL,
  has_active_contract: OPTION_MAP.ALL,
  role: OPTION_MAP.ALL,
});

// --- Drawer State ---
const drawerVisible = ref(false);
type DrawerType = typeof DRAWER_TYPE_MAP[keyof typeof DRAWER_TYPE_MAP] | string;
const drawerType = ref<DrawerType>(DRAWER_TYPE_MAP.MANAGE);
type TabValue = typeof TAB_MAP[keyof typeof TAB_MAP];
const activeTab = ref<TabValue>(TAB_MAP.BASIC);
const currentStudent = ref<Partial<StudentOverviewListResponse>>({});
const saving = ref(false);

// --- Forms ---
// Basic Info Update Form
const form = reactive<StudentUpdate>({
  name: '',
  eng_name: '',
  email: '',
  phone: '',
  address: '',
  birth_date: ''
});

const rules = reactive<FormRules>({
  name: [{ required: true, message: t('studentAdmin.validation.nameRequired') }],
  eng_name: [{ required: true, message: t('studentAdmin.validation.engNameRequired') }],
  phone: [{ required: true, message: t('studentAdmin.validation.phoneRequired') }],
  email: [{ required: true, message: t('studentAdmin.validation.emailRequired'), type: 'email' }],
});

const basicLoading = ref(false);
const studentView = ref<StudentOverviewResponse['data'] | null>(null);

// --- Contracts Feature State ---
const contracts = ref<StudentContract[]>([]);
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

const verifyInviteVisible = ref(false);
const inviteUrl = ref('');

// --- Methods ---

const fetchData = async () => {
  loading.value = true;
  try {
    const params: any = { ...queryParams };
    if (params.is_active === OPTION_MAP.ALL) delete params.is_active;
    if (params.student_type === OPTION_MAP.ALL) delete params.student_type;
    if (params.has_account === OPTION_MAP.ALL) delete params.has_account;
    if (params.has_active_contract === OPTION_MAP.ALL) delete params.has_active_contract;
    if (params.role === OPTION_MAP.ALL) delete params.role;
    
    const res = assertApiSuccess(await getStudentOverviewList(params), t('studentAdmin.loadStudentListFailed'));
    studentList.value = res.data || [];
    total.value = res.total || 0;
  } catch (err) {
    console.error(err);
    ElMessage.error(getApiErrorMessage(err, t('studentAdmin.loadStudentListFailed')));
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
  queryParams.is_active = OPTION_MAP.ALL;
  queryParams.student_type = OPTION_MAP.ALL;
  fetchData();
};

const copyEmail = (email: string) => {
  copyToClipboardUtil(email, t('studentAdmin.emailCopied'));
};

const handleVerify = async (row: StudentOverviewListResponse) => {
  try {
    const res = await generateInviteLinkApi({ entity_type: 'student', entity_id: row.id });
    if (res.success === false && res.error_code) {
      ElMessage.error(t('studentAdmin.duplicateEmail'));
      return;
    }
    inviteUrl.value = res.invite_url || '';
    currentStudent.value = row;
    verifyInviteVisible.value = true;
  } catch (err:any) {
    console.error(err);
    if (err.success === false && err.error_code) {
      ElMessage.error(t('studentAdmin.duplicateEmail'));
      return;
    } else {
      ElMessage.error(t('common.operationFailed'));
    }
  }
}

const handleStatusChange = async (row: StudentOverviewListResponse) => {
  const status = row.is_active ? t('common.active') : t('common.inactive');
  try {
    const res = assertApiSuccess(await updateStudent(row.id, { is_active: row.is_active }), t('studentAdmin.updateStatusFailed', { status }));
    ElMessage.success(res.message || t('studentAdmin.updateStatusSuccess', { status }));
  } catch (err) {
    console.error(err);
    ElMessage.error(getApiErrorMessage(err, t('studentAdmin.updateStatusFailed', { status })));
  } finally {
    fetchData();
  }
}

const openDrawer = async (row: StudentOverviewListResponse | null, type: string) => {
  drawerType.value = type;
  if (row) {
    currentStudent.value = row;
  }

  if (type === drawerTypeMap.MANAGE && row) {
    activeTab.value = TAB_MAP.BASIC;
    await loadContent(TAB_MAP.BASIC);
  }

  if (type === drawerTypeMap.CONTRACT && row) {
    await loadContent(TAB_MAP.CONTRACT);
  }

  drawerVisible.value = true;
}

const handleCreateStudent = async (data: StudentCreate) => {
  saving.value = true;
  try {
    const res = assertApiSuccess(await createStudent(data), t('studentAdmin.createStudentFailed'));
    ElMessage.success(res.message || t('studentAdmin.createStudentSuccess'));
    drawerVisible.value = false;
    fetchData();
  } catch (err: any) {
    console.error(err);
    ElMessage.error(getApiErrorMessage(err, t('studentAdmin.createStudentFailed')));
  } finally {
    saving.value = false;
  }
};

const handleSaveBasicInfo = async () => {
  if (!currentStudent.value.id) return;
  saving.value = true;
  try {
    const res = assertApiSuccess(await updateStudent(currentStudent.value.id!, form), t('studentAdmin.updateStudentFailed'));
    ElMessage.success(res.message || t('studentAdmin.updateStudentSuccess'));
    fetchData();
  } catch (err) {
    console.error(err);
    ElMessage.error(getApiErrorMessage(err, t('studentAdmin.updateStudentFailed')));
  } finally {
    saving.value = false;
  }
};

const handleDelete = (row: StudentResponse) => {
  ElMessageBox.confirm(
    t('common.deleteConfirm', { name: `${row.student_no}-${row.name}` }),
    t('studentAdmin.warning'),
    {
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
      confirmButtonClass: 'el-button--danger',
      type: 'warning',
      roundButton: true,
      buttonSize: 'small',
    }
  ).then(async () => {
    try {
      const res = assertApiSuccess(await deleteStudent(row.id), t('common.deleteFailed'));
      ElMessage.success(res.message || t('common.deleteSuccess'));
      fetchData();
    } catch (err) {
      console.error(err);
      ElMessage.error(getApiErrorMessage(err, t('common.deleteFailed')));
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
    bookingOptions.value = assertApiSuccess(bookRes).data || [];
    teacherOptions.value = assertApiSuccess(teacherRes).data || [];
  } catch (err) {
    console.error(err);
  }
};

// --- Contract Tab API ---
const loadContent = async (tabName: string | number) => {
  switch (tabName) {
    case TAB_MAP.CONTRACT:
      await loadContract()
      break;
    case TAB_MAP.SETTINGS:
      // Settings component handles its own load when mounted
      break;
    case TAB_MAP.RECORDS:
      await loadBookingList()
      break;
    default:
      await loadBasicInfo()
      break;
  }
};

const loadBasicInfo = async () => {
  if (!currentStudent.value?.id) return;
  basicLoading.value = true;
  try {
    const res = assertApiSuccess(await getStudentView(currentStudent.value.id), t('studentAdmin.loadBasicInfoFailed'));
    studentView.value = res.data;
    Object.assign(form, {
      name: studentView.value?.student?.name,
      eng_name: studentView.value?.student?.eng_name,
      email: studentView.value?.student?.email,
      phone: studentView.value?.student?.phone,
      address: studentView.value?.student?.address,
      birth_date: studentView.value?.student?.birth_date
    });
  } catch (err) {
    console.error(err);
    ElMessage.error(getApiErrorMessage(err, t('studentAdmin.loadBasicInfoFailed')));
  } finally {
    basicLoading.value = false;
  }
}

const loadContract = async () => {
  if (!currentStudent.value?.id) return;
  contractLoading.value = true;
  try {
    const res = assertApiSuccess(await getStudentContracts({ student_id: currentStudent.value.id }), t('studentAdmin.loadContractsFailed'));
    const fetchedContracts = res.data || [];
    if (fetchedContracts.length > 0) {
      contracts.value = fetchedContracts;
      await fetchContractDependencies(contracts.value[0]!.id as string);
    } else {
      contracts.value = [];
    }
  } catch (err) {
    console.error(err);
    ElMessage.error(getApiErrorMessage(err, t('studentAdmin.loadContractsFailed')));
  } finally {
    contractLoading.value = false;
  }
}

const loadBookingList = async () => {
  if (!currentStudent.value?.id) return;
  bookingLoading.value = true;
  try {
    const res = assertApiSuccess(await getBookingList({ student_id: currentStudent.value.id }), t('studentAdmin.loadBookingsFailed'));
    const bookings = res.data || [];
    if (bookings.length > 0) {
      booking.value = bookings[0]!;
      Object.assign(bookingForm, booking.value);
    } else {
      booking.value = null;
    }
  } catch (err) {
    console.error(err);
    ElMessage.error(getApiErrorMessage(err, t('studentAdmin.loadBookingsFailed')));
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
     contractDetails.value = assertApiSuccess(detailsRes).data || [];
     leaveRecords.value = assertApiSuccess(leavesRes).data || [];
  } catch(err) {
     console.error(t('studentAdmin.loadContractsFailed'), err);
     ElMessage.error(getApiErrorMessage(err, t('studentAdmin.loadContractsFailed')));
  }
};

const saveContractData = async (data: StudentContractUpdate) => {
   if(!contracts.value.length) return;
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
     const contractId = contracts.value[0]?.id;
     if (!contractId) throw new Error('Contract ID string is undefined');
     const res = assertApiSuccess(await updateStudentContract(contractId, payload), t('studentAdmin.updateContractFailed'));
     ElMessage.success(res.message || t('studentAdmin.updateContractSuccess'));
     
     // Refresh exactly the loaded tab state to see updated leave limits, etc
     await loadContent('contracts');
   } catch(err) {
     ElMessage.error(getApiErrorMessage(err, t('studentAdmin.updateContractFailed')));
   } finally {
     savingContract.value = false;
   }
};

onMounted(() => {
  fetchData();
});
</script>

<style lang="scss" scoped>
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
</style>
