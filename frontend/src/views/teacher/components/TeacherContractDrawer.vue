<template>
  <el-drawer v-model="isVisible" :title="drawerTitle" size="620px" @closed="handleClosed">
    <div v-loading="loading" class="min-h-full">
      <!-- BLOCK A: Main Contract Form -->
      <el-divider content-position="left" class="mt-1 mb-8">
        <span class="text-13px color-[#1d2d44]">當前合約</span>
      </el-divider>
      <el-row class="mb-4">
        <el-col :span="8">
          <div class="flex flex-col items-start mb-4">
            <label class="mb-2 flex-shrink-0 text-xs color-[#606266]">合約編號</label>
            <div class="w-full text-xs mt-1">{{ contract?.contract_no }}</div>
          </div>
        </el-col>
        <el-col :span="12" :push="3">
          <div class="flex flex-col items-start mb-2">
            <label class="mb-2 flex-shrink-0 text-xs color-[#606266]">合約書狀態</label>
            <div class="w-full text-12px flex flex-col items-start gap-2">
              <div class="flex items-center gap-2">
                <div class="flex items-center gap-1 text-12px" :class="contractFileStatus ? 'text-green-600' : 'text-orange-500'">
                  <div :class="contractFileStatus ? 'i-hugeicons:checkmark-circle-03' : 'i-hugeicons:alert-02'" />
                  <span>{{ contractFileStatus ? '已上傳' : '未上傳' }}</span>
                </div>
                <el-upload
                  ref="uploadContractRef"
                  v-model:file-list="contractFileList"
                  class="inline-block"
                  action="#"
                  :limit="1"
                  :multiple="false"
                  accept=".pdf"
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="(f: any) => uploadContractDoc(f)"
                >
                  <el-button color="#626aef" plain round size="small" :loading="uploadingContract">
                    <template #icon><div class="i-hugeicons:file-upload" /></template>
                    {{ contractFileStatus ? '更新合約書' : '上傳合約書' }}
                  </el-button>
                </el-upload>
              </div>
              <div
                v-if="contract?.contract_file_uploaded_at"
                class="text-11px color-gray-400 mt-2"
              >
                更新時間：{{ dayjs(contract?.contract_file_uploaded_at).format('YYYY-MM-DD HH:mm:ss') }}
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
      <el-form ref="contractFormRef" size="small" :model="contractForm" :rules="contractRules" label-position="top">
        <el-row>
          <el-col :span="8">
            <el-form-item :label="$t('contract.contractStatus')" prop="status">
            <el-select v-model="contractForm.contract_status" class="w-full">
              <el-option v-for="(label, value) in CONTRACT_STATUS_MAP" :key="value" :label="label" :value="value" />
            </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12" :push="3">
            <el-form-item :label="$t('teacher.contractType')" prop="employment_type">
            <el-radio-group v-model="contractForm.employment_type">
              <el-radio value="hourly">時薪</el-radio>
              <el-radio value="full_time">全職</el-radio>
            </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="19">
            <el-form-item label="合約區間">
            <el-date-picker
                v-model="contractDates"
                type="daterange"
                range-separator="-"
                start-placeholder="起始時間"
                end-placeholder="結束時間"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                class="w-full h-30px!"
            />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="8">
            <el-form-item label="試上完成獎金">
            <el-input-number 
              v-model="contractForm.trial_completed_bonus" 
              :min="0" 
              class="w-full h-30px!" 
            />
            </el-form-item>
          </el-col>
          <el-col :span="8" :push="3">
            <el-form-item label="試上轉正獎金">
            <el-input-number 
              v-model="contractForm.trial_to_formal_bonus" 
              :min="0" 
              class="w-full h-30px!" 
            />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="24">
            <el-form-item label="備註">
              <el-input v-model="contractForm.notes" type="textarea" :rows="3" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row v-if="contractForm.employment_type === 'full_time'">
          <!-- BLOCK B: Work Schedules (Full-time only) -->
          <el-col :span="24">
            <div class="flex justify-between">
              <label class="mb-2 flex-shrink-0 text-xs color-[#606266]">正職工作時段</label>
              <el-button type="primary" round size="small" text class="text-11px" @click="copyMondayToAll">
                <template #icon><div class="i-hugeicons:copy-01" /></template>
                複製週一至平日
              </el-button>
            </div>
            
            <div class="mt-2 mb-4 px-2 py-2 bg-[#f3f4f8] rounded-md">
              <div 
                v-for="day in weekdaysInfo"
                :key="day.value" 
                class="mb-2 border-b pb-2 last:border-0 last:pb-0"
              >
                <div class="flex items-center gap-4 mb-2">
                  <span class="font-400 text-xs">{{ day.label }}</span>
                </div>
                  
                <div 
                  v-for="(sch, index) in groupedSchedules[day.value] || []" 
                  :key="index" 
                  class="inline-flex items-center px-1.5 py-1 rounded-md mb-2 mx-1 bg-[#e9eaed]"
                >
                  <el-time-picker v-model="sch.start_time" format="HH:mm" value-format="HH:mm" placeholder="Start" class="w-90px! h-25px!" />
                  <span class="text-xs px-2">~</span>
                  <el-time-picker v-model="sch.end_time" format="HH:mm" value-format="HH:mm" placeholder="End" class="w-90px! h-25px!" />
                  <el-button type="danger" size="small" round link @click="removeScheduleFromDay(day.value, index)">
                    <div class="i-hugeicons:delete-02" />
                  </el-button>
                </div>
                <el-button 
                  type="primary" 
                  round
                  text
                  size="small" 
                  @click="addScheduleToDay(day.value)"
                >
                  <template #icon>
                    <div class="i-hugeicons:plus-sign-square" />
                  </template>
                  新增時段
                </el-button>
              </div>
            </div>
          </el-col>
        </el-row>
        <el-row class="mt-2 mb-4">
          <el-col :span="12">
            <el-button type="primary" round size="small" class="py-3!" :loading="savingContract" @click="saveContractData">
              <template #icon>
                <div class="i-hugeicons:floppy-disk text-lg" />
              </template>
              儲存
            </el-button>
          </el-col>
          <el-col :span="12" justify="end">
            <el-form-item class="w-full action-column">
              <el-space :size="10" :spacer="h(ElDivider, { direction: 'vertical' })">
                <el-button
                  color="#626aef"
                  plain
                  round
                  size="small"
                  class="py-3!"
                  :loading="savingContract"
                  @click="downloadContractData"
                >
                  <template #icon>
                    <div class="i-hugeicons:file-download" />
                  </template>
                  產生合約書
                </el-button>
                <el-button
                  v-if="!addendums.length"
                  color="#f07167"
                  plain
                  round
                  size="small"
                  :loading="savingContract"
                  @click="extendContract('create')"
                >
                  <template #icon>
                    <div class="i-hugeicons:file-add" />
                  </template>
                  附約
                </el-button>
              </el-space>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <!-- BLOCK D: Addendums -->
      <template v-if="hasContract && addendums.length > 0">
        <el-divider content-position="left" class="mt-4 mb-4">
          <span class="text-13px color-[#1d2d44]">附約</span>
        </el-divider>
        <el-table :data="addendums" border size="small" class="mb-4">
          <el-table-column type="expand" width="40">
            <template #default="{ row }">
              <el-row class="px-4 py-2">
                <el-col :span="24" class="my-1"><label class="text-12px color-gray-400 font-500 mr-4">備註</label><span class="text-12px">{{ row.notes || '-' }}</span></el-col>
                <el-col :span="24" class="my-1"><label class="text-12px color-gray-400 font-500 mr-4">附約文件</label><span class="text-12px">{{ row.file_name || '-' }}</span></el-col>
                <el-col :span="24" class="my-1"><label class="text-12px color-gray-400 font-500 mr-4">上傳時間</label><span class="text-12px">{{ row.file_uploaded_at ? dayjs(row.file_uploaded_at).format('YYYY-MM-DD HH:mm') : '-' }}</span></el-col>
              </el-row>
            </template>
          </el-table-column>
          <el-table-column prop="addendum_no" label="附約編號" min-width="160" />
          <el-table-column prop="addendum_status" label="狀態" width="80" />
          <el-table-column prop="new_end_date" label="展延結束日" width="110" />
          <el-table-column label="操作" width="110" align="center">
            <template #default="{ row }">
              <el-tooltip content="編輯" effect="dark">
                <el-button link type="primary" @click="openAddendumDialog('edit', row)">
                  <div class="i-hugeicons:edit-02" />
                </el-button>
              </el-tooltip>
              <el-tooltip content="上傳附約文件" effect="dark">
                <el-upload
                  class="inline-block"
                  action="#"
                  :limit="1"
                  :multiple="false"
                  accept=".pdf"
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="(f: any) => uploadAddendum(f, row.id)"
                >
                  <el-button link type="primary">
                    <div class="i-hugeicons:upload-01" />
                  </el-button>
                </el-upload>
              </el-tooltip>
              <el-tooltip content="刪除" effect="dark">
                <el-button link type="danger" @click="handleDeleteAddendum(row.id)">
                  <div class="i-hugeicons:delete-02" />
                </el-button>
              </el-tooltip>
            </template>
          </el-table-column>
        </el-table>
      </template>

      <!-- BLOCK C: Course Rates -->
      <el-divider content-position="left" class="mt-4 mb-2">
        <span class="text-13px color-[#1d2d44]">合約明細</span>
      </el-divider>
      <div class="flex justify-end">
        <el-button type="primary" round text size="small" class="mb-2" @click="openAddRateDialog()">
          <template #icon><div class="i-hugeicons:add-square" /></template>
          新增合約明細
        </el-button>
      </div>
      <!-- List-style detail rows -->
      <div class="mb-4 flex flex-col gap-2">
        <div
          v-for="row in courseRates"
          :key="row.id"
          class="flex items-center justify-between px-3 py-2 rounded-lg border border-[#ebedf3] bg-white hover:bg-[#f8f9fb] transition-colors"
        >
          <!-- Left -->
          <div class="flex flex-col gap-0.5 min-w-0 mr-3">
            <div class="flex items-center flex-wrap gap-1.5">
              <el-tag size="small" :type="detailTypeTagType(row.detail_type)" round class="text-10px px-5px h-18px!">
                {{ DETAIL_TYPE_MAP[row.detail_type] || row.detail_type }}
              </el-tag>
              <span v-if="row.course_name" class="text-12px font-500 text-[#3f4254]">{{ row.course_name }}</span>
              <span v-if="row.description" class="text-12px" :class="{'font-500 text-[#3f4254]': !row.course_name, 'text-[#7e8299]': row.course_name}">{{ row.description }}</span>
            </div>
            <div v-if="row.notes" class="text-11px color-gray-400 mt-0.5">備註：{{ row.notes }}</div>
          </div>
          <!-- Right -->
          <div class="flex items-center gap-2 flex-shrink-0">
            <span class="text-13px font-600 text-[#3f4254] mr-6">NT$ {{ row.amount }}</span>
            <el-tooltip content="編輯" effect="dark">
              <el-button link type="primary" @click="openAddRateDialog(row)">
                <div class="i-hugeicons:edit-02" />
              </el-button>
            </el-tooltip>
            <el-tooltip content="刪除" effect="dark">
              <el-button link type="danger" @click="handleDeleteRate(row.id)">
                <div class="i-hugeicons:delete-02" />
              </el-button>
            </el-tooltip>
          </div>
        </div>
        <div v-if="!courseRates.length" class="text-center text-12px color-gray-400 py-4">尚無合約明細</div>
      </div>
    </div>
  </el-drawer>

  <!-- Add / Edit Rate Dialog -->
  <el-dialog
    v-model="showAddRateDialog"
    :title="editingRateId ? '編輯合約明細' : '新增合約明細'"
    width="440px"
    append-to-body
    destroy-on-close
    @closed="resetRateForm"
  >
    <el-form ref="rateFormRef" :model="rateForm" :rules="rateRules" label-position="top" size="small">
      <!-- 明細類型 -->
      <el-form-item label="明細類型" prop="detail_type">
        <el-select v-model="rateForm.detail_type" placeholder="請選擇明細類型" class="w-full">
          <el-option label="底薪" value="base_salary" />
          <el-option label="津貼" value="allowance" />
          <el-option label="課程時薪" value="course_rate" />
        </el-select>
      </el-form-item>
      <!-- 課程：僅 course_rate 顯示 -->
      <el-form-item v-if="rateForm.detail_type === 'course_rate'" label="課程" prop="course_id">
        <el-select v-model="rateForm.course_id" filterable clearable placeholder="請選擇課程（選填）" class="w-full">
          <el-option
            v-for="c in courseOptions"
            :key="c.id"
            :label="c.name || `${c.course_code} - ${c.course_name}`"
            :value="c.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="說明" prop="description">
        <el-input v-model="rateForm.description" placeholder="請輸入說明（選填）" />
      </el-form-item>
      <el-form-item label="金額（必填）" prop="amount">
        <el-input-number
          v-model="rateForm.amount"
          :min="0"
          :precision="0"
          class="w-full h-30px!"
        />
      </el-form-item>
      <el-form-item label="備註" prop="notes">
        <el-input v-model="rateForm.notes" placeholder="請輸入備註（選填）" />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer flex justify-end gap-2">
        <el-button round size="small" class="py-3!" @click="showAddRateDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" round size="small" class="py-3!" :loading="savingRate" @click="saveRate">
          {{ editingRateId ? $t('common.save') : '新增' }}
        </el-button>
      </div>
    </template>
  </el-dialog>

  <!-- Addendum dialog -->
  <el-dialog
    v-model="showAddendumDialog"
    :title="addendumDialogType === 'create' ? '新增附約' : '編輯附約'"
    width="380px"
    append-to-body
    destroy-on-close
    @closed="resetAddendumForm"
  >
    <div class="mb-4 rounded-md bg-[#f5f7fa] px-4 py-3 text-xs">
      <div class="flex items-center gap-4 mb-2">
        <label class="color-[#606266] font-500">合約編號</label>
        <span>{{ contract?.contract_no }}</span>
      </div>
      <div class="flex items-center gap-4">
        <label class="color-[#606266] font-500">目前結束日期</label>
        <span>{{ contractDates?.[1] || '-' }}</span>
      </div>
    </div>
    <el-form label-position="top" size="small">
      <el-form-item label="更新結束時間">
        <el-date-picker
          v-model="addendumForm.new_end_date"
          type="date"
          value-format="YYYY-MM-DD"
          class="w-full! h-30px!"
        />
      </el-form-item>
      <el-form-item label="備註">
        <el-input type="textarea" v-model="addendumForm.notes" :rows="3" placeholder="備註（選填）" />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="flex justify-end gap-2">
        <el-button round size="small" @click="showAddendumDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" round size="small" :loading="savingAddendum" @click="saveAddendum">
          <template #icon><div class="i-hugeicons:floppy-disk" /></template>
          {{ $t('common.confirm') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick, h } from 'vue';
import { dayjs, ElDivider, ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
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
  generateTeacherContractPdf,
  getTeacherContractAddendums,
  createTeacherContractAddendum,
  updateTeacherContractAddendum,
  deleteTeacherContractAddendum,
  type TeacherWorkScheduleCreate,
  type CourseOption,
  type TeacherContractDetailResponse,
  type TeacherContractCreate,
  type TeacherContractUpdate,
  type TeacherContractResponse,
  type TeacherContractAddendumResponse,
} from '@/api/teacherContract';
import { CONTRACT_STATUS_MAP } from '@/constants/contract';
import { uploadContractFile } from '@/utils/upload';
import { triggerDownload, getFileNameFromResponse } from '@/utils/download';

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
const savingContract = ref(false);
const savingSchedules = ref(false);
const teacherName = ref('');

const hasContract = ref(false);
const contractId = ref<string | null>(null);
const contractFormRef = ref<FormInstance>();
const contract = ref<TeacherContractResponse | null>(null);

const drawerTitle = computed(() => {
  return (contract.value?.teacher_name ? `${contract.value?.teacher_name}` : 'Teacher') + '合約';
});

const contractDates = ref<[string, string] | null>(null);

const contractForm = reactive({
  contract_status: 'pending' as any,
  employment_type: 'hourly' as any,
  trial_completed_bonus: 0,
  trial_to_formal_bonus: 0,
  notes: '',
});

const contractRules = reactive<FormRules>({
  contract_status: [{ required: true, message: 'Status is required' }],
  employment_type: [{ required: true, message: 'Employment type is required' }]
});

// Schedules
const weekdaysInfo = [
  { value: 0, label: '週一' },
  { value: 1, label: '週二' },
  { value: 2, label: '週三' },
  { value: 3, label: '週四' },
  { value: 4, label: '週五' },
  { value: 5, label: '週六' },
  { value: 6, label: '週日' }
];

type ScheduleSlot = { start_time: string | null; end_time: string | null; notes: string };

const groupedSchedules = ref<Record<number, ScheduleSlot[]>>({
  0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: []
});

// Detail type options
type DetailType = 'base_salary' | 'allowance' | 'course_rate';
const DETAIL_TYPE_MAP: Record<string, string> = {
  base_salary: '底薪',
  allowance: '津貼',
  course_rate: '課程時薪',
};
const detailTypeTagType = (type: string) => {
  if (type === 'base_salary') return 'primary';
  if (type === 'allowance') return 'success';
  if (type === 'course_rate') return 'warning';
  return 'info';
};

// Course Rates
const courseRates = ref<TeacherContractDetailResponse[]>([]);
const courseOptions = ref<CourseOption[]>([]);
const showAddRateDialog = ref(false);
const savingRate = ref(false);
const editingRateId = ref<string | null>(null);
const rateFormRef = ref<FormInstance>();
const rateForm = reactive({
  detail_type: 'course_rate' as DetailType,
  course_id: '' as string | null,
  amount: 0,
  description: '',
  notes: ''
});
const rateRules = reactive<FormRules>({
  detail_type: [{ required: true, message: '請選擇明細類型', trigger: 'change' }],
  amount: [
    { required: true, message: '金額為必填欄位', trigger: 'blur' },
    { type: 'number', min: 0, message: '金額不可為負數', trigger: 'change' }
  ]
});

// Addendums
const addendums = ref<TeacherContractAddendumResponse[]>([]);
const showAddendumDialog = ref(false);
const addendumDialogType = ref<'create' | 'edit'>('create');
const editingAddendumId = ref<string | null>(null);
const savingAddendum = ref(false);
const uploadingContract = ref(false);
const contractFileStatus = ref<string | null>(null); // file_uploaded_at from contract
const contractFileList = ref<any[]>([]);

const addendumForm = reactive({ new_end_date: '', notes: '' });

// --- Methods ---
const loadContracts = async () => {
  if (!props.teacherId) return;
  const cRes = await getTeacherContracts(props.teacherId);
  if (cRes.success && cRes.data.length > 0) {
    // Take the most recent contract for simplicity, or active one
    contract.value = cRes.data[0] || null;
    if (!contract.value) return;
    contractId.value = contract.value.id;
    hasContract.value = true;
    
    contractForm.contract_status = contract.value.contract_status;
    contractForm.employment_type = contract.value.employment_type || 'hourly';
    contractForm.trial_completed_bonus = contract.value.trial_completed_bonus;
    contractForm.trial_to_formal_bonus = contract.value.trial_to_formal_bonus;
    
    if (contract.value.start_date && contract.value.end_date) {
      contractDates.value = [contract.value.start_date, contract.value.end_date];
    } else {
      contractDates.value = null;
    }

    // Load Schedules
    if (contract.value.employment_type === 'full_time') {
      const sRes = await getTeacherWorkSchedules(contract.value.id);
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
    const dRes = await getTeacherContractDetails(contract.value.id);
    // Filter just to be safe, though details API might return all detail types
    courseRates.value = dRes.data || [];
    // Load Addendums
    const aRes = await getTeacherContractAddendums(contract.value.id);
    addendums.value = aRes.success ? aRes.data : [];

    // Track contract file upload status (from contract response)
    contractFileStatus.value = (contract.value as any).contract_file_uploaded_at || null;
  } else {
    hasContract.value = false;
    contractId.value = null;
    contractDates.value = null;
    contractForm.contract_status = 'pending';
    contractForm.employment_type = 'hourly';
    contractForm.trial_completed_bonus = 0;
    contractForm.trial_to_formal_bonus = 0;
    groupedSchedules.value = { 0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [] };
    courseRates.value = [];
    addendums.value = [];
    contractFileStatus.value = null;
  }

  // Clear any stale validation state that may have fired during async load
  await nextTick();
  contractFormRef.value?.clearValidate();
};

const openAddRateDialog = async (row?: TeacherContractDetailResponse) => {
  if (!hasContract.value) {
    ElMessage.warning('請先儲存合約後再新增合約明細');
    return;
  }
  if (courseOptions.value.length === 0) {
    try {
      const res = await getCourseOptions();
      courseOptions.value = res;
    } catch (e) {
      ElMessage.error('載入課程選單失敗');
    }
  }
  if (row) {
    // Edit mode: pre-fill form
    editingRateId.value = row.id;
    rateForm.detail_type = (row.detail_type as DetailType) || 'course_rate';
    rateForm.course_id = row.course_id || null;
    rateForm.amount = row.amount;
    rateForm.description = row.description || '';
    rateForm.notes = row.notes || '';
  } else {
    // Create mode
    editingRateId.value = null;
    rateForm.detail_type = 'course_rate';
    rateForm.course_id = null;
    rateForm.amount = 0;
    rateForm.description = '';
    rateForm.notes = '';
  }
  showAddRateDialog.value = true;
};

const saveContract = async () => {
  const tId = props.teacherId;
  if (!contractFormRef.value || !tId) return;
  await contractFormRef.value.validate(async (valid) => {
    if (valid) {
      savingContract.value = true;
      try {
        const payload: any = {
          contract_status: contractForm.contract_status,
          employment_type: contractForm.employment_type,
          trial_completed_bonus: contractForm.trial_completed_bonus,
          trial_to_formal_bonus: contractForm.trial_to_formal_bonus,
          start_date: contractDates.value?.[0] || null,
          end_date: contractDates.value?.[1] || null
        };
        
        const cId = contractId.value;
        if (hasContract.value && cId) {
          await updateTeacherContract(cId, payload as TeacherContractUpdate);
          await saveSchedules();
          ElMessage.success('Contract updated');
        } else {
          payload.teacher_id = tId;
          await createTeacherContract(payload as TeacherContractCreate);
          ElMessage.success('Contract created');
          await saveSchedules();
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

// Alias – must be declared after saveContract
const saveContractData = saveContract;

// Generate / download PDF
const downloadContractData = async () => {
  const cId = contractId.value;
  if (!cId) { ElMessage.warning('請先儲存合約'); return; }
  try {
    savingContract.value = true;
    const res = await generateTeacherContractPdf(cId);
    const blob = new Blob([res.data], { type: 'application/pdf' });
    const fileName = getFileNameFromResponse(res) || `teacher_contract_${cId}.pdf`;
    triggerDownload(blob, fileName);
  } catch (e) {
    console.error(e);
    ElMessage.error('產生合約書失敗');
  } finally {
    savingContract.value = false;
  }
};

// Upload contract document
const uploadContractDoc = async (uploadFile: any) => {
  const cId = contractId.value;
  if (!cId || !uploadFile.raw) return;
  uploadingContract.value = true;
  try {
    const res = await uploadContractFile('teacher', cId, null, uploadFile.raw);
    if (res && res.success) {
      ElMessage.success('合約書已上傳');
      await loadContracts();
    }
  } catch (e) {
    console.error(e);
    ElMessage.error('合約書上傳失敗');
  } finally {
    uploadingContract.value = false;
    contractFileList.value = [];
  }
};

// Addendums
const openAddendumDialog = (type: 'create' | 'edit', row?: TeacherContractAddendumResponse) => {
  addendumDialogType.value = type;
  if (type === 'edit' && row) {
    editingAddendumId.value = row.id;
    addendumForm.new_end_date = row.new_end_date || '';
    addendumForm.notes = row.notes || '';
  } else {
    editingAddendumId.value = null;
    addendumForm.new_end_date = '';
    addendumForm.notes = '';
  }
  showAddendumDialog.value = true;
};

const resetAddendumForm = () => {
  addendumForm.new_end_date = '';
  addendumForm.notes = '';
  editingAddendumId.value = null;
};

const saveAddendum = async () => {
  const cId = contractId.value;
  if (!cId) return;
  savingAddendum.value = true;
  try {
    if (addendumDialogType.value === 'create') {
      const res = await createTeacherContractAddendum(cId, addendumForm);
      if (res && res.success) ElMessage.success('新增附約成功');
    } else if (editingAddendumId.value) {
      const res = await updateTeacherContractAddendum(cId, editingAddendumId.value, addendumForm);
      if (res && res.success) ElMessage.success('更新附約成功');
    }
    showAddendumDialog.value = false;
    await loadContracts();
  } catch (e) {
    console.error(e);
    ElMessage.error(addendumDialogType.value === 'create' ? '新增附約失敗' : '更新附約失敗');
  } finally {
    savingAddendum.value = false;
  }
};

const handleDeleteAddendum = async (addendumId: string) => {
  const cId = contractId.value;
  if (!cId) return;
  try {
    await ElMessageBox.confirm('確定要刪除此附約嗎？', '刪除附約', { type: 'warning', confirmButtonText: '確定', cancelButtonText: '取消' });
    await deleteTeacherContractAddendum(cId, addendumId);
    ElMessage.success('附約已刪除');
    await loadContracts();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('刪除附約失敗');
  }
};

const uploadAddendum = async (uploadFile: any, addendumId: string) => {
  const cId = contractId.value;
  if (!cId || !uploadFile.raw) return;
  try {
    const res = await uploadContractFile('teacher', cId, addendumId, uploadFile.raw);
    if (res && res.success) {
      ElMessage.success('附約文件已上傳');
      await loadContracts();
    }
  } catch (e) {
    console.error(e);
    ElMessage.error('附約文件上傳失敗');
  }
};

// Extend contract shortcut
const extendContract = (type: 'create' | 'edit') => openAddendumDialog(type);

// Copy Monday slots (key 0) to Tuesday–Friday (keys 1–4), skip Saturday/Sunday
const copyMondayToAll = () => {
  const mondaySlots = groupedSchedules.value[0] || [];
  if (!mondaySlots.length) {
    ElMessage.warning('週一尚未設定任何時段');
    return;
  }
  // Deep clone each slot and assign to weekdays 1–4
  for (let day = 1; day <= 4; day++) {
    groupedSchedules.value[day] = mondaySlots.map(slot => ({ ...slot }));
  }
  ElMessage.success('已複製週一時段至週二～週五');
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
  editingRateId.value = null;
  rateForm.detail_type = 'course_rate';
  rateForm.course_id = null;
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
        const payload = {
          detail_type: rateForm.detail_type,
          course_id: rateForm.detail_type === 'course_rate' ? (rateForm.course_id || null) : null,
          amount: rateForm.amount,
          description: rateForm.description || null,
          notes: rateForm.notes || null
        };
        if (editingRateId.value) {
          // No update API — delete & re-create
          await deleteTeacherContractDetail(cId, editingRateId.value);
          await createTeacherContractDetail(cId, payload);
          ElMessage.success('合約明細已更新');
        } else {
          await createTeacherContractDetail(cId, payload);
          ElMessage.success('合約明細已新增');
        }
        showAddRateDialog.value = false;
        await loadContracts();
      } catch (e) {
        ElMessage.error(editingRateId.value ? '更新合約明細失敗' : '新增合約明細失敗');
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
  teacherName.value = '';
};

watch(() => props.modelValue, (val) => {
  if (val && props.teacherId) {
    loadContracts();
  }
});
</script>

<style scoped>
.h-full { height: 100%; }
.flex-col { flex-direction: column; }
:deep(.action-column) {
  .el-form-item__content {
    justify-content: end;
  }
  .el-divider--vertical {
    height: 1.5em;
    border-color: #b5b5b5;
  }
}
</style>
