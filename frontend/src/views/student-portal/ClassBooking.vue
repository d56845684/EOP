<template>
  <div class="class-booking pl-2 pr-4">
    <div class="flex justify-between items-center px-1 mb-2">
      <div>
        <h3 class="my-0">{{ $t('studentBooking.title') }}</h3>
      </div>
      <el-button
        type="primary"
        size="small"
        round
        class="h-30px! px-2"
        :disabled="!currentStudentId"
        @click="openBookingDialog"
      >
        <template #icon>
          <div class="i-hugeicons:plus-sign-square" />
        </template>
        {{ $t('studentBooking.bookingFormTitle') }}
      </el-button>
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
            :placeholder="$t('studentBooking.searchPlaceholder')"
            clearable
            class="w-220px h-30px!"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <div class="i-hugeicons:search-01" />
            </template>
          </el-input>
        </el-form-item>

        <el-form-item :label="$t('common.dateRange')">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="~"
            :start-placeholder="$t('common.startDate')"
            :end-placeholder="$t('common.endDate')"
            class="w-240px! h-30px!"
            clearable
            value-format="YYYY-MM-DD"
            @change="handleSearch"
          />
        </el-form-item>

        <el-form-item :label="$t('common.status')">
          <el-select
            v-model="filters.status"
            :placeholder="$t('common.all')"
            clearable
            class="w-120px!"
            @change="handleSearch"
          >
            <el-option
              v-for="(label, value) in BOOKING_STATUS_MAP"
              :key="value"
              :label="label"
              :value="value"
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
      <el-table
        :data="bookings"
        size="small"
        class="w-full"
        v-loading="loading"
        :empty-text="$t('studentBooking.emptyText')"
        stripe
      >
        <el-table-column prop="booking_no" :label="$t('studentBooking.colBookingNo')" width="150" />

        <el-table-column :label="$t('studentBooking.colDate')" width="150" align="center">
          <template #default="{ row }">
            <div>{{ row.booking_date || '-' }}</div>
            <div class="text-12px text-[var(--el-text-color-secondary)]">
              {{ formatTime(row.start_time) }} ~ {{ formatTime(row.end_time) }}
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('studentBooking.colCourse')" min-width="180">
          <template #default="{ row }">
            {{ row.course_name || '-' }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('studentBooking.colTeacher')" min-width="160">
          <template #default="{ row }">
            {{ row.substitute_teacher_name || row.teacher_name || '-' }}
            <el-tag v-if="row.substitute_teacher_name" class="ml-1" size="small" type="warning" effect="plain">
              代課
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="$t('studentBooking.colContract')" min-width="140">
          <template #default="{ row }">
            {{ row.student_contract_no || '-' }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('studentBooking.colStatus')" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.booking_status)" size="small" effect="plain">
              {{ BOOKING_STATUS_MAP[row.booking_status] || row.booking_status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="$t('common.type')" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.booking_type === 'trial' ? 'warning' : ''" size="small" effect="plain">
              {{ BOOKING_TYPE_MAP[row.booking_type] || row.booking_type || '-' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="$t('studentBooking.colZoom')" width="120" align="center">
          <template #default="{ row }">
            <el-link
              v-if="zoomInfoMap[row.id]?.join_url"
              :href="zoomInfoMap[row.id]?.join_url"
              target="_blank"
              type="primary"
            >
              {{ $t('studentBooking.zoomEnter') }}
            </el-link>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column :label="$t('teacherRecords.colActions')" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.has_pending_leave" size="small" type="warning" effect="plain">
              {{ $t('studentBooking.leavePending') }}
            </el-tag>
            <el-button
              v-else-if="row.booking_status === 'confirmed'"
              type="danger"
              link
              size="small"
              :disabled="!canRequestLeave(row)"
              @click="openLeaveDialog(row)"
            >
              {{ $t('studentBooking.btnCancel') }}
            </el-button>
            <span v-else class="text-12px text-[var(--el-text-color-secondary)]">
              {{ getActionHint(row) }}
            </span>
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
          @size-change="fetchBookings"
          @current-change="fetchBookings"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="bookingDialogVisible"
      :title="$t('studentBooking.bookingFormTitle')"
      width="480px"
      @closed="resetBookingForm"
    >
      <!-- <div class="student-info-grid mb-4">
        <div>
          <div class="info-label">{{ $t('studentBooking.currentStudent') }}</div>
          <div class="info-value">{{ currentStudentName }}</div>
        </div>
        <div>
          <div class="info-label">{{ $t('studentBooking.email') }}</div>
          <div class="info-value">{{ currentStudentEmail }}</div>
        </div>
        <div>
          <div class="info-label">{{ $t('studentBooking.studentId') }}</div>
          <div class="info-value is-mono">{{ currentStudentId || '-' }}</div>
        </div>
      </div> -->

      <el-form
        ref="bookingFormRef"
        :model="bookingForm"
        :rules="bookingRules"
        size="small"
        label-position="top"
        v-loading="creating"
      >
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item :label="$t('studentBooking.labelTeacher')" prop="teacher_id">
              <el-select
                v-model="bookingForm.teacher_id"
                filterable
                clearable
                class="w-full h-30px!"
                :disabled="!currentStudentId"
                :loading="optionsLoading"
                :placeholder="$t('studentBooking.teacherPlaceholder')"
                @change="handleTeacherChange"
              >
                <el-option
                  v-for="teacher in teacherOptions"
                  :key="teacher.id"
                  :label="teacher.name"
                  :value="teacher.id"
                />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item :label="$t('studentBooking.labelCourse')" prop="course_id">
              <el-select
                v-model="bookingForm.course_id"
                filterable
                clearable
                class="w-full h-30px!"
                :disabled="!bookingForm.teacher_id"
                :loading="coursesLoading"
                :placeholder="$t('studentBooking.coursePlaceholder')"
                @change="handleCourseChange"
              >
                <el-option
                  v-for="course in courseOptions"
                  :key="course.id"
                  :label="getCourseLabel(course)"
                  :value="course.id"
                />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item :label="$t('studentBooking.labelContract')">
              <el-select
                v-model="bookingForm.student_contract_id"
                filterable
                clearable
                class="w-full h-30px!"
                :disabled="!bookingForm.course_id || contractsLoading || studentContractOptions.length === 0"
                :loading="contractsLoading"
                :placeholder="contractPlaceholder"
              >
                <el-option
                  v-for="contract in studentContractOptions"
                  :key="contract.id"
                  :label="getContractLabel(contract)"
                  :value="contract.id"
                />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item :label="$t('studentBooking.labelSlot')" prop="teacher_slot_id">
              <el-select
                v-model="bookingForm.teacher_slot_id"
                filterable
                clearable
                class="w-full h-30px!"
                :disabled="!bookingForm.teacher_id"
                :loading="slotsLoading"
                :placeholder="$t('studentBooking.slotPlaceholder')"
              >
                <el-option
                  v-for="slot in teacherSlotOptions"
                  :key="slot.id"
                  :label="getSlotLabel(slot)"
                  :value="slot.id"
                  :disabled="slot.is_booked || isPastSlot(slot)"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item :label="$t('studentBooking.labelNotes')">
          <el-input
            v-model="bookingForm.notes"
            type="textarea"
            :rows="4"
            :placeholder="$t('studentBooking.notesPlaceholder')"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button round size="small" class="h-30px! px-5!" @click="bookingDialogVisible = false">
            <template #icon>
              <div class="i-hugeicons:cancel-circle-half-dot" />
            </template>
            {{ $t('common.cancel') }}
          </el-button>
          <el-button
            type="primary"
            round
            size="small"
            class="h-30px! px-5!"
            :loading="creating"
            :disabled="!currentStudentId"
            @click="submitBooking"
          >
            <template #icon>
              <div class="i-hugeicons:calendar-check-out-02" />
            </template>
            {{ $t('studentBooking.btnBook') }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="leaveDialogVisible"
      :title="$t('studentBooking.dialogLeaveTitle')"
      width="420px"
      @closed="resetLeaveForm"
    >
      <div v-if="leaveBooking" class="mb-4 rounded-3 bg-[var(--el-fill-color-light)] px-4 py-3">
        <div class="font-600">{{ leaveBooking.course_name || '-' }}</div>
        <div class="text-12px text-[var(--el-text-color-secondary)] mt-1">
          {{ leaveBooking.booking_date }} {{ formatTime(leaveBooking.start_time) }} ~ {{ formatTime(leaveBooking.end_time) }}
        </div>
        <el-alert
          v-if="isEmergencyLeave(leaveBooking)"
          class="mt-3"
          type="warning"
          :closable="false"
          show-icon
          :title="$t('studentBooking.confirmLateCancel')"
        />
      </div>

      <el-form
        ref="leaveFormRef"
        :model="leaveForm"
        :rules="leaveRules"
        size="small"
        label-position="top"
        v-loading="leaving"
      >
        <el-form-item :label="$t('studentBooking.labelLeaveReason')" prop="reason">
          <el-input
            v-model="leaveForm.reason"
            type="textarea"
            :rows="4"
            :placeholder="$t('studentBooking.leaveReasonPlaceholder')"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button round size="small" class="h-30px! px-5!" @click="leaveDialogVisible = false">
            {{ $t('common.cancel') }}
          </el-button>
          <el-button
            round
            size="small"
            class="h-30px! px-5!"
            type="primary"
            :loading="leaving"
            @click="submitLeave"
          >
            {{ $t('common.confirm') }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import dayjs from 'dayjs';
import { useAuthStore } from '@/stores/auth';
import {
  createBooking,
  getBookingList,
  getBookingOptionOverlappingCourses,
  getBookingOptionStudentContracts,
  getBookingOptionTeacherSlots,
  getBookingOptionTeachers,
  type BookingCourseOption,
  type BookingItem,
  type BookingStatus,
  type BookingStudentContractOption,
  type BookingTeacherOption,
  type BookingTeacherSlotOption,
} from '@/api/booking';
import { createLeaveRecord } from '@/api/leaveRecord';
import { batchGetZoomMeetings, type ZoomMeetingLogResponse } from '@/api/zoom';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { BOOKING_STATUS_MAP, BOOKING_TYPE_MAP } from '@/constants/booking';

const { t } = useI18n();
const authStore = useAuthStore();

const currentStudentId = computed(() => authStore.userInfo?.student_id || '');

const teacherOptions = ref<BookingTeacherOption[]>([]);
const courseOptions = ref<BookingCourseOption[]>([]);
const studentContractOptions = ref<BookingStudentContractOption[]>([]);
const teacherSlotOptions = ref<BookingTeacherSlotOption[]>([]);
const optionsLoading = ref(false);
const coursesLoading = ref(false);
const contractsLoading = ref(false);
const slotsLoading = ref(false);
const creating = ref(false);
const bookingDialogVisible = ref(false);

const bookingFormRef = ref<FormInstance>();
const bookingForm = reactive({
  teacher_id: '',
  course_id: '',
  student_contract_id: '',
  teacher_slot_id: '',
  notes: '',
});

const bookingRules = reactive<FormRules>({
  teacher_id: [{ required: true, message: t('studentBooking.teacherRequired'), trigger: 'change' }],
  course_id: [{ required: true, message: t('studentBooking.courseRequired'), trigger: 'change' }],
  teacher_slot_id: [{ required: true, message: t('studentBooking.slotRequired'), trigger: 'change' }],
});

const contractPlaceholder = computed(() => {
  if (contractsLoading.value) return t('studentBooking.contractLoading');
  return studentContractOptions.value.length
    ? t('studentBooking.contractPlaceholder')
    : t('studentBooking.noContractOption');
});

const selectedSlot = computed(() =>
  teacherSlotOptions.value.find((slot) => slot.id === bookingForm.teacher_slot_id)
);

const filters = reactive({
  search: '',
  dateRange: [] as [string, string] | [],
  status: '' as BookingStatus | '',
});

const queryParams = reactive({
  page: 1,
  per_page: 10,
});

const bookings = ref<BookingItem[]>([]);
const loading = ref(false);
const total = ref(0);
const zoomInfoMap = ref<Record<string, ZoomMeetingLogResponse>>({});

const leaveDialogVisible = ref(false);
const leaveBooking = ref<BookingItem | null>(null);
const leaving = ref(false);
const leaveFormRef = ref<FormInstance>();
const leaveForm = reactive({
  reason: '',
});
const leaveRules = reactive<FormRules>({
  reason: [{ required: true, message: t('studentBooking.leaveReasonRequired'), trigger: 'blur' }],
});

const toTimeText = (time?: string | null) => (time ? time.substring(0, 5) : '');
const formatTime = toTimeText;

const getCourseLabel = (course: BookingCourseOption) => {
  return course.course_code ? `${course.course_code} - ${course.course_name}` : course.course_name;
};

const getContractLabel = (contract: BookingStudentContractOption) => {
  const courseName = contract.course_name ? ` / ${contract.course_name}` : '';
  return `${contract.contract_no}${courseName} / ${t('studentBooking.remainingLessons', { count: contract.remaining_lessons })}`;
};

const getSlotLabel = (slot: BookingTeacherSlotOption) => {
  const status = slot.is_booked ? ` (${t('studentBooking.slotBooked')})` : '';
  return `${slot.slot_date} ${toTimeText(slot.start_time)} ~ ${toTimeText(slot.end_time)}${status}`;
};

const isPastSlot = (slot: BookingTeacherSlotOption) => {
  return dayjs(`${slot.slot_date} ${toTimeText(slot.end_time)}`).isBefore(dayjs());
};

const getStatusType = (status: BookingStatus) => {
  switch (status) {
    case 'completed':
      return 'success';
    case 'cancelled':
      return 'info';
    case 'confirmed':
      return 'primary';
    case 'pending':
      return 'warning';
    default:
      return '';
  }
};

const getBookingStart = (booking: BookingItem) => {
  return dayjs(`${booking.booking_date} ${toTimeText(booking.start_time)}`);
};

const canRequestLeave = (booking: BookingItem) => {
  return getBookingStart(booking).diff(dayjs(), 'minute') >= 30;
};

const isEmergencyLeave = (booking: BookingItem) => {
  const diffHours = getBookingStart(booking).diff(dayjs(), 'hour', true);
  return diffHours >= 0.5 && diffHours < 24;
};

const getActionHint = (booking: BookingItem) => {
  if (booking.booking_status === 'pending') return t('studentBooking.pendingTeacherConfirm');
  if (booking.booking_status === 'completed') return t('studentBooking.completed');
  if (booking.booking_status === 'cancelled') return t('studentBooking.cancelled');
  return '-';
};

const loadTeacherOptions = async () => {
  if (!currentStudentId.value) return;

  optionsLoading.value = true;
  try {
    const teachersRes = await getBookingOptionTeachers({ student_id: currentStudentId.value });
    teacherOptions.value = assertApiSuccess(teachersRes, t('studentBooking.loadOptionsFailed')).data || [];
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('studentBooking.loadOptionsFailed')));
  } finally {
    optionsLoading.value = false;
  }
};

const loadStudentContracts = async () => {
  if (!currentStudentId.value) {
    studentContractOptions.value = [];
    return [];
  }

  contractsLoading.value = true;
  try {
    const contractsRes = await getBookingOptionStudentContracts(currentStudentId.value);
    const contracts = assertApiSuccess(contractsRes, t('studentBooking.loadContractsFailed')).data || [];
    studentContractOptions.value = contracts;
    return contracts;
  } catch (error) {
    studentContractOptions.value = [];
    ElMessage.error(getApiErrorMessage(error, t('studentBooking.loadContractsFailed')));
    return [];
  } finally {
    contractsLoading.value = false;
  }
};

const loadStudentOptions = async () => {
  await Promise.all([
    loadTeacherOptions(),
    loadStudentContracts(),
  ]);
};

const loadCoursesAndSlots = async () => {
  if (!currentStudentId.value || !bookingForm.teacher_id) return;

  coursesLoading.value = true;
  slotsLoading.value = true;
  try {
    const [coursesRes, slotsRes] = await Promise.all([
      getBookingOptionOverlappingCourses({
        student_id: currentStudentId.value,
        teacher_id: bookingForm.teacher_id,
      }),
      getBookingOptionTeacherSlots(bookingForm.teacher_id, {
        date_from: dayjs().format('YYYY-MM-DD'),
        date_to: dayjs().add(30, 'day').format('YYYY-MM-DD'),
      }),
    ]);

    courseOptions.value = assertApiSuccess(coursesRes, t('studentBooking.loadCoursesFailed')).data || [];
    teacherSlotOptions.value = (assertApiSuccess(slotsRes, t('studentBooking.loadSlotsFailed')).data || [])
      .filter((slot) => !isPastSlot(slot));
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('studentBooking.loadOptionsFailed')));
  } finally {
    coursesLoading.value = false;
    slotsLoading.value = false;
  }
};

const handleTeacherChange = () => {
  bookingForm.course_id = '';
  bookingForm.student_contract_id = '';
  bookingForm.teacher_slot_id = '';
  courseOptions.value = [];
  teacherSlotOptions.value = [];
  bookingFormRef.value?.clearValidate(['course_id', 'teacher_slot_id']);
  loadCoursesAndSlots();
};

const handleCourseChange = () => {
  bookingForm.student_contract_id = '';
  if (!bookingForm.course_id) return;

  const firstContract = studentContractOptions.value[0];
  bookingForm.student_contract_id = firstContract?.id || '';
};

const resetBookingForm = () => {
  bookingForm.teacher_id = '';
  bookingForm.course_id = '';
  bookingForm.student_contract_id = '';
  bookingForm.teacher_slot_id = '';
  bookingForm.notes = '';
  courseOptions.value = [];
  teacherSlotOptions.value = [];
  bookingFormRef.value?.clearValidate();
};

const openBookingDialog = async () => {
  if (!currentStudentId.value) {
    ElMessage.warning(t('studentBooking.missingStudentTitle'));
    return;
  }

  resetBookingForm();
  teacherOptions.value = [];
  studentContractOptions.value = [];
  bookingDialogVisible.value = true;
  await loadStudentOptions();
};

const submitBooking = async () => {
  if (!bookingFormRef.value || !currentStudentId.value) return;

  await bookingFormRef.value.validate(async (valid) => {
    if (!valid || !selectedSlot.value) return;

    creating.value = true;
    try {
      const slot = selectedSlot.value;
      const res = assertApiSuccess(await createBooking({
        student_id: currentStudentId.value,
        teacher_id: bookingForm.teacher_id,
        course_id: bookingForm.course_id,
        student_contract_id: bookingForm.student_contract_id || null,
        teacher_contract_id: slot.teacher_contract_id || null,
        teacher_slot_id: slot.id,
        booking_date: slot.slot_date,
        start_time: toTimeText(slot.start_time),
        end_time: toTimeText(slot.end_time),
        notes: bookingForm.notes || null,
      }), t('studentBooking.createFailed'));

      ElMessage.success(res.message || t('studentBooking.msgBookSuccess'));
      bookingDialogVisible.value = false;
      fetchBookings();
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, t('studentBooking.createFailed')));
    } finally {
      creating.value = false;
    }
  });
};

const fetchBookings = async () => {
  if (!currentStudentId.value) {
    bookings.value = [];
    total.value = 0;
    return;
  }

  loading.value = true;
  try {
    const params: Parameters<typeof getBookingList>[0] = {
      page: queryParams.page,
      per_page: queryParams.per_page,
      search: filters.search.trim() || undefined,
      student_id: currentStudentId.value,
      booking_status: filters.status || undefined,
    };

    if (filters.dateRange?.length === 2) {
      params.date_from = filters.dateRange[0];
      params.date_to = filters.dateRange[1];
    }

    const res = assertApiSuccess(await getBookingList(params), t('studentBooking.loadFailed'));
    bookings.value = res.data || [];
    total.value = res.total || 0;
    fetchZoomInfos();
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, t('studentBooking.loadFailed')));
  } finally {
    loading.value = false;
  }
};

const fetchZoomInfos = async () => {
  const ids = bookings.value
    .filter((booking) => ['pending', 'confirmed', 'completed'].includes(booking.booking_status))
    .filter((booking) => !zoomInfoMap.value[booking.id])
    .map((booking) => booking.id);

  if (ids.length === 0) return;

  try {
    const res = assertApiSuccess(await batchGetZoomMeetings(ids), t('studentBooking.loadZoomFailed'));
    if (res.data) {
      zoomInfoMap.value = { ...zoomInfoMap.value, ...res.data };
    }
  } catch {
    // Zoom may not exist before staff confirms/creates a meeting; keep the list usable.
  }
};

const handleSearch = () => {
  queryParams.page = 1;
  fetchBookings();
};

const resetFilters = () => {
  filters.search = '';
  filters.dateRange = [];
  filters.status = '';
  handleSearch();
};

const openLeaveDialog = (booking: BookingItem) => {
  if (!canRequestLeave(booking)) {
    ElMessage.error(t('studentBooking.errorTooLate'));
    return;
  }

  leaveBooking.value = booking;
  leaveDialogVisible.value = true;
};

const resetLeaveForm = () => {
  leaveBooking.value = null;
  leaveForm.reason = '';
  leaveFormRef.value?.clearValidate();
};

const submitLeave = async () => {
  if (!leaveFormRef.value || !leaveBooking.value) return;

  await leaveFormRef.value.validate(async (valid) => {
    if (!valid || !leaveBooking.value) return;

    const confirmMessage = isEmergencyLeave(leaveBooking.value)
      ? t('studentBooking.confirmLateCancel')
      : t('studentBooking.confirmCancel');

    try {
      await ElMessageBox.confirm(confirmMessage, t('studentBooking.dialogLeaveTitle'), {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: isEmergencyLeave(leaveBooking.value) ? 'warning' : 'info',
      });
    } catch {
      return;
    }

    leaving.value = true;
    try {
      const res = assertApiSuccess(await createLeaveRecord({
        booking_id: leaveBooking.value.id,
        reason: leaveForm.reason,
      }), t('studentBooking.leaveFailed'));

      ElMessage.success(res.message || t('studentBooking.msgCancelSuccess'));
      leaveDialogVisible.value = false;
      fetchBookings();
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, t('studentBooking.leaveFailed')));
    } finally {
      leaving.value = false;
    }
  });
};

watch(
  currentStudentId,
  (studentId) => {
    if (!studentId) return;
    resetBookingForm();
    fetchBookings();
  },
  { immediate: true },
);
</script>

<style scoped>
:deep(.filter-form) {
  gap: 20px;
   .el-form-item {
     margin-right: 0;
     margin-bottom: 5px;
   }
}

.student-info-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.info-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-bottom: 4px;
}

.info-value {
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 600;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.info-value.is-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}

.pagination-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

@media (max-width: 768px) {
  .student-info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
