<template>
  <div class="booking-history">
    <el-card>
      <template #header>
        <div class="header">
          <span class="title">{{ $t('teacherRecords.title') }}</span>
          <el-checkbox v-model="filterIncomplete" :label="$t('teacherRecords.filterIncompleteNotes')" />
        </div>
      </template>

      <el-table :data="pagedData" style="width: 100%" stripe>
        <el-table-column :label="$t('teacherRecords.colDate')" width="120">
          <template #default="{ row }">
            {{ formatDate(row.time) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('teacherRecords.colTime')" width="100">
          <template #default="{ row }">
            {{ formatTime(row.time) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('teacherRecords.colCourse')" prop="courseName">
             <template #default="{ row }">
                {{ getCourseName(row.courseId) }}
             </template>
        </el-table-column>
        <el-table-column :label="$t('teacherRecords.colStudent')" prop="studentName">
             <template #default="{ row }">
                {{ getStudentName(row.studentId) }}
             </template>
        </el-table-column>
        
        <!-- After-Class Notes -->
        <el-table-column :label="$t('teacherRecords.colNotes')" min-width="200">
          <template #default="{ row }">
            <!-- Condition B: Note Exists -->
            <div v-if="row.noteUrl" class="note-link-container">
               <a :href="row.noteUrl" target="_blank" class="note-link">{{ row.noteUrl }}</a>
               <el-button link type="primary" @click="copyLink(row.noteUrl)">
                  <el-icon><CopyDocument /></el-icon>
               </el-button>
               <!-- Allow edit even if exists? User flow says "Condition A: Empty -> Button", "Condition B: Exists -> Link". 
                    Usually users might want to edit. I'll stick to strict requirements but maybe add a small edit icon if strictly not forbidden. 
                    User Requirement: "Condition A ... Condition B". 
                    I'll strictly follow Condition A vs B. -->
            </div>
            <!-- Condition A: Note Empty -->
            <el-button v-else type="primary" link @click="openNoteDialog(row)">
              {{ $t('teacherRecords.btnUpdateNote') }}
            </el-button>
          </template>
        </el-table-column>

        <!-- Actions -->
        <el-table-column :label="$t('teacherRecords.colActions')" width="120">
          <template #default="{ row }">
             <el-button 
                v-if="row.status === 'Scheduled'" 
                type="danger" 
                link 
                @click="openLeaveDialog(row)"
             >
                {{ $t('teacherRecords.btnLeave') }}
             </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="tableData.length"
          layout="total, prev, pager, next"
        />
      </div>
    </el-card>

    <!-- Dialog A: Update Notes -->
    <el-dialog v-model="noteDialogVisible" :title="$t('teacherRecords.dialogNoteTitle')" width="500px">
        <el-form>
            <el-form-item label="URL">
                <el-input v-model="noteForm.url" placeholder="https://..." />
            </el-form-item>
        </el-form>
        <template #footer>
            <el-button @click="noteDialogVisible = false">{{ $t('common.cancel') }}</el-button>
            <el-button type="primary" @click="saveNote">{{ $t('common.confirm') }}</el-button>
        </template>
    </el-dialog>

    <!-- Dialog B: Leave Request -->
    <el-dialog v-model="leaveDialogVisible" :title="$t('teacherRecords.dialogLeaveTitle')" width="500px">
        <el-form layout="top">
            <el-form-item :label="$t('teacherRecords.labelLeaveReason')">
                <el-input v-model="leaveReason" type="textarea" />
            </el-form-item>
        </el-form>
        <template #footer>
            <el-button @click="leaveDialogVisible = false">{{ $t('common.cancel') }}</el-button>
            <el-button type="primary" @click="submitLeave">{{ $t('common.confirm') }}</el-button>
        </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMockStore, type Booking } from '../../stores/mockStore';
import dayjs from 'dayjs';
import { ElMessage, ElMessageBox } from 'element-plus';
import { CopyDocument } from '@element-plus/icons-vue';
import { useClipboard } from '@vueuse/core';

const { t } = useI18n();
const store = useMockStore();
const { copy } = useClipboard();

// --- State ---
const filterIncomplete = ref(false);
const currentPage = ref(1);
const pageSize = ref(10);
const allBookings = ref<Booking[]>([]);

const noteDialogVisible = ref(false);
const leaveDialogVisible = ref(false);
const currentBooking = ref<Booking | null>(null);

const noteForm = reactive({
    url: ''
});
const leaveReason = ref('');

// --- Helpers ---
const currentUser = computed(() => store.currentUser);

const formatDate = (iso: string) => dayjs(iso).format('YYYY-MM-DD');
const formatTime = (iso: string) => dayjs(iso).format('HH:mm');

const getCourseName = (id: string) => {
    const c = store.courses.find(x => x.id === id);
    return c ? c.name : id;
};

const getStudentName = (id: string) => {
    const s = store.students.find(x => x.id === id);
    return s ? s.name : id;
};

// --- Data Fetching ---
const fetchData = async () => {
    if (!currentUser.value) return;
    
    // --- Dynamic Mock Data Generation for Testing ---
    // User requested 7 specific records relative to today.
    
    const today = dayjs();
    const mockRecords: Booking[] = [
        // 1. Past Records (3 items)
        {
            id: 'mock-p1',
            time: today.subtract(1, 'day').hour(10).minute(0).toISOString(),
            status: 'Completed',
            noteUrl: 'https://notes.example.com/class1',
            studentId: 's1', teacherId: currentUser.value.id, courseId: 'c1', type: 'Regular', isConverted: false, createdAt: ''
        },
        {
            id: 'mock-p2',
            time: today.subtract(2, 'day').hour(14).minute(0).toISOString(),
            status: 'Completed',
            noteUrl: '', // Empty to test filter
            studentId: 's2', teacherId: currentUser.value.id, courseId: 'c1', type: 'Regular', isConverted: false, createdAt: ''
        },
        {
            id: 'mock-p3',
            time: today.subtract(3, 'day').hour(16).minute(0).toISOString(),
            status: 'Completed',
            noteUrl: '', // Empty
            studentId: 's1', teacherId: currentUser.value.id, courseId: 'c2', type: 'Trial', isConverted: false, createdAt: ''
        },
        
        // 2. Future Records (3 items)
        {
            id: 'mock-f1',
            time: today.add(1, 'day').hour(9).minute(0).toISOString(), // Tomorrow
            status: 'Scheduled',
            noteUrl: '',
            studentId: 's2', teacherId: currentUser.value.id, courseId: 'c2', type: 'Regular', isConverted: false, createdAt: ''
        },
        {
            id: 'mock-f2',
            time: today.add(3, 'day').hour(11).minute(0).toISOString(),
            status: 'Scheduled',
            noteUrl: '',
            studentId: 's1', teacherId: currentUser.value.id, courseId: 'c1', type: 'Regular', isConverted: false, createdAt: ''
        },
        {
            id: 'mock-f3',
            time: today.add(1, 'week').hour(15).minute(0).toISOString(),
            status: 'Scheduled',
            noteUrl: '',
            studentId: 's2', teacherId: currentUser.value.id, courseId: 'c1', type: 'Regular', isConverted: false, createdAt: ''
        },
        
        // 3. Today's Record (1 item)
        {
            id: 'mock-t1',
            time: today.hour(13).minute(0).toISOString(),
            status: 'Scheduled',
            noteUrl: '',
            studentId: 's1', teacherId: currentUser.value.id, courseId: 'c1', type: 'Trial', isConverted: false, createdAt: ''
        }
    ];

    allBookings.value = mockRecords;
    
    // Sort desc by time
    allBookings.value.sort((a, b) => dayjs(b.time).diff(dayjs(a.time)));
};

onMounted(() => {
    fetchData();
});

// --- Computed Data ---
const tableData = computed(() => {
    let data = allBookings.value;
    
    if (filterIncomplete.value) {
        data = data.filter(b => !b.noteUrl);
    }
    
    return data;
});

const pagedData = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value;
    return tableData.value.slice(start, start + pageSize.value);
});

// --- Actions ---
const openNoteDialog = (row: Booking) => {
    currentBooking.value = row;
    noteForm.url = '';
    noteDialogVisible.value = true;
};

const saveNote = async () => {
    if (currentBooking.value && noteForm.url) {
        // Update in store
        // Update in store or local mock
        // Since we are using local component mock data for this view's testing, we update local first.
        // In real app, we'd call store action. Here we update "allBookings" to reflect change in UI immediately.
        const localTarget = allBookings.value.find(b => b.id === currentBooking.value?.id);
        if (localTarget) {
            localTarget.noteUrl = noteForm.url;
            ElMessage.success(t('common.save') + ' ' + t('common.done'));
        }
        
        // Also try to update store if it exists there (it won't because these are local mocks, but failsafe)
        const target = store.bookings.find(b => b.id === currentBooking.value?.id);
        if (target) {
            target.noteUrl = noteForm.url;
        }
        noteDialogVisible.value = false;
        fetchData(); // Refresh local list
    }
};

const openLeaveDialog = (row: Booking) => {
    currentBooking.value = row;
    leaveReason.value = '';
    leaveDialogVisible.value = true;
};

const submitLeave = async () => {
    if (currentBooking.value) {
        // Update local mock
        const localTarget = allBookings.value.find(b => b.id === currentBooking.value?.id);
        if (localTarget) {
             localTarget.status = 'Cancelled';
             if (leaveReason.value) localTarget.note = (localTarget.note || '') + ` [Leave: ${leaveReason.value}]`;
             ElMessage.success(t('teacherRecords.btnLeave') + ' ' + t('common.done'));
        }

        const target = store.bookings.find(b => b.id === currentBooking.value?.id);
        if (target) {
            target.status = 'Cancelled'; // Or Leave? Interface says Cancelled/Completed/Scheduled. 
            // MockStore has bookings status type: 'Scheduled' | 'Completed' | 'Cancelled'
            // I'll set it to Cancelled + add a note maybe?
            if (leaveReason.value) target.note = (target.note || '') + ` [Leave: ${leaveReason.value}]`;
        }
        leaveDialogVisible.value = false;
        fetchData();
    }
};

const copyLink = (url: string) => {
    copy(url);
    ElMessage.success(t('teacherRecords.msgCopySuccess'));
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

.note-link-container {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .note-link {
        color: var(--el-color-primary);
        text-decoration: underline;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 150px;
        display: inline-block;
    }
}

.pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
}
</style>
