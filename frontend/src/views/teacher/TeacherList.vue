<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { useMockStore, type RoleDef } from '../../stores/mockStore';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { Plus, Edit, CopyDocument, Document, Delete, UploadFilled } from '@element-plus/icons-vue';
import dayjs from 'dayjs';
import type { UploadFile } from 'element-plus';
import { getTeacherList, createTeacher, updateTeacher, type TeacherListParams, type TeacherCreate, type TeacherUpdate, type TeacherResponse } from '../../api/teacher';

const store = useMockStore();

// --- API State ---
const teachersData = ref<TeacherResponse[]>([]);
const totalTeachers = ref(0);
const loading = ref(false);

const queryParams = reactive({
    page: 1,
    per_page: 10,
    search: '',
    is_active: 'all' as 'all' | boolean
});

const fetchTeachersList = async () => {
    loading.value = true;
    try {
        const params: TeacherListParams = {
            page: queryParams.page,
            per_page: queryParams.per_page,
            search: queryParams.search || undefined,
            is_active: queryParams.is_active === 'all' ? undefined : queryParams.is_active
        };
        const res = await getTeacherList(params);
        if (res.success) {
            teachersData.value = res.data;
            totalTeachers.value = res.total;
        }
    } catch (e: any) {
        ElMessage.error(e.message || 'Failed to fetch teachers');
    } finally {
        loading.value = false;
    }
};

onMounted(() => {
    fetchTeachersList();
});

// --- State ---
const editDrawerVisible = ref(false);
const detailsDrawerVisible = ref(false);
const isAddMode = ref(false);

const activeEditTab = ref('basic');
const activeDetailsTab = ref('info');
const currentTeacherId = ref<string | null>(null);

const currentTeacher = computed(() => 
    teachersData.value.find(t => t.id === currentTeacherId.value)
);

// We need an extended interface for the UI state since API doesn't hold all these yet
interface TeacherUIState extends Omit<TeacherResponse, 'id' | 'teacher_no' | 'created_at' | 'updated_at' | 'email_verified_at'> {
    // These fields are only in UI for now, mocked until backend supports them
    id?: string;
    teacher_no?: string;
    contractType: 'Part-time' | 'Full-time';
    bonusMultiplier: number;
    salaryConfig: { hourlyRate?: number; courseRates?: any[]; baseSalary?: number; overtimeRate?: number };
    zoomLink: string;
    tags: string[];
    videoUrl: string;
    certs: string[];
    isCourseFeesEnabled: boolean;
    courseFees: { courseId: string; price: number }[];
    courseIds: string[];
    educationExperience: string;
    teachingSpecialty: string;
    introduction: string;
    description: string;
    status: boolean; // mapped from is_active
}

// Form Data (for Edit/Add)
const formRef = ref<FormInstance>();
// Default Form State
const getDefaultFormData = (): TeacherUIState => ({
    name: '',
    email: '',
    phone: '',
    address: '',
    bio: '',
    teacher_level: 1,
    is_active: true,
    status: true, // ui sync
    description: '',
    contractType: 'Part-time',
    bonusMultiplier: 1.0,
    salaryConfig: { hourlyRate: 0, courseRates: [], baseSalary: 0, overtimeRate: 0 },
    zoomLink: '',
    tags: [],
    videoUrl: '',
    certs: [],
    isCourseFeesEnabled: false,
    courseFees: [],
    courseIds: [],
    educationExperience: '',
    teachingSpecialty: '',
    introduction: ''
});

const formData = reactive<TeacherUIState>(getDefaultFormData());

// Rules
const rules = reactive<FormRules>({
    name: [{ required: true, message: 'Name is required' }],
    email: [{ required: true, message: 'Email is required', type: 'email' }],
    contractType: [{ required: true, message: 'Contract type required' }]
});

// --- Computed Logic for Teaching History (Substitute) ---
// --- Details State ---
const videoDialogVisible = ref(false);
const currentVideoUrl = ref('');
const historyFilters = reactive({
    status: 'All',
    isSubstitute: false,
    dateRange: [] as [string, string] | []
});

// --- Computed Logic for Teaching History (Substitute & Filtered) ---
const filteredTeachingHistory = computed(() => {
    if (!currentTeacherId.value) return [];
    
    let bookings = store.bookings.filter(b => b.teacherId === currentTeacherId.value);
    
    // Apply filters
    if (historyFilters.status !== 'All') {
        bookings = bookings.filter(b => b.status === historyFilters.status);
    }
    
    if (historyFilters.dateRange && historyFilters.dateRange.length === 2) {
        const [start, end] = historyFilters.dateRange;
        bookings = bookings.filter(b => dayjs(b.time).isAfter(dayjs(start).startOf('day')) && dayjs(b.time).isBefore(dayjs(end).endOf('day')));
    }

    return bookings.map(b => {
        const course = store.courses.find(c => c.id === b.courseId);
        const student = store.students.find(s => s.id === b.studentId);
        const courseName = course?.name || 'Unknown Course';
        const roleType = (course && course.defaultTeacherId && course.defaultTeacherId !== b.teacherId) ? 'Substitute' : 'Regular';
        
        // Filter by Substitute logic if checked
        if (historyFilters.isSubstitute && roleType !== 'Substitute') return null;

        return {
            id: b.id,
            date: dayjs(b.time).format('YYYY-MM-DD HH:mm'),
            courseName,
            studentName: student?.name || 'Unknown',
            duration: course?.duration || 60,
            status: b.status,
            type: b.type,
            role: roleType,
            note: '-'
        };
    }).filter(x => x !== null) // Remove filtered out items
      .sort((a,b) => b!.date.localeCompare(a!.date));
});

// Helper to get Course Names for Tags
const getCourseName = (id: string) => {
    const c = store.courses.find(x => x.id === id);
    return c ? `${c.code || ''} ${c.name}`.trim() : id;
};

// Actions
const openVideoModal = (url: string) => {
    if (!url) return;
    currentVideoUrl.value = url;
    videoDialogVisible.value = true;
};

const handleAdd = () => {
    isAddMode.value = true;
    currentTeacherId.value = null;
    resetForm();
    editDrawerVisible.value = true;
};

const handleEdit = (t: TeacherResponse) => {
    isAddMode.value = false;
    currentTeacherId.value = t.id;
    
    // 1. Reset Form first to clear old data
    resetForm();

    // 2. Clone basic API data to form, preserving mock complex data keys
    const dataOverrides = {
        id: t.id,
        teacher_no: t.teacher_no,
        name: t.name,
        email: t.email,
        phone: t.phone || '',
        address: t.address || '',
        bio: t.bio || '',
        teacher_level: t.teacher_level,
        is_active: t.is_active,
        status: t.is_active // map for UI
    };
    Object.assign(formData, dataOverrides);
    
    activeEditTab.value = 'basic';
    editDrawerVisible.value = true;
};

const handleDetails = (t: TeacherResponse) => {
    currentTeacherId.value = t.id;
    activeDetailsTab.value = 'info';
    detailsDrawerVisible.value = true;
};

const handleSave = async (formEl: FormInstance | undefined) => {
    if (!formEl) return;
    await formEl.validate(async (valid) => {
        if (valid) {
             if (formData.contractType === 'Part-time' && formData.isCourseFeesEnabled && formData.courseFees?.length === 0) {
                ElMessage.warning('Please add at least one course fee setting.');
                return;
            }
            try {
                if (isAddMode.value) {
                    const payload: TeacherCreate = {
                        teacher_no: formData.teacher_no || 'T-' + Date.now(), // Auto-gen if empty for now
                        name: formData.name,
                        email: formData.email,
                        phone: formData.phone,
                        address: formData.address,
                        bio: formData.bio || formData.introduction, // Use intro if bio is empty, since PRD separates them
                        teacher_level: formData.teacher_level,
                        is_active: formData.status
                    };
                    await createTeacher(payload);
                    ElMessage.success('Teacher added successfully');
                } else {
                    const payload: TeacherUpdate = {
                        name: formData.name,
                        email: formData.email,
                        phone: formData.phone,
                        address: formData.address,
                        bio: formData.bio || formData.introduction,
                        teacher_level: formData.teacher_level,
                        is_active: formData.status
                    };
                    if (currentTeacherId.value) {
                        await updateTeacher(currentTeacherId.value, payload);
                        ElMessage.success('Teacher updated successfully');
                    }
                }
                editDrawerVisible.value = false;
                fetchTeachersList();
            } catch (e: any) {
                ElMessage.error(e.message || 'Failed to save teacher');
            }
        }
    });
};

const handleToggleStatus = async (t: TeacherResponse, val: boolean) => {
    try {
        await ElMessageBox.confirm(
            '是否已確認上/下架該老師？ 上/下架後學生可/不可預約該老師課程。',
            'Warning',
            {
                confirmButtonText: 'Confirm',
                cancelButtonText: 'Cancel',
                type: 'warning',
            }
        );
        
        try {
            await updateTeacher(t.id, { is_active: val });
            ElMessage.success('Status updated successfully');
            fetchTeachersList();
        } catch (e: any) {
            ElMessage.error(e.message || 'Failed to update status');
            // Revert switch on failure
            t.is_active = !val;
        }

    } catch {
        // User cancelled, revert switch
        t.is_active = !val;
    }
};

const copyZoomLink = async (link: string) => {
    if (!link) return;
    try {
        await navigator.clipboard.writeText(link);
        ElMessage.success('Zoom link copied!');
    } catch (e) {
        ElMessage.error('Failed to copy');
    }
};

const addFeeRow = () => {
    if (!formData.courseFees) formData.courseFees = [];
    formData.courseFees.push({ courseId: '', price: 0 });
};

const removeFeeRow = (index: number) => {
    formData.courseFees?.splice(index, 1);
};

const handleVideoUpload = (file: UploadFile) => {
    if (file) {
        // Mock upload
        formData.videoUrl = URL.createObjectURL(file.raw!);
        ElMessage.success('Video uploaded (Mock)');
    }
};

const resetForm = () => {
    Object.assign(formData, getDefaultFormData());
};

// Reset on Close
watch(editDrawerVisible, (val) => {
    if (!val) {
        resetForm();
    }
});

</script>

<template>
  <div class="teacher-list-page">
     <div class="page-header">
        <h2>{{ $t('teacher.title') }}</h2>
        <el-button type="primary" :icon="Plus" @click="handleAdd">{{ $t('teacher.add') }}</el-button>
     </div>

     <!-- Search & Filter Area -->
     <el-card class="filter-card">
         <el-form :inline="true" :model="queryParams">
             <el-form-item label="Contract Type (合約類型)">
                 <el-select v-model="queryParams.is_active" style="width: 150px" @change="fetchTeachersList">
                     <el-option label="All" value="all" />
                     <el-option label="Active (Full-time/Part-time mock)" :value="true" />
                     <el-option label="Inactive" :value="false" />
                 </el-select>
             </el-form-item>
             <el-form-item label="Keyword Search (關鍵字搜尋)">
                 <el-input v-model="queryParams.search" placeholder="Name or Email" clearable @clear="fetchTeachersList" @keyup.enter="fetchTeachersList" />
             </el-form-item>
              <!-- Date range mock for now as API doesn't support join date filter -->
             <el-form-item label="Join Date (加入時間區間)">
                 <el-date-picker type="daterange" style="width: 250px" placeholder="Past 3 months (mock)" />
             </el-form-item>
             <el-form-item>
                 <el-button type="primary" @click="fetchTeachersList">搜尋 (Search)</el-button>
             </el-form-item>
         </el-form>
     </el-card>

     <!-- Main List -->
     <div class="teacher-cards" v-loading="loading">
        <el-card v-for="teacher in teachersData" :key="teacher.id" class="teacher-card" shadow="hover">
            <!-- Full Width Descriptions Grid -->
            <el-descriptions direction="vertical" :column="3" border class="teacher-desc">
                <template #extra>
                     <!-- Edit Button in Extra Slot -->
                    <el-button type="primary" link :icon="Edit" @click="handleEdit(teacher)">{{ $t('common.edit') }}</el-button>
                </template>

                <!-- Item 1: Avatar (Rowspan 2, Fixed Width) -->
                <el-descriptions-item :label="$t('account.avatar')" :rowspan="2" width="150px" align="center">
                    <el-avatar :size="80" shape="square" :src="teacher.avatar || ''" />
                </el-descriptions-item>

                <!-- Item 2: Basic Info (Name wrapping) -->
                <el-descriptions-item :label="$t('teacher.name') + '/' + $t('salary.contract')">
                    <div class="name-contract-row">
                        <span class="teacher-name">{{ teacher.name }}</span>
                        <!-- Mock contract type for now since real API doesn't have it -->
                        <el-tag size="small" type="warning">
                            Part-time
                        </el-tag>
                    </div>
                </el-descriptions-item>

                <!-- Item 3: Status (Fixed Width, Left Label / Center Content) -->
                <el-descriptions-item :label="$t('common.status')" width="120px" label-align="left" align="center">
                     <el-switch 
                        v-model="teacher.is_active" 
                        @change="(val: boolean) => handleToggleStatus(teacher, val)"
                     />
                </el-descriptions-item>

                <!-- Item 4: Course Tags (Full Row) -->
                <el-descriptions-item :label="$t('common.course')">
                    <div class="tags-group">
                        <span class="text-gray">No courses (API)</span>
                    </div>
                </el-descriptions-item>

                <!-- Item 5: Details Action (Fixed Width, Left Label / Center Content) -->
                <el-descriptions-item :label="$t('common.details')" width="120px" label-align="left" align="center">
                     <el-button link type="primary" @click="handleDetails(teacher)">{{ $t('common.viewDetails') }}</el-button>
                </el-descriptions-item>

                <!-- Item 6: Email -->
                <el-descriptions-item :label="$t('common.email')" :span="3">
                    {{ teacher.email }}
                </el-descriptions-item>

                <!-- Item 7: Zoom Link (Full Row) -->
                <!-- <el-descriptions-item :label="$t('teacher.zoomLink')" :span="3">
                    <div class="zoom-row">
                        <span class="link-text">No Link</span>
                    </div>
                </el-descriptions-item> -->
            </el-descriptions>
        </el-card>
     </div>
     
     <!-- Pagination -->
     <div class="pagination-footer">
        <el-pagination
            v-model:current-page="queryParams.page"
            v-model:page-size="queryParams.per_page"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="totalTeachers"
            @size-change="fetchTeachersList"
            @current-change="fetchTeachersList"
        />
     </div>

     <!-- Edit Drawer -->
     <el-drawer v-model="editDrawerVisible" :title="isAddMode ? $t('common.add') : $t('common.edit')" size="600px">
        <el-form ref="formRef" :model="formData" :rules="rules" label-width="150px" label-position="right">
            <el-tabs v-model="activeEditTab">
                <el-tab-pane :label="$t('common.basicInfo')" name="info">
                    <el-row :gutter="20">
                        <el-col :span="12">
                            <el-form-item :label="$t('common.name')" prop="name">
                                <el-input v-model="formData.name" />
                            </el-form-item>
                        </el-col>
                        <el-col :span="12">
                            <el-form-item :label="$t('common.phone')" prop="phone">
                                <el-input v-model="formData.phone" />
                            </el-form-item>
                        </el-col>
                    </el-row>
                    <el-form-item :label="$t('common.email')" prop="email">
                        <el-input v-model="formData.email" />
                    </el-form-item>
                    
                    <el-form-item :label="$t('teacher.contractType')" prop="contractType">
                        <el-radio-group v-model="formData.contractType">
                            <el-radio value="Full-time">Full-time</el-radio>
                            <el-radio value="Part-time">Part-time</el-radio>
                        </el-radio-group>
                    </el-form-item>

                    <!-- Dynamic Salary Fields -->
                    <div v-if="formData.contractType === 'Full-time'" class="salary-section">
                        <el-form-item :label="$t('salary.baseSalary')">
                            <el-input-number v-model="formData.salaryConfig.baseSalary" :min="0" style="width: 150px" />
                        </el-form-item>
                        <el-form-item :label="$t('salary.overtimeRate')">
                            <el-input-number v-model="formData.salaryConfig.overtimeRate" :min="0" style="width: 150px" />
                        </el-form-item>
                    </div>
                    <div v-else class="salary-section">
                        <el-form-item :label="$t('salary.hourlyRate')">
                            <el-input-number v-model="formData.salaryConfig.hourlyRate" :min="0" style="width: 150px" />
                        </el-form-item>
                        
                        <!-- Course Fee Settings -->
                        <el-form-item :label="$t('teacher.courseFeeSettings')">
                            <el-switch v-model="formData.isCourseFeesEnabled" /> 
                        </el-form-item>

                        <div v-if="formData.isCourseFeesEnabled" class="course-fees-list">
                            <div v-for="(fee, index) in formData.courseFees" :key="index" class="fee-row">
                                 <el-select v-model="fee.courseId" :placeholder="$t('common.course')" style="width: 180px">
                                     <el-option v-for="c in store.courses" :key="c.id" :label="c.name" :value="c.id" />
                                 </el-select>
                                 <el-input-number v-model="fee.price" :min="0" style="width: 150px" controls-position="right" :placeholder="$t('course.price')" />
                                 <el-button link type="danger" :icon="Delete" @click="removeFeeRow(index)" />
                            </div>
                            <div class="add-btn-row">
                                <el-button type="primary" link :icon="Plus" @click="addFeeRow">{{ $t('common.add') }}</el-button>
                            </div>
                        </div>
                    </div>

                    <el-form-item :label="$t('teacher.bonusMultiplier')">
                        <el-input-number v-model="formData.bonusMultiplier" :step="0.1" :min="1.0" style="width: 150px" />
                    </el-form-item>
                    
                    <el-form-item :label="$t('teacher.zoomLink')">
                        <el-input v-model="formData.zoomLink" placeholder="https://zoom.us/..." />
                    </el-form-item>
                    
                    <el-form-item :label="$t('teacher.teachingCourses')">
                        <el-select v-model="formData.courseIds" multiple filterable :placeholder="$t('common.course')">
                           <el-option v-for="c in store.courses" :key="c.id" :label="`${c.code || c.id} - ${c.name}`" :value="c.id" />
                        </el-select>
                    </el-form-item>
                </el-tab-pane>

                <el-tab-pane label="Resume/Bio" name="resume">
                     <el-form-item :label="$t('teacher.educationExperience')">
                         <el-input type="textarea" v-model="formData.educationExperience" :rows="3" />
                     </el-form-item>

                     <el-form-item :label="$t('teacher.teachingSpecialty')">
                         <el-input type="textarea" v-model="formData.teachingSpecialty" :rows="3" />
                     </el-form-item>

                     <el-form-item :label="$t('teacher.introduction')">
                         <el-input type="textarea" v-model="formData.introduction" :rows="4" />
                     </el-form-item>

                     <el-form-item :label="$t('teacher.introVideoLabel')">
                         <!-- Upload mimics video file selection -->
                         <el-upload
                            class="upload-demo"
                            drag
                            action="#"
                            accept=".mp4"
                            :auto-upload="false"
                            :show-file-list="false"
                            :on-change="handleVideoUpload"
                         >
                            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                            <div class="el-upload__text">
                                {{ $t('course.upload') }}
                            </div>
                         </el-upload>
                         <div v-if="formData.videoUrl" class="video-preview">
                             <p>Selected Video URL: {{ formData.videoUrl }}</p>
                             <video :src="formData.videoUrl" controls width="200"></video>
                         </div>
                     </el-form-item>
                     
                     <!-- Certs mock -->
                     <el-form-item :label="$t('teacher.certificates')">
                         <div class="mock-upload">
                             <el-button :icon="Plus" size="small">{{ $t('common.add') }}</el-button>
                             <div class="cert-list" v-if="formData.certs?.length">
                                 <el-tag v-for="c in formData.certs" :key="c">{{ c }}</el-tag>
                             </div>
                         </div>
                     </el-form-item>
                </el-tab-pane>
            </el-tabs>
        </el-form>
        <template #footer>
            <div style="flex: auto">
                <el-button @click="editDrawerVisible = false">{{ $t('common.cancel') }}</el-button>
                <el-button type="primary" @click="handleSave(formRef)">{{ $t('common.confirm') }}</el-button>
            </div>
        </template>
     </el-drawer>

     <!-- Details Drawer -->
      <el-drawer v-model="detailsDrawerVisible" :title="$t('common.viewDetails')" size="800px">
          <el-tabs v-model="activeDetailsTab" v-if="currentTeacher">
              <!-- Tab 1: Basic Info -->
              <el-tab-pane :label="$t('student.basicInfo')" name="info">
                  <el-descriptions border :column="1">
                      <el-descriptions-item :label="$t('teacher.name')">{{ currentTeacher.name }}</el-descriptions-item>
                      <el-descriptions-item :label="$t('common.status')">
                          <el-tag :type="currentTeacher.is_active ? 'success' : 'danger'">{{ currentTeacher.is_active ? 'On-Shelf' : 'Off-Shelf' }}</el-tag>
                      </el-descriptions-item>
                      <el-descriptions-item :label="$t('common.email')">{{ currentTeacher.email }}</el-descriptions-item>
                      <el-descriptions-item :label="$t('common.phone')">{{ currentTeacher.phone || '-' }}</el-descriptions-item>
                      <el-descriptions-item :label="$t('common.address')">{{ currentTeacher.address || '-' }}</el-descriptions-item>
                      <el-descriptions-item :label="'Level'">{{ currentTeacher.teacher_level }}</el-descriptions-item>
                      <el-descriptions-item :label="$t('teacher.joinDate')">{{ currentTeacher.created_at ? dayjs(currentTeacher.created_at).format('YYYY-MM-DD') : '-' }}</el-descriptions-item>
                      <el-descriptions-item :label="$t('common.lastUpdated')">{{ currentTeacher.updated_at ? dayjs(currentTeacher.updated_at).format('YYYY-MM-DD HH:mm') : '-' }}</el-descriptions-item>
                  </el-descriptions>
              </el-tab-pane>

              <!-- Tab 2: Resume -->
              <el-tab-pane label="Resume" name="resume">
                  <el-descriptions border :column="1">
                      <el-descriptions-item :label="$t('teacher.introduction')">
                          {{ currentTeacher.bio || '-' }}
                      </el-descriptions-item>
                  </el-descriptions>
              </el-tab-pane>

              <!-- Tab 3: Teaching History -->
              <el-tab-pane :label="$t('student.classRecords')" name="history">
                  <!-- Filters -->
                  <div class="history-filters">
                      <el-select v-model="historyFilters.status" :placeholder="$t('teacher.filter.status')" style="width: 120px">
                          <el-option label="All" value="All" />
                          <el-option label="Scheduled" value="Scheduled" />
                          <el-option label="Completed" value="Completed" />
                          <el-option label="Cancelled" value="Cancelled" />
                      </el-select>
                      <el-checkbox v-model="historyFilters.isSubstitute" :label="$t('teacher.filter.substitute')" border />
                      <el-date-picker 
                        v-model="historyFilters.dateRange" 
                        type="daterange" 
                        range-separator="To" 
                        :start-placeholder="$t('common.startDate')" 
                        :end-placeholder="$t('common.endDate')"
                        value-format="YYYY-MM-DD"
                        style="width: 240px"
                      />
                      <el-button type="primary" :icon="Document">{{ $t('common.export') }}</el-button>
                  </div>

                  <!-- Table -->
                  <el-table :data="filteredTeachingHistory" stripe border style="width: 100%; margin-top: 15px;">
                      <el-table-column prop="courseName" :label="$t('common.course')" width="150" show-overflow-tooltip>
                           <template #default="{ row }">
                               {{ row.courseName }}
                           </template>
                      </el-table-column>
                      <el-table-column prop="date" :label="$t('salary.dateTime')" width="160" />
                      <el-table-column prop="studentName" :label="$t('common.student')" width="120" />
                      <el-table-column prop="duration" :label="$t('course.duration')" width="120" />
                      <el-table-column prop="status" :label="$t('teacher.filter.status')" width="100">
                           <template #default="{ row }">
                               <el-tag :type="row.status === 'Completed' ? 'success' : row.status === 'Cancelled' ? 'info' : 'warning'">{{ row.status }}</el-tag>
                           </template>
                      </el-table-column>
                      <el-table-column prop="type" :label="$t('common.type')" width="80" />
                      <el-table-column :label="$t('teacher.filter.substitute')" width="100" align="center">
                          <template #default="{ row }">
                              <el-tag v-if="row.role === 'Substitute'" type="danger" effect="dark" size="small">Yes</el-tag>
                              <span v-else>-</span>
                          </template>
                      </el-table-column>
                      <el-table-column prop="note" :label="$t('common.note')" min-width="100" />
                  </el-table>
              </el-tab-pane>
          </el-tabs>
      </el-drawer>

      <!-- Video Dialog -->
      <el-dialog v-model="videoDialogVisible" title="Introduction Video" width="500px" append-to-body destroy-on-close>
          <div class="video-container">
              <video :src="currentVideoUrl" controls style="width: 100%;" autoplay></video>
          </div>
      </el-dialog>

  </div>
</template>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.teacher-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; }
.teacher-desc :deep(.el-descriptions__label) { font-weight: bold; background: #f5f7fa; }
.name-contract-row { display: flex; justify-content: space-between; align-items: center; }
.teacher-name { font-weight: bold; font-size: 1.1em; }
.tags-group { display: flex; flex-wrap: wrap; gap: 5px; }
.zoom-row { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.pagination-footer { display: flex; justify-content: flex-end; margin-top: 20px; }
.link-text {
    color: var(--el-color-primary);
    text-decoration: underline;
    font-size: 13px;
}

.text-gray {
    color: #909399;
}

.course-fees-list {
    margin-left: 20px; /* Indent slightly under label if needed, or just container */
    margin-bottom: 20px;
    padding: 10px;
    background-color: var(--el-fill-color-light);
    border-radius: 4px;
}

.fee-row {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 10px;
}

.add-btn-row {
    margin-top: 5px;
}

.filter-card {
    margin-bottom: 20px;
}

.history-filters {
    display: flex;
    gap: 15px;
    align-items: center;
    background-color: #f5f7fa;
    padding: 10px;
    border-radius: 4px;
    margin-bottom: 20px;
}

.video-thumbnail {
    display: flex;
    align-items: center;
    cursor: pointer;
    background-color: #f2f6fc;
    padding: 10px;
    border-radius: 4px;
    width: fit-content;
}
.video-preview {
    margin-top: 10px;
}

.cert-gallery {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.video-container {
    background: #000;
    line-height: 0;
}

</style>
