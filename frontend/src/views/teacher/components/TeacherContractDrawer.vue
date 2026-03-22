<template>
  <el-drawer v-model="isVisible" :title="drawerTitle" size="800px" @closed="handleClosed">
    <div v-loading="loading" class="h-full">
      <!-- BLOCK A: Main Contract Form -->
      <el-card shadow="never" class="mb-4">
      <template #header>
        <div class="flex justify-between items-center">
        <span>{{ $t('salary.contract') }}</span>
        <el-button type="primary" size="small" :loading="savingContract" @click="saveContract">{{ $t('common.save') }}</el-button>
        </div>
      </template>
      <el-form ref="contractFormRef" :model="contractForm" :rules="contractRules" label-position="top">
        <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item :label="$t('common.status')" prop="status">
          <el-select v-model="contractForm.status" class="w-full">
            <el-option label="Pending" value="pending" />
            <el-option label="Active" value="active" />
            <el-option label="Expired" value="expired" />
            <el-option label="Terminated" value="terminated" />
          </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item :label="$t('teacher.contractType')" prop="employment_type">
          <el-radio-group v-model="contractForm.employment_type">
            <el-radio value="hourly">Hourly (Part-time)</el-radio>
            <el-radio value="full_time">Full-time</el-radio>
          </el-radio-group>
          </el-form-item>
        </el-col>
        </el-row>
        <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="Contract Dates">
          <el-date-picker
              v-model="contractDates"
              type="daterange"
              range-separator="-"
              start-placeholder="Start Date"
              end-placeholder="End Date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              class="w-full"
          />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="Trial Completed Bonus">
          <el-input-number v-model="contractForm.trial_completed_bonus" :min="0" class="w-full" controls-position="right" />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="Trial To Formal Bonus">
          <el-input-number v-model="contractForm.trial_to_formal_bonus" :min="0" class="w-full" controls-position="right" />
          </el-form-item>
        </el-col>
        </el-row>
      </el-form>
      </el-card>

      <!-- BLOCK B: Work Schedules (Full-time only) -->
      <el-card shadow="never" class="mb-4" v-if="hasContract && contractForm.employment_type === 'full_time'">
      <template #header>
          <div class="flex justify-between items-center">
          <span>正職排班/工作時段 (Working Schedules)</span>
          <el-button type="success" size="small" :loading="savingSchedules" @click="saveSchedules">{{ $t('common.save') }} 排班</el-button>
          </div>
      </template>
      
      <div v-for="day in weekdaysInfo" :key="day.value" class="mb-4 border-b pb-4 last:border-0 last:pb-0">
          <div class="flex items-center gap-4 mb-2">
          <span class="font-bold w-32">{{ day.label }}</span>
          <el-button type="primary" plain size="small" icon="Plus" @click="addScheduleToDay(day.value)">
              新增時段 (Add)
          </el-button>
          </div>
          
          <div v-for="(sch, index) in groupedSchedules[day.value] || []" :key="index" class="flex gap-2 items-center mb-2 pl-4">
          <el-time-picker v-model="sch.start_time" format="HH:mm" value-format="HH:mm" placeholder="Start" class="w-28" />
          <span>-</span>
          <el-time-picker v-model="sch.end_time" format="HH:mm" value-format="HH:mm" placeholder="End" class="w-28" />
          <el-input v-model="sch.notes" placeholder="Notes (optional)" class="flex-1" />
          <el-button type="danger" plain icon="Delete" @click="removeScheduleFromDay(day.value, index)" />
          </div>
          
          <div v-if="!groupedSchedules[day.value]?.length" class="text-gray-400 text-sm pl-4 italic">
          無安排時段 (No slots scheduled)
          </div>
      </div>
      </el-card>

      <!-- BLOCK C: Course Rates -->
      <el-card shadow="never" v-if="hasContract">
      <template #header>
        <div class="flex justify-between items-center">
        <span>Course Rates</span>
        <el-button type="primary" size="small" @click="showAddRateDialog = true">Add Rate</el-button>
        </div>
      </template>
      <el-table :data="courseRates" border stripe size="small">
        <el-table-column label="Course" min-width="150">
        <template #default="{ row }">
            {{ getCourseName(row.course_id) }}
        </template>
        </el-table-column>
        <el-table-column prop="description" label="Description" min-width="120" />
        <el-table-column prop="amount" label="Hourly Rate" width="120" align="right" />
        <el-table-column prop="notes" label="Notes" min-width="100" />
        <el-table-column label="Actions" width="80" align="center">
        <template #default="{ row }">
          <el-button link type="danger" @click="handleDeleteRate(row.id)">
          <div class="i-hugeicons:delete-02" />
          </el-button>
        </template>
        </el-table-column>
      </el-table>
      </el-card>
    </div>
  </el-drawer>

  <!-- Add Rate Dialog -->
  <el-dialog v-model="showAddRateDialog" title="Add Course Rate" width="500px" append-to-body @closed="resetRateForm">
    <el-form ref="rateFormRef" :model="rateForm" :rules="rateRules" label-width="100px">
      <el-form-item label="Course" prop="course_id">
        <el-select v-model="rateForm.course_id" filterable class="w-full">
          <el-option v-for="c in courseOptions" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="Amount" prop="amount">
        <el-input-number v-model="rateForm.amount" :min="0" class="w-full" controls-position="right" />
      </el-form-item>
      <el-form-item label="Description" prop="description">
        <el-input v-model="rateForm.description" />
      </el-form-item>
      <el-form-item label="Notes" prop="notes">
        <el-input v-model="rateForm.notes" />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="showAddRateDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="savingRate" @click="saveRate">Add</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { getTeacherList, updateTeacher, type TeacherUpdate } from '@/api/teacher';
import { 
  getTeacherContracts, 
  createTeacherContract, 
  updateTeacherContract,
  getTeacherWorkSchedules,
  batchSetTeacherWorkSchedules,
  getTeacherContractDetails,
  createTeacherContractDetail,
  deleteTeacherContractDetail,
  getCourseOptions,
  type TeacherWorkScheduleCreate,
  type CourseOption,
  type TeacherContractDetailResponse,
  type TeacherContractCreate,
  type TeacherContractUpdate
} from '@/api/teacherContract';

const props = defineProps<{
  modelValue: boolean;
  teacherId: string | null;
}>();

const emit = defineEmits(['update:modelValue', 'saved']);

const isVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

// UI State
const loading = ref(false);
const saving = ref(false);
const savingContract = ref(false);
const savingSchedules = ref(false);
const activeTab = ref('basic');
const teacherName = ref('');

const drawerTitle = computed(() => {
  return teacherName.value ? `${teacherName.value}` : 'Teacher Details';
});

// --- Tab 1: Basic Info ---
const basicFormRef = ref<FormInstance>();
const basicForm = reactive<TeacherUpdate>({
  name: '',
  email: '',
  phone: '',
  address: '',
  bio: '',
  teacher_level: 1
});

const basicRules = reactive<FormRules>({
  name: [{ required: true, message: 'Name is required', trigger: 'blur' }],
  email: [{ required: true, message: 'Email is required', trigger: 'blur', type: 'email' }]
});

// --- Tab 2: Contracts ---
const hasContract = ref(false);
const contractId = ref<string | null>(null);
const contractFormRef = ref<FormInstance>();

const contractDates = ref<[string, string] | null>(null);

const contractForm = reactive({
  status: 'pending' as any,
  employment_type: 'hourly' as any,
  trial_completed_bonus: 0,
  trial_to_formal_bonus: 0
});

const contractRules = reactive<FormRules>({
  status: [{ required: true, message: 'Status is required' }],
  employment_type: [{ required: true, message: 'Employment type is required' }]
});

// Schedules
const weekdaysInfo = [
  { value: 0, label: '星期一 (Mon)' },
  { value: 1, label: '星期二 (Tue)' },
  { value: 2, label: '星期三 (Wed)' },
  { value: 3, label: '星期四 (Thu)' },
  { value: 4, label: '星期五 (Fri)' },
  { value: 5, label: '星期六 (Sat)' },
  { value: 6, label: '星期日 (Sun)' }
];

type ScheduleSlot = { start_time: string | null; end_time: string | null; notes: string };

const groupedSchedules = ref<Record<number, ScheduleSlot[]>>({
  0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: []
});

// Course Rates
const courseRates = ref<TeacherContractDetailResponse[]>([]);
const courseOptions = ref<CourseOption[]>([]);
const showAddRateDialog = ref(false);
const savingRate = ref(false);
const rateFormRef = ref<FormInstance>();
const rateForm = reactive({
  course_id: '',
  amount: 0,
  description: '',
  notes: ''
});
const rateRules = reactive<FormRules>({
  course_id: [{ required: true, message: 'Course is required' }],
  amount: [{ required: true, message: 'Amount is required' }]
});

// --- Methods ---

const fetchData = async () => {
  if (!props.teacherId) return;
  loading.value = true;
  try {
    // 1. Fetch Teacher Basic Info
    // Since we don't have a GET /teachers/{id} strictly defined in the snippet, we fetch from list.
    // In a real scenario there might be a getTeacher(id).
    // Assuming backend returns it in the list endpoint.
    const res = await getTeacherList({ search: props.teacherId }); // pseudo fetch. Or pass full teacher object from parent
    const target = res.data.find(t => t.id === props.teacherId);
    if (target) {
      teacherName.value = target.name;
      basicForm.name = target.name;
      basicForm.email = target.email;
      basicForm.phone = target.phone || '';
      basicForm.address = target.address || '';
      basicForm.bio = target.bio || '';
      basicForm.teacher_level = target.teacher_level;
    }

    // 2. Fetch Options
    if (courseOptions.value.length === 0) {
      const optRes = await getCourseOptions();
      if (optRes.success) courseOptions.value = optRes.data;
    }

    // 3. Fetch Contracts
    await loadContracts();

  } catch (error) {
    ElMessage.error('Failed to load teacher data');
  } finally {
    loading.value = false;
  }
};

const loadContracts = async () => {
  if (!props.teacherId) return;
  const cRes = await getTeacherContracts(props.teacherId);
  if (cRes.success && cRes.data.length > 0) {
    // Take the most recent contract for simplicity, or active one
    const contract = cRes.data[0];
    if (!contract) return;
    contractId.value = contract.id;
    hasContract.value = true;
    
    contractForm.status = contract.status;
    contractForm.employment_type = contract.employment_type || 'hourly';
    contractForm.trial_completed_bonus = contract.trial_completed_bonus;
    contractForm.trial_to_formal_bonus = contract.trial_to_formal_bonus;
    
    if (contract.start_date && contract.end_date) {
      contractDates.value = [contract.start_date, contract.end_date];
    } else {
      contractDates.value = null;
    }

    // Load Schedules
    if (contract.employment_type === 'full_time') {
      const sRes = await getTeacherWorkSchedules(contract.id);
      groupedSchedules.value = { 0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [] };
      if (sRes.success) {
        sRes.data.forEach(s => {
          let arr = groupedSchedules.value[s.weekday];
          if (!arr) {
            arr = [];
            groupedSchedules.value[s.weekday] = arr;
          }
          arr.push({
            start_time: s.start_time,
            end_time: s.end_time,
            notes: s.notes || ''
          });
        });
      }
    } else {
      groupedSchedules.value = { 0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [] };
    }

    // Load Course Rates
    const dRes = await getTeacherContractDetails(contract.id);
    if (dRes.success) {
      // Filter just to be safe, though details API might return all detail types
      courseRates.value = dRes.data.filter(d => d.detail_type === 'course_rate');
    }
  } else {
    hasContract.value = false;
    contractId.value = null;
    contractDates.value = null;
    contractForm.status = 'pending';
    contractForm.employment_type = 'hourly';
    contractForm.trial_completed_bonus = 0;
    contractForm.trial_to_formal_bonus = 0;
    groupedSchedules.value = { 0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [] };
    courseRates.value = [];
  }
};

const saveBasicInfo = async () => {
  const tId = props.teacherId;
  if (!basicFormRef.value || !tId) return;
  await basicFormRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true;
      try {
        await updateTeacher(tId, basicForm);
        ElMessage.success('Basic info updated successfully');
        teacherName.value = basicForm.name || teacherName.value;
        emit('saved');
      } catch (e) {
        ElMessage.error('Failed to update basic info');
      } finally {
        saving.value = false;
      }
    }
  });
};

const saveContract = async () => {
  const tId = props.teacherId;
  if (!contractFormRef.value || !tId) return;
  await contractFormRef.value.validate(async (valid) => {
    if (valid) {
      savingContract.value = true;
      try {
        const payload: any = {
          status: contractForm.status,
          employment_type: contractForm.employment_type,
          trial_completed_bonus: contractForm.trial_completed_bonus,
          trial_to_formal_bonus: contractForm.trial_to_formal_bonus,
          start_date: contractDates.value?.[0] || null,
          end_date: contractDates.value?.[1] || null
        };
        
        const cId = contractId.value;
        if (hasContract.value && cId) {
          await updateTeacherContract(cId, payload as TeacherContractUpdate);
          ElMessage.success('Contract updated');
        } else {
          payload.teacher_id = tId;
          await createTeacherContract(payload as TeacherContractCreate);
          ElMessage.success('Contract created');
          await loadContracts(); // Reload to get contract ID
        }
      } catch (e) {
        ElMessage.error('Failed to save contract');
      } finally {
        savingContract.value = false;
      }
    }
  });
};

const addScheduleToDay = (weekday: number) => {
  if (!groupedSchedules.value[weekday]) groupedSchedules.value[weekday] = [];
  groupedSchedules.value[weekday].push({
    start_time: '09:00',
    end_time: '18:00',
    notes: ''
  });
};

const removeScheduleFromDay = (weekday: number, idx: number) => {
  if (groupedSchedules.value[weekday]) {
    groupedSchedules.value[weekday].splice(idx, 1);
  }
};

const saveSchedules = async () => {
  const cId = contractId.value;
  if (!cId) return;
  savingSchedules.value = true;
  try {
    const flattenedSchedules: TeacherWorkScheduleCreate[] = [];
    Object.keys(groupedSchedules.value).forEach(keyStr => {
      const weekday = parseInt(keyStr);
      const arr = groupedSchedules.value[weekday];
      if (arr) {
        arr.forEach(slot => {
          if (slot.start_time && slot.end_time) {
            flattenedSchedules.push({
              weekday,
              start_time: slot.start_time,
              end_time: slot.end_time,
              notes: slot.notes || null
            });
          }
        });
      }
    });

    await batchSetTeacherWorkSchedules(cId, { schedules: flattenedSchedules });
    ElMessage.success('Schedules updated');
  } catch (e) {
    ElMessage.error('Failed to update schedules');
  } finally {
    savingSchedules.value = false;
  }
};

const resetRateForm = () => {
  if (rateFormRef.value) rateFormRef.value.resetFields();
  rateForm.course_id = '';
  rateForm.amount = 0;
  rateForm.description = '';
  rateForm.notes = '';
};

const saveRate = async () => {
  const cId = contractId.value;
  if (!rateFormRef.value || !cId) return;
  await rateFormRef.value.validate(async (valid) => {
    if (valid) {
      savingRate.value = true;
      try {
        await createTeacherContractDetail(cId, {
          detail_type: 'course_rate',
          course_id: rateForm.course_id,
          amount: rateForm.amount,
          description: rateForm.description,
          notes: rateForm.notes
        });
        ElMessage.success('Course rate added');
        showAddRateDialog.value = false;
        await loadContracts(); // Reload rates
      } catch (e) {
        ElMessage.error('Failed to add rate');
      } finally {
        savingRate.value = false;
      }
    }
  });
};

const handleDeleteRate = async (detailId: string) => {
  const cId = contractId.value;
  if (!cId) return;
  try {
    await ElMessageBox.confirm('Are you sure you want to delete this course rate?', 'Warning', { type: 'warning' });
    await deleteTeacherContractDetail(cId, detailId);
    ElMessage.success('Rate deleted');
    await loadContracts(); // Reload rates
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('Failed to delete rate');
  }
};

const getCourseName = (id: string | null | undefined) => {
  if (!id) return '-';
  const c = courseOptions.value.find(o => o.id === id);
  return c ? c.name : id;
};

const handleClosed = () => {
  activeTab.value = 'basic';
  teacherName.value = '';
};

watch(() => props.modelValue, (val) => {
  if (val && props.teacherId) {
    fetchData();
  }
});
</script>

<style scoped>
.h-full { height: 100%; }
.flex-col { flex-direction: column; }
</style>
