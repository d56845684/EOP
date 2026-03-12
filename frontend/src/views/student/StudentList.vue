<template>
  <div class="student-list-page">
    <!-- Search / Filter Bar -->
    <div class="page-header">
      <h3 class="my-0">{{ $t('menu.student_mgmt') }}</h3>
      <el-button 
        type="primary" 
        :icon="Plus" 
        @click="openDrawer(null, 'add')"
        v-permission="'students.create'"
      >
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
        <el-table-column prop="name" :label="$t('common.name')" align="center" min-width="160" />

        <!-- Type -->
        <el-table-column :label="$t('student.filter.identity')" width="100" align="center">
           <template #default="{ row }">
             <el-tag :type="row.student_type === 'formal' ? 'success' : 'info'" :color="row.student_type === 'formal' ? '#66c18c' : '#a7a8bd'" effect="dark">
               {{ row.student_type === 'formal' ? $t('student.type.formal') : $t('student.type.trial') }}
             </el-tag>
           </template>
        </el-table-column>
        
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
      size="660px"
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
          @openAddDetailDialog="openAddDetailDialog"
          @submitLeaveForm="submitLeaveForm"
          @deleteLeave="deleteLeave"
          @saveContractData="saveContractData"
        />
        <div v-else class="skeleton-content">
            <p class="text-[#909399]" v-if="!contractLoading">無合約紀錄</p>
        </div>
      </template>
    </el-drawer>

    <!-- Convert to Formal Dialog -->
    <el-dialog v-model="convertVisible" :title="`${currentConvertStudent?.name}(${currentConvertStudent?.student_no}) - 轉正`" width="500px">
      <el-form :model="convertForm" :rules="convertRules" ref="convertFormRef" label-width="120px" @submit.prevent>
        <el-form-item label="合約編號" prop="contract_no">
          <el-input v-model="convertForm.contract_no" placeholder="請輸入合約編號"></el-input>
        </el-form-item>
        <el-form-item label="總堂數" prop="total_lessons">
          <el-input-number v-model="convertForm.total_lessons" :min="1" class="w-full"></el-input-number>
        </el-form-item>
        <el-form-item label="合約總金額" prop="total_amount">
          <el-input-number v-model="convertForm.total_amount" :min="0" class="w-full"></el-input-number>
        </el-form-item>
        <el-form-item label="起迄日期" prop="dateRange">
          <el-date-picker v-model="convertForm.dateRange" type="daterange" value-format="YYYY-MM-DD" class="w-full"></el-date-picker>
        </el-form-item>
        <el-form-item label="關聯試上預約">
          <el-select v-model="convertForm.booking_id" :disabled="bookingOptions.length === 0" :placeholder="bookingOptions.length > 0 ? '請選擇' : '無預約紀錄'" class="w-full" clearable>
            <el-option v-for="b in bookingOptions" :key="b.id" :label="b.booking_no + ' - ' + b.booking_date" :value="b.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="指定教師">
          <el-select v-model="convertForm.teacher_id" placeholder="請選擇教師(選填)" class="w-full" clearable>
            <el-option v-for="t in teacherOptions" :key="t.id" :label="t.name" :value="t.id"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="備註">
          <el-input type="textarea" v-model="convertForm.notes" :rows="3"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="convertVisible = false">取消</el-button>
        <el-button type="primary" :loading="converting" @click="submitConvert">確認轉正</el-button>
      </template>
    </el-dialog>

    <!-- Add Contract Detail Dialog -->
    <el-dialog v-model="detailVisible" title="新增合約明細" width="360px">
      <el-form :model="detailForm" :rules="detailRules" ref="detailFormRef" label-width="120px" label-position="top" @submit.prevent>
        <el-form-item label="類型" prop="detail_type">
          <el-select v-model="detailForm.detail_type" class="w-full">
            <el-option label="課程單價" value="lesson_price"></el-option>
            <el-option label="優惠折扣" value="discount"></el-option>
            <el-option label="補償堂數" value="compensation"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="課程" prop="course_id" v-if="detailForm.detail_type === 'lesson_price'">
          <el-select v-model="detailForm.course_id" class="w-full" clearable>
            <el-option v-for="c in detailCourseOptions" :key="c.value" :label="c.label" :value="c.value"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="說明" prop="description">
          <el-input v-model="detailForm.description" maxlength="100" show-word-limit></el-input>
        </el-form-item>
        <el-form-item label="金額" prop="amount">
          <el-input-number v-model="detailForm.amount" class="w-full"></el-input-number>
        </el-form-item>
        <el-form-item label="備註">
          <el-input type="textarea" v-model="detailForm.notes"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="detailVisible = false">取消</el-button>
        <el-button type="primary" :loading="detailLoading" @click="submitDetailForm">新增</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { Search, Plus, Edit, Refresh } from '@element-plus/icons-vue';
import { 
  getStudentList, 
  createStudent, 
  updateStudent, 
  deleteStudent,
  convertToFormal,
  type StudentListParams,
  type StudentResponse,
  type StudentCreate,
  type StudentUpdate,
  type ConvertToFormalRequest
} from '@/api/student';
import {
  getStudentContracts,
  updateStudentContract,
  getContractDetails,
  createContractDetail,
  getContractLeaveRecords,
  createContractLeaveRecord,
  deleteContractLeaveRecord,
  getContractTeacherOptions,
  getContractCourseOptions,
  getContractDownloadUrl,
  type StudentContract,
  type StudentContractUpdate,
  type StudentContractDetail,
  type StudentContractDetailCreate,
  type StudentContractLeaveRecord,
  type StudentContractLeaveRecordCreate
} from '@/api/contract';
import { getBookingList, type BookingItem } from '@/api/booking';
import BaseInfo from './components/BaseInfo.vue';
import BookingList from './components/BookingList.vue';
import ContractManagement from './components/ContractManagement.vue';
import CreateStudent from './components/CreateStudent.vue';

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
const contractForm = reactive<StudentContractUpdate & { dateRange: [string, string] }>({
  contract_status: 'pending',
  is_recurring: false,
  dateRange: ['', ''],
  start_date: '',
  end_date: '',
  total_lessons: 0,
  total_amount: 0,
  total_leave_allowed: 0,
  notes: ''
});

const contractDetails = ref<StudentContractDetail[]>([]);
const detailVisible = ref(false);
const detailLoading = ref(false);
const detailCourseOptions = ref<any[]>([]);
const detailFormRef = ref<FormInstance>();
const detailForm = reactive<StudentContractDetailCreate>({
  detail_type: 'lesson_price',
  course_id: '',
  description: '',
  amount: 0,
  notes: ''
});
const detailRules = reactive<FormRules>({});

const leaveRecords = ref<StudentContractLeaveRecord[]>([]);
const leaveLoading = ref(false);
const leaveForm = reactive<StudentContractLeaveRecordCreate>({
  leave_date: '',
  reason: ''
});

// --- Booking Feature State ---
const booking = ref<BookingItem | null>(null);
const bookingLoading = ref(false);
const bookingForm = reactive<Partial<BookingItem>>({});


// --- Convert to Formal State ---
const convertVisible = ref(false);
const converting = ref(false);
const convertFormRef = ref<FormInstance>();
const currentConvertStudent = ref<StudentResponse | null>(null);

const convertForm = reactive({
  contract_no: '',
  total_lessons: 1,
  total_amount: 0,
  dateRange: ['', ''] as unknown as [string, string],
  teacher_id: '',
  booking_id: '',
  notes: ''
});

const convertRules = reactive<FormRules>({
  contract_no: [{ required: true, message: 'Required', trigger: 'blur' }],
  total_lessons: [{ required: true, message: 'Required', trigger: 'blur' }],
  total_amount: [{ required: true, message: 'Required', trigger: 'blur' }],
  dateRange: [{ required: true, message: 'Required', trigger: 'change' }]
});

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
const openConvertToFormalDialog = async (row: any) => {
  currentConvertStudent.value = row;
  Object.assign(convertForm, {
    contract_no: '',
    total_lessons: 1,
    total_amount: 0,
    dateRange: ['', ''],
    teacher_id: '',
    booking_id: '',
    notes: ''
  });
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

const submitConvert = async () => {
  if (!convertFormRef.value) return;
  await convertFormRef.value.validate(async valid => {
    if (valid && currentConvertStudent.value) {
      converting.value = true;
      try {
        const payload: ConvertToFormalRequest = {
          contract_no: convertForm.contract_no,
          total_lessons: convertForm.total_lessons,
          total_amount: convertForm.total_amount,
          start_date: convertForm.dateRange[0],
          end_date: convertForm.dateRange[1],
          teacher_id: convertForm.teacher_id || null,
          booking_id: convertForm.booking_id || null,
          notes: convertForm.notes || null,
        };
        const res: any = await convertToFormal(currentConvertStudent.value.id, payload);
        ElMessage.success('轉換學生身份成功');
        
        const rowAny: any = currentConvertStudent.value;
        rowAny.student_type = 'formal';
        rowAny._contract_id = res.data?.contract?.id || res.data?.id || res.contract?.id;
        
        convertVisible.value = false;
      } catch (err) {
         ElMessage.error('轉換學生身份失敗');
      } finally {
        converting.value = false;
      }
    }
  });
};

const downloadContract = async (contractId: string) => {
  try {
    const res: any = await getContractDownloadUrl(contractId);
    if (res.data && res.data.url) {
      window.open(res.data.url, '_blank');
    } else {
      ElMessage.warning('無法下載合約');
    }
  } catch (err) {
    ElMessage.error('合約下載失敗');
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
      Object.assign(contractForm, { 
        contract_status: contract.value?.contract_status || 'pending',
        is_recurring: contract.value?.is_recurring || false,
        total_lessons: contract.value?.total_lessons || 0,
        total_amount: contract.value?.total_amount || 0,
        total_leave_allowed: contract.value?.total_leave_allowed,
        notes: contract.value?.notes || ''
      });
      contractForm.dateRange = [(contract.value as any).start_date, (contract.value as any).end_date];
      if (contractForm.total_leave_allowed == null) {
        contractForm.total_leave_allowed = contractForm.total_lessons * 2;
      }
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

const saveContractData = async () => {
   if(!contract.value) return;
   savingContract.value = true;
   try {
     const payload: StudentContractUpdate = {
       contract_status: contractForm.contract_status,
       is_recurring: contractForm.is_recurring,
       start_date: contractForm.dateRange[0],
       end_date: contractForm.dateRange[1],
       total_lessons: contractForm.total_lessons,
       total_amount: contractForm.total_amount,
       total_leave_allowed: contractForm.total_leave_allowed,
       notes: contractForm.notes
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

// --- Contract Details API ---
const openAddDetailDialog = async () => {
  Object.assign(detailForm, {
    detail_type: 'lesson_price',
    course_id: '',
    description: '',
    amount: 0,
    notes: ''
  });
  detailVisible.value = true;
  
  if (currentStudent.value?.id) {
    try {
      const cRes = await getContractCourseOptions(currentStudent.value.id);
      detailCourseOptions.value = (cRes.data as any) || [];
    } catch(err) {
      console.error(err);
    }
  }
};

const submitDetailForm = async () => {
  if (!detailFormRef.value || !contract.value) return;
  await detailFormRef.value.validate(async valid => {
    if (valid) {
      detailLoading.value = true;
      try {
        const payload: StudentContractDetailCreate = { ...detailForm };
        if (payload.detail_type !== 'lesson_price') {
           payload.course_id = null;
        }
        await createContractDetail(contract.value!.id, payload);
        ElMessage.success('新增合約明細成功');
        detailVisible.value = false;
        fetchContractDependencies(contract.value!.id);
      } catch(err) {
        ElMessage.error('新增合約明細失敗');
      } finally {
        detailLoading.value = false;
      }
    }
  });
};

// --- Leave Records API ---
const submitLeaveForm = async () => {
  if (!leaveForm.leave_date || !contract.value) {
     ElMessage.warning('請選擇請假日期');
     return;
  }
  leaveLoading.value = true;
  try {
     await createContractLeaveRecord(contract.value.id, {
        leave_date: leaveForm.leave_date,
        reason: leaveForm.reason
     });
     ElMessage.success('請假紀錄已新增');
     leaveForm.leave_date = '';
     leaveForm.reason = '';
     // Re-fetch to update used leave counts
     await loadContent('contracts');
  } catch(err) {
     ElMessage.error('新增請假紀錄失敗');
  } finally {
     leaveLoading.value = false;
  }
};

const deleteLeave = async (recordId: string) => {
  if (!contract.value) return;
  try {
      await deleteContractLeaveRecord(contract.value.id, recordId);
      ElMessage.success('請假紀錄已刪除');
      // Re-fetch to update used leave counts
      await loadContent('contracts');
  } catch(err){
      ElMessage.error('刪除請假紀錄失敗');
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
