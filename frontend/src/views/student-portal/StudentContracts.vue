<template>
  <div class="student-contracts pl-2 pr-4">
    <div class="flex justify-between items-center px-1 mb-3">
      <div>
        <h3 class="my-0">{{ $t('myContracts.title') }}</h3>
        <div class="text-12px text-[var(--el-text-color-secondary)] mt-1">
          {{ $t('myContracts.subtitle', { total: filteredContracts.length }) }}
        </div>
      </div>
    </div>

    <el-alert
      v-if="!currentStudentId"
      class="mb-14px"
      type="warning"
      :closable="false"
      show-icon
      :title="$t('studentBooking.missingStudentTitle')"
      :description="$t('studentBooking.missingStudentDesc')"
    />

    <el-row :gutter="14" class="mb-14px">
      <el-col :xs="12" :sm="6" :lg="6">
        <el-card shadow="never" class="summary-card">
          <div class="summary-icon is-active">
            <div class="i-hugeicons:file-verified" />
          </div>
          <div>
            <div class="summary-value">{{ activeContracts.length }}</div>
            <div class="summary-label">{{ $t('myContracts.activeCount') }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6" :lg="6">
        <el-card shadow="never" class="summary-card">
          <div class="summary-icon is-history">
            <div class="i-hugeicons:archive" />
          </div>
          <div>
            <div class="summary-value">{{ historyContracts.length }}</div>
            <div class="summary-label">{{ $t('myContracts.historyCount') }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6" :lg="6">
        <el-card shadow="never" class="summary-card">
          <div class="summary-icon is-lessons">
            <div class="i-hugeicons:book-open-02" />
          </div>
          <div>
            <div class="summary-value">{{ remainingLessonsTotal }}</div>
            <div class="summary-label">{{ $t('myContracts.remainingLessons') }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6" :lg="6">
        <el-card shadow="never" class="summary-card">
          <div class="summary-icon is-leave">
            <div class="i-hugeicons:calendar-remove-02" />
          </div>
          <div>
            <div class="summary-value">{{ usedLeaveTotal }}</div>
            <div class="summary-label">{{ $t('myContracts.usedLeaveCount') }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="filter-card mb-14px">
      <el-form
        :inline="true"
        :model="filters"
        size="small"
        label-position="top"
        class="filter-form flex items-end"
        @submit.prevent="handleSearch"
      >
        <el-form-item :label="$t('common.searchKeyword')">
          <el-input
            v-model="filters.search"
            :placeholder="$t('myContracts.searchPlaceholder')"
            clearable
            class="w-280px h-30px!"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <div class="i-hugeicons:search-01" />
            </template>
          </el-input>
        </el-form-item>

        <el-form-item :label="$t('common.status')">
          <el-select
            v-model="filters.status"
            :placeholder="$t('common.all')"
            clearable
            class="w-140px!"
            @change="handleSearch"
          >
            <el-option
              v-for="option in statusOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" round class="h-30px!" :disabled="!currentStudentId" @click="handleSearch">
            <template #icon>
              <div class="i-hugeicons:search-01" />
            </template>
            {{ $t('common.search') }}
          </el-button>
          <el-button round class="h-30px!" @click="resetFilters">
            <template #icon>
              <div class="i-hugeicons:arrow-reload-horizontal" />
            </template>
            {{ $t('common.btnReset') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-tabs v-model="activeTab" class="contract-tabs">
        <el-tab-pane :label="$t('myContracts.tabCurrent')" name="current" />
        <el-tab-pane :label="$t('myContracts.tabHistory')" name="history" />
        <el-tab-pane :label="$t('common.all')" name="all" />
      </el-tabs>

      <div
        v-if="activeTab === 'current'"
        v-loading="loading"
        class="current-contracts"
      >
        <el-empty
          v-if="!displayContracts.length"
          :description="$t('myContracts.emptyText')"
        />

        <el-row
          v-for="contract in displayContracts"
          :key="contract.id"
          :gutter="30"
          class="current-contract-row"
        >
          <el-col :xs="24" :lg="12">
            <el-descriptions
              :title="`${$t('myContracts.colContractNo')}：${contract.contract_no}`"
              :column="4"
              border
              size="small"
              class="contract-descriptions mb-20px"
            >
              <el-descriptions-item :label="$t('common.status')" :span="2">
                <div :class="`flex items-center gap-1 color-${STUDENT_CONTRACT_STATUS_TAG_MAP[contract.contract_status]}`">
                  <span class="text-lg">•</span>
                  {{ formatStudentContractStatusLabel(contract.contract_status, contract.contract_status, t) }}
                </div>
              </el-descriptions-item>
              <el-descriptions-item :label="$t('myContracts.colCourse')" :span="2">
                {{ getCourseNames(contract) }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('myContracts.colLessons')" :span="2">
                {{ contract.remaining_lessons }} / {{ contract.total_lessons }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('myContracts.colAmount')" :span="2">
                {{ formatCurrency(contract.total_amount) }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('myContracts.colLeave')" :span="2">
                {{ contract.used_leave_count || 0 }} / {{ contract.total_leave_allowed || 0 }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('common.note')" :span="4">
                {{ contract.notes || '-' }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('myContracts.colPeriod')" :span="4">
                {{ formatDate(contract.start_date) }} ~ {{ formatDate(contract.end_date) }}
              </el-descriptions-item>
              <el-descriptions-item
                :label="$t('myContracts.colFile')"
                :span="4"
              >
                <el-button
                  v-if="contract.contract_file_path"
                  type="primary"
                  link
                  size="small"
                  :loading="downloadingId === contract.id"
                  @click="downloadContract(contract.id)"
                >
                  {{ $t('myContracts.download') }}
                </el-button>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item
                v-if="contract.addendums?.length"
                :label="$t('myContracts.addendumTitle')"
                :span="4"
              >
                <div class="addendum-list">
                  <div
                    v-for="addendum in contract.addendums"
                    :key="addendum.id"
                    class="addendum-item"
                  >
                    <div class="font-mono">{{ addendum.addendum_no }}</div>
                    <div class="text-[var(--el-text-color-secondary)]">
                      {{ formatDate(addendum.original_end_date) }} 展延至 <b>{{ formatDate(addendum.new_end_date) }}</b>
                    </div>
                  </div>
                </div>
              </el-descriptions-item>
            </el-descriptions>
          </el-col>

          <el-col :xs="24" :lg="12">
            <div class="current-side-section">
              <div class="expand-title">{{ $t('myContracts.detailTitle') }}</div>
              <el-table
                :data="contract.details || []"
                size="small"
                border
                :empty-text="$t('myContracts.noDetails')"
              >
                <el-table-column :label="$t('myContracts.detailType')" width="110">
                  <template #default="{ row: detail }">
                    {{ getDetailTypeLabel(detail.detail_type) }}
                  </template>
                </el-table-column>
                <el-table-column :label="$t('myContracts.colCourse')" min-width="130">
                  <template #default="{ row: detail }">
                    {{ detail.course_name || detail.description || '-' }}
                  </template>
                </el-table-column>
                <el-table-column :label="$t('myContracts.detailAmount')" width="110" align="right">
                  <template #default="{ row: detail }">
                    {{ formatDetailAmount(detail) }}
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div class="current-side-section">
              <div class="expand-title">{{ $t('myContracts.leaveTitle') }}</div>
              <el-table
                :data="contract.leave_records || []"
                size="small"
                border
                :empty-text="$t('myContracts.noLeaveRecords')"
              >
                <el-table-column :label="$t('myContracts.leaveDate')" width="120">
                  <template #default="{ row: leave }">
                    {{ formatDate(leave.leave_date) }}
                  </template>
                </el-table-column>
                <el-table-column :label="$t('myContracts.leaveReason')" min-width="120">
                  <template #default="{ row: leave }">
                    {{ leave.reason || '-' }}
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-col>
        </el-row>
      </div>

      <el-table
        v-else
        :data="displayContracts"
        size="small"
        class="w-full"
        v-loading="loading"
        :empty-text="$t('myContracts.emptyText')"
        border
        stripe
      >
        <el-table-column prop="contract_no" :label="$t('myContracts.colContractNo')" min-width="150">
          <template #default="{ row }">
            <span class="font-mono text-12px">{{ row.contract_no }}</span>
          </template>
        </el-table-column>

        <el-table-column :label="$t('myContracts.colCourse')" min-width="170">
          <template #default="{ row }">
            {{ getCourseNames(row) }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('common.status')" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="STUDENT_CONTRACT_STATUS_TAG_MAP[row.contract_status]" size="small" effect="plain">
              {{ formatStudentContractStatusLabel(row.contract_status, row.contract_status, t) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="$t('myContracts.colPeriod')" min-width="190">
          <template #default="{ row }">
            {{ formatDate(row.start_date) }} ~ {{ formatDate(row.end_date) }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('myContracts.colLessons')" width="110" align="center">
          <template #default="{ row }">
            {{ row.remaining_lessons }} / {{ row.total_lessons }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('myContracts.colAmount')" width="100" align="right">
          <template #default="{ row }">
            {{ formatCurrency(row.total_amount) }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('myContracts.colLeave')" width="100" align="center">
          <template #default="{ row }">
            {{ row.used_leave_count || 0 }} / {{ row.total_leave_allowed || 0 }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('myContracts.colFile')" width="110" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.contract_file_path"
              type="primary"
              link
              size="small"
              :loading="downloadingId === row.id"
              @click="downloadContract(row.id)"
            >
              {{ $t('myContracts.download') }}
            </el-button>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column :label="$t('myContracts.more')" width="90" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openContractDrawer(row)">
              {{ $t('myContracts.more') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-drawer
      v-model="detailDrawerVisible"
      :title="drawerTitle"
      size="500px"
      class="contract-detail-drawer"
    >
      <template v-if="selectedContract">
        <div class="drawer-section">
          <div class="expand-title">{{ $t('myContracts.addendumTitle') }}</div>
          <el-table
            :data="selectedContract.addendums || []"
            size="small"
            border
            :empty-text="$t('myContracts.noAddendums')"
          >
            <el-table-column prop="addendum_no" :label="$t('myContracts.addendumNo')" min-width="150" />
            <el-table-column :label="$t('common.status')" width="100" align="center">
              <template #default="{ row: addendum }">
                {{ formatStudentContractStatusLabel(addendum.addendum_status, addendum.addendum_status, t) }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('myContracts.addendumPeriod')" min-width="180">
              <template #default="{ row: addendum }">
                {{ formatDate(addendum.original_end_date) }} → {{ formatDate(addendum.new_end_date) }}
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="drawer-section">
          <div class="expand-title">{{ $t('myContracts.detailTitle') }}</div>
          <el-table
            :data="selectedContract.details || []"
            size="small"
            border
            :empty-text="$t('myContracts.noDetails')"
          >
            <el-table-column :label="$t('myContracts.detailType')" width="120">
              <template #default="{ row: detail }">
                {{ getDetailTypeLabel(detail.detail_type) }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('myContracts.colCourse')" min-width="150">
              <template #default="{ row: detail }">
                {{ detail.course_name || detail.description || '-' }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('myContracts.detailAmount')" width="130" align="right">
              <template #default="{ row: detail }">
                {{ formatDetailAmount(detail) }}
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="drawer-section">
          <div class="expand-title">{{ $t('myContracts.leaveTitle') }}</div>
          <el-table
            :data="selectedContract.leave_records || []"
            size="small"
            border
            :empty-text="$t('myContracts.noLeaveRecords')"
          >
            <el-table-column :label="$t('myContracts.leaveDate')" width="130">
              <template #default="{ row: leave }">
                {{ formatDate(leave.leave_date) }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('myContracts.leaveReason')" min-width="180">
              <template #default="{ row: leave }">
                {{ leave.reason || '-' }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import dayjs from 'dayjs';
import { useAuthStore } from '@/stores/auth';
import {
  getContractDownloadUrl,
  getStudentContracts,
  type StudentContract,
  type StudentContractDetail,
  type StudentContractStatus,
} from '@/api/studentContract';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { STUDENT_CONTRACT_STATUS_TAG_MAP } from '@/constants/display';
import { CONTRACT_STATUS } from '@/constants/contract';
import {
  formatStudentContractStatusLabel,
  getStudentContractStatusOptions,
} from '@/utils/i18n-formatters';

const { t } = useI18n();
const authStore = useAuthStore();

const currentStudentId = computed(() => authStore.userInfo?.student_id || '');
const loading = ref(false);
const downloadingId = ref('');
const contracts = ref<StudentContract[]>([]);
const activeTab = ref<'current' | 'history' | 'all'>('current');
const detailDrawerVisible = ref(false);
const selectedContract = ref<StudentContract | null>(null);

const filters = reactive({
  search: '',
  status: '' as StudentContractStatus | '',
});

const statusOptions = computed(() => getStudentContractStatusOptions(t));

const activeContracts = computed(() =>
  contracts.value.filter((contract) => contract.contract_status === CONTRACT_STATUS.ACTIVE)
);

const historyContracts = computed(() =>
  contracts.value.filter((contract) => contract.contract_status !== CONTRACT_STATUS.ACTIVE)
);

const remainingLessonsTotal = computed(() =>
  activeContracts.value.reduce((total, contract) => total + (contract.remaining_lessons || 0), 0)
);

const usedLeaveTotal = computed(() =>
  activeContracts.value.reduce((total, contract) => total + (contract.used_leave_count || 0), 0)
);

const filteredContracts = computed(() => {
  const keyword = filters.search.trim().toLowerCase();

  return contracts.value.filter((contract) => {
    const matchesSearch = !keyword
      || contract.contract_no.toLowerCase().includes(keyword)
      || getCourseNames(contract).toLowerCase().includes(keyword);
    const matchesStatus = !filters.status || contract.contract_status === filters.status;
    return matchesSearch && matchesStatus;
  });
});

const displayContracts = computed(() => {
  if (activeTab.value === 'current') {
    return filteredContracts.value.filter((contract) => contract.contract_status === CONTRACT_STATUS.ACTIVE);
  }

  if (activeTab.value === 'history') {
    return filteredContracts.value.filter((contract) => contract.contract_status !== CONTRACT_STATUS.ACTIVE);
  }

  return filteredContracts.value;
});

const drawerTitle = computed(() => {
  if (!selectedContract.value) return t('myContracts.detailDrawerTitle');
  return `${t('myContracts.detailDrawerTitle')} - ${selectedContract.value.contract_no}`;
});

const formatDate = (date?: string | null) => (date ? dayjs(date).format('YYYY-MM-DD') : '-');

const formatCurrency = (amount?: number | null) => {
  if (amount === undefined || amount === null) return '-';
  return new Intl.NumberFormat('zh-TW', {
    style: 'currency',
    currency: 'TWD',
    minimumFractionDigits: 0,
  }).format(amount);
};

const getCourseNames = (contract: StudentContract) => {
  const names = contract.details
    ?.filter((detail) => detail.detail_type === 'lesson_price')
    .map((detail) => detail.course_name)
    .filter(Boolean);

  return names?.length ? [...new Set(names)].join('、') : '-';
};

const getDetailTypeLabel = (type: StudentContractDetail['detail_type']) => {
  const labelMap: Record<StudentContractDetail['detail_type'], string> = {
    lesson_price: t('myContracts.detailTypeLessonPrice'),
    discount: t('myContracts.detailTypeDiscount'),
    compensation: t('myContracts.detailTypeCompensation'),
  };

  return labelMap[type] || type;
};

const formatDetailAmount = (detail: StudentContractDetail) => {
  if (detail.amount === undefined || detail.amount === null) return '-';
  if (detail.detail_type === 'compensation') {
    return t('studentBooking.remainingLessons', { count: detail.amount });
  }
  return formatCurrency(detail.amount);
};

const fetchContracts = async () => {
  if (!currentStudentId.value) {
    contracts.value = [];
    return;
  }

  loading.value = true;
  try {
    const res = assertApiSuccess(await getStudentContracts({
      student_id: currentStudentId.value,
      page: 1,
      per_page: 100,
    }), t('myContracts.loadFailed'));

    contracts.value = res.data || [];
  } catch (error) {
    contracts.value = [];
    ElMessage.error(getApiErrorMessage(error, t('myContracts.loadFailed')));
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  // Filtering is local because students usually have a small contract set and we show current/history tabs together.
};

const resetFilters = () => {
  filters.search = '';
  filters.status = '';
};

const openContractDrawer = (contract: StudentContract) => {
  selectedContract.value = contract;
  detailDrawerVisible.value = true;
};

const downloadContract = async (contractId: string) => {
  downloadingId.value = contractId;
  try {
    const res = assertApiSuccess(await getContractDownloadUrl(contractId), t('myContracts.downloadFailed'));
    if (res.success) {
      const { download_url} = res
      const downloadUrl = download_url
      window.open(downloadUrl, '_blank');
    } else {
      ElMessage.warning(t('myContracts.noDownloadUrl'));
    }
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('myContracts.downloadFailed')));
  } finally {
    downloadingId.value = '';
  }
};

watch(
  currentStudentId,
  (studentId) => {
    if (!studentId) return;
    fetchContracts();
  },
  { immediate: true },
);
</script>

<style scoped lang="scss">
.summary-card {
  :deep(.el-card__body) {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
  }
}

.summary-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.summary-icon.is-active {
  color: var(--el-color-success);
  background: var(--el-color-success-light-9);
}

.summary-icon.is-history {
  color: var(--el-color-info);
  background: var(--el-fill-color-light);
}

.summary-icon.is-lessons {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.summary-icon.is-leave {
  color: var(--el-color-warning);
  background: var(--el-color-warning-light-9);
}

.summary-value {
  color: var(--el-text-color-primary);
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
}

.summary-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-top: 6px;
}

.contract-tabs {
  margin-top: -8px;
}

.current-contracts {
  min-height: 120px;
}

.current-contract-row {
  padding: 14px 0 18px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.current-contract-row:first-of-type {
  border-top: 0;
  padding-top: 4px;
}

.contract-descriptions {
  :deep(.el-descriptions__title) {
    color: var(--el-text-color-primary);
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
    font-size: 13px;
  }
}

.current-side-section,
.drawer-section {
  margin-bottom: 20px;
}

.expand-title {
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
}

.addendum-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.addendum-item {
  display: flex;
  flex-direction: column;
  line-height: 1.5;
  padding: 4px 0;
}

.contract-detail-drawer {
  :deep(.el-drawer__body) {
    padding-top: 8px;
  }
}
</style>
