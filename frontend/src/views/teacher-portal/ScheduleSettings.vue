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
import { ref, computed, onMounted, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMockStore, type TeacherSlot } from '../../stores/mockStore';
import dayjs from 'dayjs';
import { ElMessage, ElMessageBox } from 'element-plus';
import { MoreFilled } from '@element-plus/icons-vue';

const { t } = useI18n();
const store = useMockStore();

// --- State ---
const currentDate = ref(new Date());
const selectedDate = ref('');
const drawerVisible = ref(false);

const addDialogVisible = ref(false);
const leaveDialogVisible = ref(false);
const slots = ref<TeacherSlot[]>([]);

const addForm = reactive({
    startDate: '',
    timeRange: ['09:00', '17:00'],
    isAllDay: false,
    repeatType: 'none', // none, custom
    // Custom logic
    weekDays: [] as number[], // 0=Sun, 1=Mon... wait, dayjs().day() 0=Sun.
    endType: 'date', // date, count
    endDate: '',
    repeatCount: 1,
});

const leaveReason = ref('');
const selectedSlotId = ref<string | null>(null);

// --- Computed ---
const currentUser = computed(() => store.currentUser);

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
    await fetchRequest();
});

const fetchRequest = async () => {
    if (!currentUser.value) return;
    const start = dayjs(currentDate.value).startOf('month').subtract(1, 'week').toISOString();
    const end = dayjs(currentDate.value).endOf('month').add(1, 'week').toISOString();
    slots.value = await store.fetchSlots(currentUser.value.id, start, end);
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
    // currentDate.value = new Date(data.day); // Sync calendar current view
    
    // Only open drawer if there are slots
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
    
    // Get raw slots for day
    const dayStart = dayjs(selectedDate.value).startOf('day');
    const dayEnd = dayjs(selectedDate.value).endOf('day');
    
    const daySlots = slots.value.filter(s => {
        const sStart = dayjs(s.start);
        return sStart.isAfter(dayStart) && sStart.isBefore(dayEnd);
    }).sort((a, b) => dayjs(a.start).diff(dayjs(b.start)));
    
    return daySlots.map(s => {
        let info = '';
        if (s.status === 'Booked' && s.bookingId) {
             const booking = store.bookings.find(b => b.id === s.bookingId);
             if (booking) {
                 const course = store.courses.find(c => c.id === booking.courseId);
                 const student = store.students.find(st => st.id === booking.studentId);
                 info = `${course?.name || 'Course'} - ${student?.name || 'Student'}`;
             }
        }
        return { ...s, bookingInfo: info };
    });
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
            await store.removeSlot(slot.id);
            await fetchRequest();
            ElMessage.success(t('common.done'));
        });
    }
};

// --- Add Dialog Logic ---
const openAddDialog = () => {
    // Default to currently selected date or today
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
    
    // Preparation
    const baseDate = addForm.startDate;
    let timeStartStr = '00:00';
    let timeEndStr = '00:00';
    
    if (addForm.isAllDay) {
        timeStartStr = '06:00';
        timeEndStr = '23:59';
    } else {
        if (!addForm.timeRange) return;
        timeStartStr = addForm.timeRange[0];
        timeEndStr = addForm.timeRange[1];
    }
    
    // Generate dates to add
    const datesToAdd: string[] = [];
    
    if (addForm.repeatType === 'none') {
        datesToAdd.push(baseDate);
    } else if (addForm.repeatType === 'custom') {
        // Validation
        if (addForm.weekDays.length === 0) {
            ElMessage.warning('Please select at least one day of week');
            return;
        }

        let current = dayjs(baseDate);
        let count = 0;
        const maxDate = addForm.endType === 'date' ? dayjs(addForm.endDate) : dayjs(baseDate).add(2, 'year'); // safety
        const maxCount = addForm.endType === 'count' ? addForm.repeatCount : 999; 

        // Safety break loop
        let safety = 0;
        while (safety < 300) { // Limit 300 days/iterations check
            if (addForm.endType === 'date' && current.isAfter(maxDate)) break;
            if (addForm.endType === 'count' && count >= maxCount) break;
            
            const currentDayOfWeek = current.day(); // 0-6
            if (addForm.weekDays.includes(currentDayOfWeek)) {
                datesToAdd.push(current.format('YYYY-MM-DD'));
                count++;
            }
            
            current = current.add(1, 'day');
            safety++;
        }
    }
    
    // Create Slots for each date
    for (const dateStr of datesToAdd) {
        // Parse start/end for this date
        const startISO = `${dateStr}T${timeStartStr}:00`;
        const endISO = `${dateStr}T${timeEndStr}:00`;
        
        let slotCurrent = dayjs(startISO);
        const slotEnd = dayjs(endISO);
        
        // Generate 30 min segments (simplified safety 50 slots per day)
        let daySafety = 0;
        while(slotCurrent.isBefore(slotEnd) && daySafety < 50) {
            const next = slotCurrent.add(30, 'minute');
            if (next.isAfter(slotEnd)) break;
            
            // Check formatted string logic if spanning days?
            // Assuming simplified same-day slots 06:00-23:59
            
            const newSlot: TeacherSlot = {
                id: `ts-${Date.now()}-${daySafety}-${Math.random().toString(36).substr(2, 5)}`,
                teacherId: currentUser.value.id,
                start: slotCurrent.toISOString(),
                end: next.toISOString(),
                status: 'Available'
            };
            
            await store.addSlot(newSlot);
            slotCurrent = next;
            daySafety++;
        }
    }

    addDialogVisible.value = false;
    await fetchRequest();
    ElMessage.success(t('common.done'));
};

const submitLeaveRequest = async () => {
    if (selectedSlotId.value) {
        await store.updateSlotStatus(selectedSlotId.value, 'Leave');
        leaveDialogVisible.value = false;
        await fetchRequest();
        ElMessage.success(t('common.done'));
    }
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
