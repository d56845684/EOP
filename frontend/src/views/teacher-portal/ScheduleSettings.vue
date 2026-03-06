<template>
  <div class="schedule-settings">
    <el-card>
      <template #header>
        <div class="header">
          <span class="title">{{ $t('teacherSchedule.title') }}</span>
          <el-button type="primary" @click="openAddDialog">
            {{ $t('teacherSchedule.addTimeBtn') }}
          </el-button>
        </div>
      </template>
      
      <el-calendar v-model="currentDate">
        <template #date-cell="{ data }">
          <div class="date-cell" @click.stop="handleDateClick(data)">
            <span :class="{ 'is-today': data.isSelected }">{{ data.day.split('-').slice(2).join('') }}</span>
            <div class="slots-indicators">
              <span v-if="hasSlots(data.day)" class="dot available"></span>
              <span v-if="hasBookings(data.day)" class="dot booked"></span>
            </div>
          </div>
        </template>
      </el-calendar>
    </el-card>

    <!-- Daily Details Drawer -->
    <el-drawer
      v-model="drawerVisible"
      :title="$t('teacherSchedule.drawerHeader', { date: formattedSelectedDate })"
      direction="rtl"
      size="400px"
      :modal="false"
    >
      <div class="daily-schedule">
        <template v-for="slot in dailySlots" :key="slot.id">
          <el-card class="slot-card" :class="slot.status.toLowerCase()">
            <div class="slot-content">
              <div class="time">{{ formatTime(slot.start) }} ~ {{ formatTime(slot.end) }}</div>
              <div class="status">
                <span v-if="slot.status === 'Available'">{{ $t('teacherSchedule.statusAvailable') }}</span>
                <span v-else-if="slot.status === 'Booked'">
                    {{ $t('teacherSchedule.statusBooked') }} 
                    <span v-if="slot.bookingInfo"> - {{ slot.bookingInfo }}</span>
                </span>
                <span v-else>{{ $t('teacherSchedule.actionLeave') }}</span>
              </div>
            </div>
            <div class="actions">
               <el-dropdown trigger="click" @command="(cmd: string) => handleSlotAction(cmd, slot)">
                    <span class="el-dropdown-link">
                        <el-icon><MoreFilled /></el-icon>
                    </span>
                    <template #dropdown>
                        <el-dropdown-menu>
                            <el-dropdown-item v-if="slot.status === 'Booked'" command="leave">{{ $t('teacherSchedule.actionLeave') }}</el-dropdown-item>
                            <el-dropdown-item v-if="slot.status === 'Available'" command="remove">{{ $t('teacherSchedule.actionRemove') }}</el-dropdown-item>
                        </el-dropdown-menu>
                    </template>
               </el-dropdown>
            </div>
          </el-card>
        </template>
        <el-empty v-if="dailySlots.length === 0" description="No slots" />
      </div>
    </el-drawer>

    <!-- Add Time Dialog -->
    <el-dialog
      v-model="addDialogVisible"
      :title="$t('teacherSchedule.dialogTitle')"
      width="600px"
    >
      <el-form label-width="120px">
        <!-- Date Picker -->
        <el-form-item :label="$t('teacherSchedule.date')">
             <el-date-picker
                v-model="addForm.startDate"
                type="date"
                placeholder="Pick a date"
                value-format="YYYY-MM-DD"
                :disabled-date="disabledDate"
             />
        </el-form-item>

        <!-- Time Range -->
        <el-form-item :label="$t('teacherSchedule.timeRange')">
            <el-time-picker
                v-model="addForm.timeRange"
                is-range
                format="HH:mm"
                value-format="HH:mm"
                :disabled="addForm.isAllDay"
                range-separator="-"
                start-placeholder="Start"
                end-placeholder="End"
            />
            <el-checkbox v-model="addForm.isAllDay" style="margin-left: 10px;">{{ $t('teacherSchedule.allDay') }}</el-checkbox>
        </el-form-item>
        
        <!-- Repeat Type -->
        <el-form-item :label="$t('teacherSchedule.repeat')">
             <el-select v-model="addForm.repeatType">
                <el-option :label="$t('teacherSchedule.repeatNone')" value="none" />
                <el-option :label="$t('teacherSchedule.repeatCustom')" value="custom" />
             </el-select>
        </el-form-item>

         <!-- Custom Repeat Settings -->
        <template v-if="addForm.repeatType === 'custom'">
            <el-form-item :label="$t('teacherSchedule.weekDays')">
                <el-checkbox-group v-model="addForm.weekDays">
                    <el-checkbox-button v-for="day in weekDayOptions" :key="day.value" :label="day.value">
                        {{ day.label }}
                    </el-checkbox-button>
                </el-checkbox-group>
            </el-form-item>

            <el-form-item :label="$t('teacherSchedule.endCondition')">
                <el-radio-group v-model="addForm.endType">
                    <el-radio label="date">{{ $t('teacherSchedule.endDate') }}</el-radio>
                    <el-radio label="count">{{ $t('teacherSchedule.count') }}</el-radio>
                </el-radio-group>
            </el-form-item>

            <el-form-item v-if="addForm.endType === 'date'">
                 <el-date-picker
                    v-model="addForm.endDate"
                    type="date"
                    placeholder="Pick a date"
                    value-format="YYYY-MM-DD"
                    :disabled-date="disabledEndDate"
                 />
            </el-form-item>
            <el-form-item v-if="addForm.endType === 'count'">
                 <el-input-number v-model="addForm.repeatCount" :min="1" :max="52" />
                 <span style="margin-left: 10px">{{ $t('teacherSchedule.times') }}</span>
            </el-form-item>

        </template>
        
        <!-- Removed Description field -->

      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="addDialogVisible = false">{{ $t('teacherSchedule.cancelBtn') }}</el-button>
          <el-button type="primary" @click="saveTimeSlot">{{ $t('teacherSchedule.saveBtn') }}</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Leave Request Dialog -->
    <el-dialog v-model="leaveDialogVisible" :title="$t('teacherSchedule.leaveDialogTitle')" width="400px">
        <el-form layout="top">
            <el-form-item :label="$t('teacherSchedule.leaveReason')">
                <el-input v-model="leaveReason" type="textarea" />
            </el-form-item>
        </el-form>
        <template #footer>
            <el-button type="primary" @click="submitLeaveRequest">{{ $t('teacherSchedule.submitBtn') }}</el-button>
        </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { getTeacherSlots, createTeacherSlot, batchCreateTeacherSlots, deleteTeacherSlot, type TeacherSlotParams, type TeacherSlotCreate, type TeacherSlotBatchCreate } from '@/api/teacherSlot';
import dayjs from 'dayjs';
import { ElMessage, ElMessageBox } from 'element-plus';
import { MoreFilled } from '@element-plus/icons-vue';

const { t } = useI18n();
const authStore = useAuthStore();

// --- State ---
const currentDate = ref(new Date());
const selectedDate = ref('');
const drawerVisible = ref(false);

const addDialogVisible = ref(false);
const leaveDialogVisible = ref(false);
const slots = ref<any[]>([]);

const addForm = reactive({
    startDate: '',
    timeRange: ['09:00', '17:00'],
    isAllDay: false,
    repeatType: 'none', // none, custom
    weekDays: [] as number[],
    endType: 'date', // date, count
    endDate: '',
    repeatCount: 1,
});

const leaveReason = ref('');
const selectedSlotId = ref<string | null>(null);

// --- Computed ---
const currentUser = computed(() => authStore.userInfo);

const formattedSelectedDate = computed(() => {
    return dayjs(selectedDate.value).format('YYYY/MM/DD dddd');
});

const weekDayOptions = computed(() => [
    { value: 1, label: t('teacherSchedule.mon') },
    { value: 2, label: t('teacherSchedule.tue') },
    { value: 3, label: t('teacherSchedule.wed') },
    { value: 4, label: t('teacherSchedule.thu') },
    { value: 5, label: t('teacherSchedule.fri') },
    { value: 6, label: t('teacherSchedule.sat') },
    { value: 0, label: t('teacherSchedule.sun') }
]);

// --- Lifecycle ---
onMounted(async () => {
    await fetchSlots();
});

watch(currentDate, () => {
    fetchSlots();
});

const fetchSlots = async () => {
    if (!currentUser.value) return;
    const start = dayjs(currentDate.value).startOf('month').subtract(1, 'week').format('YYYY-MM-DD');
    const end = dayjs(currentDate.value).endOf('month').add(1, 'week').format('YYYY-MM-DD');
    
    try {
        const params: TeacherSlotParams = {
            teacher_id: currentUser.value.id,
            date_from: start,
            date_to: end
        };
        const res: any = await getTeacherSlots(params);
        const dataList = res.data || res || [];
        
        slots.value = dataList.map((s: any) => ({
            id: s.id,
            start: `${s.slot_date}T${s.start_time}`,
            end: `${s.slot_date}T${s.end_time}`,
            status: s.is_available === false ? 'Booked' : 'Available',
            bookingInfo: s.notes || ''
        }));
    } catch (e: any) {
        console.error(e);
        ElMessage.error(e.response?.data?.message || 'Failed to fetch slots');
    }
};

// --- Calendar Logic ---
const hasSlots = (day: string) => {
    return slots.value.some(s => s.start.startsWith(day));
};

const hasBookings = (day: string) => {
     return slots.value.some(s => s.start.startsWith(day) && s.status === 'Booked');
};

const handleDateClick = (data: any) => {
    selectedDate.value = data.day;
    if (hasSlots(data.day)) {
        drawerVisible.value = true;
    }
};

const disabledDate = (time: Date) => {
    return dayjs(time).isBefore(dayjs(), 'day');
};

const disabledEndDate = (time: Date) => {
     return dayjs(time).isBefore(dayjs(addForm.startDate), 'day');
};

// --- Drawer Logic ---
const dailySlots = computed(() => {
    if (!selectedDate.value) return [];
    const dayStart = dayjs(selectedDate.value).startOf('day');
    const dayEnd = dayjs(selectedDate.value).endOf('day');
    
    const daySlots = slots.value.filter(s => {
        const sStart = dayjs(s.start);
        return sStart.isAfter(dayStart) && sStart.isBefore(dayEnd);
    }).sort((a, b) => dayjs(a.start).diff(dayjs(b.start)));
    
    return daySlots;
});

const formatTime = (iso: string) => dayjs(iso).format('HH:mm');

const handleSlotAction = (cmd: string, slot: any) => {
    if (cmd === 'leave') {
        selectedSlotId.value = slot.id;
        leaveReason.value = '';
        leaveDialogVisible.value = true;
    } else if (cmd === 'remove') {
        ElMessageBox.confirm(
            t('teacherSchedule.confirmRemoveMsg'),
            t('teacherSchedule.confirmRemoveTitle'),
            {
                confirmButtonText: t('common.confirm'),
                cancelButtonText: t('common.cancel'),
                type: 'warning',
            }
        ).then(async () => {
            try {
                await deleteTeacherSlot(slot.id);
                await fetchSlots();
                ElMessage.success(t('common.done'));
            } catch (e: any) {
                ElMessage.error(e.response?.data?.message || 'Failed to delete slot');
            }
        });
    }
};

// --- Add Dialog Logic ---
const openAddDialog = () => {
    const defaultDate = selectedDate.value || dayjs().format('YYYY-MM-DD');
    addForm.startDate = defaultDate;
    addForm.timeRange = ['09:00', '10:00'];
    addForm.isAllDay = false;
    addForm.repeatType = 'none';
    addForm.weekDays = [];
    addForm.endType = 'date';
    addForm.endDate = dayjs(defaultDate).add(1, 'month').format('YYYY-MM-DD');
    addForm.repeatCount = 1;
    
    addDialogVisible.value = true;
};

const saveTimeSlot = async () => {
    if (!currentUser.value || !addForm.startDate) return;
    
    let timeStartStr = '00:00:00';
    let timeEndStr = '00:00:00';
    
    if (addForm.isAllDay) {
        timeStartStr = '06:00:00';
        timeEndStr = '23:59:00';
    } else {
        if (!addForm.timeRange || addForm.timeRange.length !== 2) return;
        timeStartStr = addForm.timeRange[0] + ':00';
        timeEndStr = addForm.timeRange[1] + ':00';
    }
    
    try {
        if (addForm.repeatType === 'none') {
            const data: TeacherSlotCreate = {
                teacher_id: currentUser.value.id,
                slot_date: addForm.startDate,
                start_time: timeStartStr,
                end_time: timeEndStr,
                is_available: true
            };
            await createTeacherSlot(data);
        } else if (addForm.repeatType === 'custom') {
            if (addForm.weekDays.length === 0) {
                ElMessage.warning('Please select at least one day of week');
                return;
            }
            const determinedEndDate = addForm.endType === 'date' 
                ? addForm.endDate 
                : dayjs(addForm.startDate).add(addForm.repeatCount, 'week').format('YYYY-MM-DD');
                
            const data: TeacherSlotBatchCreate = {
                teacher_id: currentUser.value.id,
                start_date: addForm.startDate,
                end_date: determinedEndDate,
                weekdays: addForm.weekDays,
                start_time: timeStartStr,
                end_time: timeEndStr,
            };
            await batchCreateTeacherSlots(data);
        }
        
        addDialogVisible.value = false;
        await fetchSlots();
        ElMessage.success(t('common.done'));
    } catch (e: any) {
        ElMessage.error(e.response?.data?.message || 'Failed to save slots');
    }
};

const submitLeaveRequest = async () => {
    leaveDialogVisible.value = false;
    ElMessage.warning('Leave request logic requires further backend support');
};
</script>

<style scoped lang="scss">
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    .title {
        font-size: 18px;
        font-weight: bold;
    }
}

.date-cell {
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    cursor: pointer;
    
    &:hover {
        background-color: var(--el-fill-color-light);
    }
    
    .slots-indicators {
        display: flex;
        gap: 4px;
        justify-content: center;
        padding-bottom: 4px;
        
        .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            &.available { background-color: var(--el-color-success); }
            &.booked { background-color: var(--el-color-danger); }
        }
    }
}

.daily-schedule {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 10px;
}

.slot-card {
    border-left: 4px solid transparent;
    
    &.available { border-left-color: var(--el-color-success); }
    &.booked { border-left-color: var(--el-color-danger); }
    &.leave { border-left-color: var(--el-color-info); opacity: 0.6; }

    .slot-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        
        .time { font-weight: bold; }
        .status { font-size: 12px; color: var(--el-text-color-secondary); }
    }
    
    :deep(.el-card__body) {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px;
    }
}
</style>
