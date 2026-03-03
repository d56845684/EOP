<template>
  <div class="student-list-page">
    
    <!-- Search / Filter Bar -->
    <el-card class="filter-card mb-20">
        <div class="filter-row">
            <el-input v-model="filters.contractId" :placeholder="$t('student.filter.contractId')" class="filter-item" clearable style="width: 200px;" />
            <el-input v-model="filters.keyword" :placeholder="$t('student.filter.keyword')" class="filter-item" clearable :prefix-icon="Search" style="width: 200px;" />
            <el-select v-model="filters.identity" :placeholder="$t('student.filter.identity')" clearable class="filter-item" style="width: 160px;">
                <el-option :label="$t('student.type.regular')" value="Regular" />
                <el-option :label="$t('student.type.trial')" value="Trial" />
            </el-select>
            <el-date-picker
                v-model="filters.dateRange"
                type="daterange"
                range-separator="To"
                :start-placeholder="$t('common.startDate')"
                :end-placeholder="$t('common.endDate')"
                class="filter-item"
                style="width: 260px;"
            />
            <div class="spacer"></div>
            <el-button :icon="Download" @click="handleExport">{{ $t('common.export') }}</el-button>
            <el-button type="primary" :icon="Plus" @click="openDrawer(null)">{{ $t('student.add') }}</el-button>
        </div>
    </el-card>

    <!-- Student Table -->
    <el-card>
      <el-table :data="paginatedStudents" style="width: 100%" v-loading="loading" stripe>
        <!-- 1. Name (No Avatar) -->
        <el-table-column prop="name" :label="$t('common.name')" min-width="120" />
        
        <!-- 2. Eng Name -->
        <el-table-column prop="engName" :label="$t('student.engName')" min-width="120" />

        <!-- 3. Identity -->
        <el-table-column :label="$t('student.identity')" width="120">
           <template #default="{ row }">
             <el-tag :type="row.type === 'Regular' ? 'success' : 'info'" effect="dark">
               {{ row.type === 'Regular' ? 'Regular' : 'Trial' }}
             </el-tag>
           </template>
        </el-table-column>
        
        <!-- 4. Email -->
        <el-table-column prop="email" :label="$t('common.email')" min-width="180" />

        <!-- 5. Phone -->
        <el-table-column prop="phone" :label="$t('common.phone')" min-width="120" />

        <!-- 6. Contract Time -->
        <el-table-column :label="$t('student.contractTime')" min-width="200">
             <template #default="{ row }">
                 <div v-if="row.contractPeriod && row.contractPeriod[0]">
                     {{ row.contractPeriod[0] }} ~ {{ row.contractPeriod[1] }}
                 </div>
                 <span v-else class="text-gray">-</span>
             </template>
        </el-table-column>

        <!-- 7. Last Updated -->
        <el-table-column :label="$t('common.lastUpdated')" width="180">
            <template #default="{ row }">{{ formatDateTime(row.updatedAt) }}</template>
        </el-table-column>

        <!-- 8. Details (Standalone) -->
        <el-table-column :label="$t('common.details')" width="120" align="center">
            <template #default="{ row }">
                <el-button size="small" :icon="Document" @click="openDetails(row)">{{ $t('common.viewDetails') }}</el-button>
            </template>
        </el-table-column>

        <!-- 9. Actions -->
        <el-table-column :label="$t('common.actions')" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" :icon="Edit" @click="openDrawer(row)">{{ $t('common.edit') }}</el-button>
            
            <el-button 
               v-if="row.type === 'Regular'" 
               type="primary" 
               link 
               size="small"
               @click="openAddCourseDialog(row)"
            >
              {{ $t('student.addCourse') }}
            </el-button>

            <el-button 
                 v-if="row.type === 'Trial' && (row.contractFileUrl || row.contractUrl)" 
                 type="success" 
                 size="small" 
                 link
                 @click="handleActivate(row)"
               >
                 {{ $t('student.activate') }}
             </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-footer">
         <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="students.length"
         />
      </div>
    </el-card>

    <!-- Edit/Add Drawer -->
    <el-drawer
      v-model="editDrawerVisible"
      :title="isAddMode ? $t('student.addTitle') : $t('student.editTitle')"
      size="500px"
    >
        <el-form :model="form" :rules="rules" ref="formRef" label-width="140px" label-position="right">
            <!-- 1. Name -->
            <el-form-item :label="$t('common.name')" prop="name">
                <el-input v-model="form.name" />
            </el-form-item>
            <!-- 2. Eng Name -->
            <el-form-item :label="$t('student.engName')" prop="engName">
                <el-input v-model="form.engName" />
            </el-form-item>
             <!-- 3. Birthday -->
            <el-form-item label="Birthday" prop="birthday">
                <el-date-picker v-model="form.birthday" type="date" placeholder="Select Date" style="width: 100%" />
            </el-form-item>
             <!-- 4. Email -->
             <el-form-item :label="$t('common.email')" prop="email">
                <el-input v-model="form.email" />
            </el-form-item>
             <!-- 5. Phone -->
             <el-form-item :label="$t('common.phone')" prop="phone">
                <el-input v-model="form.phone" />
            </el-form-item>
             <!-- 6. Address -->
            <el-form-item :label="$t('common.address')" prop="address">
                <el-input v-model="form.address" />
            </el-form-item>
             <!-- 7. Emergency Contact (Split) -->
            <el-form-item :label="$t('student.emergencyName')">
                <el-input v-model="form.emergencyContactName" placeholder="Name" />
            </el-form-item>
            <el-form-item :label="$t('student.emergencyPhone')">
                <el-input v-model="form.emergencyContactPhone" placeholder="Phone" />
            </el-form-item>
             <!-- 8. Contract ID (Read Only) -->
            <el-form-item :label="$t('student.contractId')">
                <el-input v-model="form.contractId" disabled />
            </el-form-item>
             <!-- 9. Contract Period -->
            <el-form-item :label="$t('student.contractTime')">
                <el-date-picker
                    v-model="form.contractPeriod"
                    type="daterange"
                    range-separator="To"
                    :start-placeholder="$t('common.startDate')"
                    :end-placeholder="$t('common.endDate')"
                    style="width: 100%"
                />
            </el-form-item>
             <!-- 10. Contract File -->
            <el-form-item label="Contract File">
                <el-upload
                  action="#"
                  :show-file-list="true"
                  :auto-upload="false"
                  :on-change="handleUploadContract"
                  limit="1"
                >
                    <el-button type="primary" link>{{ $t('course.upload') }}</el-button>
                    <div v-if="form.contractFileUrl" class="text-gray text-xs ml-2">File: {{ form.contractFileUrl }}</div>
                </el-upload>
            </el-form-item>
             <!-- 11. Leave Limit -->
            <el-form-item :label="$t('student.leaveLimit')">
                <el-input-number v-model="form.leaveLimit" :min="0" />
            </el-form-item>
             <!-- 12. Note -->
            <el-form-item :label="$t('common.note')">
                <el-input v-model="form.note" type="textarea" />
            </el-form-item>
        </el-form>
        <template #footer>
            <el-button @click="editDrawerVisible = false">{{ $t('common.cancel') }}</el-button>
            <el-button type="primary" @click="handleSave(formRef)">{{ $t('common.save') }}</el-button>
        </template>
    </el-drawer>

    <!-- Details Drawer -->
    <el-drawer
      v-model="detailsDrawerVisible"
      :title="$t('student.detailsTitle')"
      size="700px"
    >
        <el-tabs v-model="activeDetailsTab">
            <!-- Tab 1: Basic Info -->
            <el-tab-pane :label="$t('student.basicInfo')" name="basic">
                <el-descriptions :column="1" border label-width="160px">
                    <el-descriptions-item :label="$t('common.name')">{{ currentStudent?.name }}</el-descriptions-item>
                    <el-descriptions-item :label="$t('student.engName')">{{ currentStudent?.engName }}</el-descriptions-item>
                    <el-descriptions-item :label="$t('student.identity')">
                        <el-tag :type="currentStudent?.type === 'Regular' ? 'success' : 'info'">{{ currentStudent?.type }}</el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item :label="$t('student.contractId')">
                        <div class="flex-between">
                            <span>{{ currentStudent?.contractId || '--' }}</span>
                            <el-button v-if="currentStudent?.contractFileUrl || currentStudent?.contractUrl" size="small" link type="primary">View Contract</el-button>
                        </div>
                    </el-descriptions-item>
                    <el-descriptions-item :label="$t('student.contractTime')">
                        <span v-if="currentStudent?.contractPeriod">{{ currentStudent.contractPeriod[0] }} ~ {{ currentStudent.contractPeriod[1] }}</span>
                        <span v-else>-</span>
                    </el-descriptions-item>
                    <el-descriptions-item label="Birthday">{{ currentStudent?.birthday }}</el-descriptions-item>
                    <el-descriptions-item :label="$t('common.email')">{{ currentStudent?.email }}</el-descriptions-item>
                    <el-descriptions-item :label="$t('common.phone')">{{ currentStudent?.phone }}</el-descriptions-item>
                    <el-descriptions-item :label="$t('student.emergencyName')">{{ currentStudent?.emergencyContactName }}</el-descriptions-item>
                    <el-descriptions-item :label="$t('student.emergencyPhone')">{{ currentStudent?.emergencyContactPhone }}</el-descriptions-item>
                    <el-descriptions-item :label="$t('common.note')">{{ currentStudent?.note }}</el-descriptions-item>
                    <el-descriptions-item label="Last Login">--</el-descriptions-item>
                </el-descriptions>
            </el-tab-pane>

            <!-- Tab 2: Purchased Courses -->
            <el-tab-pane :label="$t('student.purchasedCourses')" name="courses">
                <el-table :data="purchasedCoursesList" border stripe>
                     <el-table-column prop="name" label="Course Name" />
                     <el-table-column prop="sessions" label="Total Sessions" width="120" />
                     <el-table-column prop="teacher" :label="$t('common.teacher')" />
                     <el-table-column prop="date" label="Purchase Date" />
                     <el-table-column prop="status" :label="$t('common.status')">
                         <template #default>
                            <el-tag type="success" size="small">Active</el-tag>
                         </template>
                     </el-table-column>
                </el-table>
                <div class="mt-20 text-center" v-if="purchasedCoursesList.length === 0">
                    <span class="text-gray">No purchased courses</span>
                </div>
            </el-tab-pane>

             <!-- Tab 3: Class Records -->
             <el-tab-pane :label="$t('student.classRecords')" name="records">
                <!-- Filter for Records -->
                 <div class="filter-row mb-10">
                     <el-select :placeholder="$t('common.status')" size="small" style="width: 120px;">
                        <el-option value="Completed" label="Completed" />
                        <el-option value="Scheduled" label="Scheduled" />
                     </el-select>
                     <el-date-picker type="daterange" size="small" style="width: 200px;" :start-placeholder="$t('common.startDate')" :end-placeholder="$t('common.endDate')" />
                     <el-button size="small" :icon="Download">{{ $t('common.export') }}</el-button>
                 </div>

                <el-table :data="studentRecords" border height="400">
                    <el-table-column prop="courseName" :label="$t('common.course')" width="150" />
                    <el-table-column prop="time" :label="$t('salary.dateTime')" width="160" />
                    <el-table-column :label="$t('common.teacher')">
                        <template #default="{ row }">
                            {{ row.teacherName }}
                            <el-tag v-if="row.isSubstitute" type="warning" size="small" effect="plain" class="ml-5">Substitute</el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column prop="duration" :label="$t('course.duration')" width="100">
                        <template #default="{ row }">{{ row.duration }} min</template>
                    </el-table-column>
                    <el-table-column prop="status" :label="$t('common.status')">
                        <template #default="{ row }">
                            <el-tag :type="row.status === 'Completed' ? 'success' : 'warning'" size="small">{{ row.status }}</el-tag>
                        </template>
                    </el-table-column>
                </el-table>
             </el-tab-pane>
        </el-tabs>
    </el-drawer>

    <!-- Add Course Dialog -->
    <el-dialog
        v-model="addCourseDialogVisible"
        :title="$t('student.addCourse')"
        width="400px"
    >
        <el-form :model="addCourseForm" label-width="100px" label-position="top">
            <el-form-item :label="$t('student.courseLabel')">
                <el-select v-model="addCourseForm.courseId" filterable placeholder="Select Course" @change="handleCourseChange">
                    <el-option v-for="c in store.courses" :key="c.id" :label="`${c.code || c.id} - ${c.name}`" :value="c.id" />
                </el-select>
            </el-form-item>
            <el-form-item :label="$t('student.teacherLabel')">
                <el-select v-model="addCourseForm.teacherId" placeholder="Select Teacher">
                    <el-option v-for="t in teacherOptions" :key="t.id" :label="t.name" :value="t.id" />
                </el-select>
            </el-form-item>
            <el-form-item :label="$t('student.sessionsLabel')">
                <el-input-number v-model="addCourseForm.sessions" :min="1" @change="calculateTotal" />
            </el-form-item>
            <el-form-item :label="$t('student.totalAmountLabel')">
                <el-input v-model="addCourseForm.totalAmount" />
            </el-form-item>
        </el-form>
        <template #footer>
            <el-button @click="addCourseDialogVisible = false">{{ $t('common.cancel') }}</el-button>
            <el-button type="primary" @click="saveCourse">{{ $t('common.confirm') }}</el-button>
        </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { useMockStore, type Student, type Course } from '../../stores/mockStore';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { Search, Plus, Download, Edit, Document } from '@element-plus/icons-vue';
import dayjs from 'dayjs';

const store = useMockStore();

// --- Filters ---
const filters = reactive({
    contractId: '',
    keyword: '',
    identity: '',
    dateRange: [] as [string, string] | []
});

// --- List Data ---
const students = computed(() => {
    let list = store.students;

    // Filter Logic
    if (filters.contractId) {
        list = list.filter(s => s.contractId === filters.contractId);
    }
    if (filters.identity) {
        list = list.filter(s => s.type === filters.identity);
    }
    if (filters.keyword) {
        const k = filters.keyword.toLowerCase();
        list = list.filter(s => 
            s.name.toLowerCase().includes(k) || 
            (s.engName && s.engName.toLowerCase().includes(k)) || 
            (s.email && s.email.toLowerCase().includes(k))
        );
    }
    if (filters.dateRange && filters.dateRange.length === 2) {
        const [start, end] = filters.dateRange;
        list = list.filter(s => dayjs(s.updatedAt).isAfter(start) && dayjs(s.updatedAt).isBefore(end));
    }
    return list;
});

const loading = ref(false);

// --- Pagination State ---
const currentPage = ref(1);
const pageSize = ref(10);
const paginatedStudents = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value;
    const end = start + pageSize.value;
    return students.value.slice(start, end);
});

// Reset page on filter change
watch(filters, () => {
    currentPage.value = 1;
}, { deep: true });

// --- Drawers State ---
const editDrawerVisible = ref(false);
const detailsDrawerVisible = ref(false);
const isAddMode = ref(false);
const activeDetailsTab = ref('basic');

// --- Form State ---
const formRef = ref<FormInstance>();
const form = reactive<Student>({
    id: '',
    name: '',
    engName: '',
    birthday: '',
    email: '',
    phone: '',
    address: '',
    emergencyContactName: '',
    emergencyContactPhone: '',
    contractId: '',
    contractPeriod: ['', ''],
    contractFileUrl: '',
    leaveLimit: 2,
    note: '',
    type: 'Trial',
    credits: 0,
    purchasedCourses: [],
    avatar: '',
    updatedAt: ''
});

const rules = reactive<FormRules>({
    name: [{ required: true, message: 'Required' }],
    engName: [{ required: true, message: 'Required' }],
    birthday: [{ required: true, message: 'Required' }],
    email: [{ required: true, message: 'Required' }],
    phone: [{ required: true, message: 'Required' }],
    address: [{ required: true, message: 'Required' }]
});

// --- Details State ---
const currentStudentId = ref<string | null>(null);
const currentStudent = computed(() => store.students.find(s => s.id === currentStudentId.value));
const studentRecords = computed(() => {
    if (!currentStudentId.value) return [];
    return store.bookings.filter(b => b.studentId === currentStudentId.value).map(b => {
         const course = store.courses.find(c => c.id === b.courseId);
         const teacher = store.teachers.find(t => t.id === b.teacherId);
         // Substitute Logic: If booking teacher != course default teacher
         const isSubstitute = course && course.defaultTeacherId && course.defaultTeacherId !== b.teacherId;
         
         return {
             courseName: course?.name || b.courseId,
             time: dayjs(b.time).format('YYYY-MM-DD HH:mm'),
             teacherName: teacher?.name || 'Unknown',
             isSubstitute,
             duration: course?.duration || 60,
             status: b.status
         };
    });
});
const purchasedCoursesList = computed(() => {
    if (!currentStudent.value) return [];
    return currentStudent.value.purchasedCourses.map(pc => {
        const c = store.courses.find(x => x.id === pc.courseId);
        return {
            name: c ? c.name : pc.courseId,
            sessions: 10, // Mock total sessions per purchase
            teacher: c ? store.teachers.find(t => t.id === c.defaultTeacherId)?.name : '-',
            date: dayjs(pc.date).format('YYYY-MM-DD'),
            status: 'Active'
        };
    });
});

// --- Add Course Dialog Types & State ---
const addCourseDialogVisible = ref(false);
const addCourseForm = reactive({
    studentId: '',
    courseId: '',
    teacherId: '',
    sessions: 1,
    totalAmount: 0
});

const teacherOptions = computed(() => {
    if (!addCourseForm.courseId) return [];
    // Filter teachers who have this courseId in their courseIds array
    return store.teachers.filter(t => t.courseIds?.includes(addCourseForm.courseId));
});

// --- Actions ---

const handleSearch = () => {
    // Computed triggers automatically
    ElMessage.success('Search Filter Applied');
};

const handleExport = () => {
    ElMessage.success('Exporting Data... (Mock)');
};

const openDrawer = (row: Student | null) => {
    if (row) {
        // Edit Mode
        isAddMode.value = false;
        const data = JSON.parse(JSON.stringify(row));
        Object.assign(form, data);
        if (!form.contractPeriod) form.contractPeriod = ['', ''];
    } else {
        // Add Mode
        isAddMode.value = true;
        Object.assign(form, {
            id: '',
            name: '',
            engName: '',
            birthday: '',
            email: '',
            phone: '',
            address: '',
            emergencyContactName: '',
            emergencyContactPhone: '',
            contractId: 'CT-' + Date.now(),
            contractPeriod: [dayjs().format('YYYY-MM-DD'), dayjs().add(3, 'month').format('YYYY-MM-DD')],
            contractFileUrl: '',
            leaveLimit: 2,
            note: '',
            type: 'Trial',
            credits: 0,
            purchasedCourses: [],
            avatar: 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png',
            updatedAt: ''
        });
    }
    editDrawerVisible.value = true;
};

const openDetails = (row: Student) => {
    currentStudentId.value = row.id;
    activeDetailsTab.value = 'basic';
    detailsDrawerVisible.value = true;
};

const handleSave = async (formEl: FormInstance | undefined) => {
    if (!formEl) return;
    await formEl.validate((valid) => {
        if (valid) {
            form.updatedAt = dayjs().toISOString();
            
            // Mock Save to Store
            const idx = store.students.findIndex(s => s.id === form.id);
            if (idx !== -1) {
                store.students[idx] = { ...form };
            } else {
                form.id = 's' + Date.now();
                store.students.push({ ...form });
            }
            
            editDrawerVisible.value = false;
            ElMessage.success(isAddMode.value ? 'Student Added' : 'Student Updated');
        }
    });
};

const handleActivate = async (row: Student) => {
    if (!row.contractUrl && !row.contractFileUrl) {
         ElMessage.warning('No contract file uploaded.');
         return;
    }
    await store.activateStudent(row.id);
};

// --- Add Course Logic ---
const openAddCourseDialog = (row: Student) => {
    addCourseForm.studentId = row.id;
    addCourseForm.courseId = '';
    addCourseForm.teacherId = '';
    addCourseForm.sessions = 1;
    addCourseForm.totalAmount = 0;
    addCourseDialogVisible.value = true;
};

const handleCourseChange = (courseId: string) => {
    const course = store.courses.find(c => c.id === courseId);
    if (course) {
        // Auto select default teacher if available and in list
        // We need to wait for computed updates or just check store
        const potentialTeachers = store.teachers.filter(t => t.courseIds?.includes(courseId));
        if (potentialTeachers.length > 0) {
             // If course has specific defaultTeacherId, try to select matches
             if (course.defaultTeacherId && potentialTeachers.find(t => t.id === course.defaultTeacherId)) {
                 addCourseForm.teacherId = course.defaultTeacherId;
             } else {
                 addCourseForm.teacherId = potentialTeachers[0].id; // Fallback to first
             }
        } else {
            addCourseForm.teacherId = '';
        }
    }
    calculateTotal();
};

const calculateTotal = () => {
    if (!addCourseForm.courseId) return;
    const course = store.courses.find(c => c.id === addCourseForm.courseId);
    if (course) {
        addCourseForm.totalAmount = course.price * addCourseForm.sessions;
    }
};

const saveCourse = () => {
    if (!addCourseForm.courseId || !addCourseForm.teacherId) {
        ElMessage.warning('Please select course and teacher');
        return;
    }
    const student = store.students.find(s => s.id === addCourseForm.studentId);
    if (student) {
        if (!student.purchasedCourses) student.purchasedCourses = [];
        student.purchasedCourses.push({
            courseId: addCourseForm.courseId,
            date: dayjs().toISOString()
        });
        student.updatedAt = dayjs().toISOString();
        ElMessage.success(`Course added. Total: $${addCourseForm.totalAmount} (Mock Save)`);
        addCourseDialogVisible.value = false;
    }
};

const handleUploadContract = (file: any) => {
    form.contractFileUrl = 'mock_contract_' + file.name;
    ElMessage.success('Contract uploaded (mock)');
};

// --- Helpers ---
const formatDateTime = (d: string) => d ? dayjs(d).format('YYYY-MM-DD HH:mm:ss') : '-';

</script>

<style scoped>
.student-list-page {
    padding: 20px;
}
.pagination-footer { display: flex; justify-content: flex-end; margin-top: 20px; }
.filter-row {
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
}
.spacer {
    flex: 1;
}
.filter-item {
    min-width: 150px;
}
.flex-center {
    display: flex;
    align-items: center;
}
.mr-10 { margin-right: 10px; }
.mb-20 { margin-bottom: 20px; }
.mb-10 { margin-bottom: 10px; }
.mt-20 { margin-top: 20px; }
.ml-5 { margin-left: 5px; }
.ml-2 { margin-left: 8px; }
.text-gray { color: #909399; }
.text-xs { font-size: 12px; }
.flex-between {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
}
</style>
