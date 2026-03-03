<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { useMockStore, type Teacher, type RoleDef } from '../../stores/mockStore';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { Plus, Edit, CopyDocument, Document, Delete, UploadFilled } from '@element-plus/icons-vue';
import dayjs from 'dayjs';
import type { UploadFile } from 'element-plus';

const store = useMockStore();

// --- State ---
const editDrawerVisible = ref(false);
const detailsDrawerVisible = ref(false);
const isAddMode = ref(false);

const activeEditTab = ref('basic');
const activeDetailsTab = ref('info');
const currentTeacherId = ref<string | null>(null);

const currentTeacher = computed(() => 
    store.teachers.find(t => t.id === currentTeacherId.value)
);

// --- Pagination State ---
const currentPage = ref(1);
const pageSize = ref(10);
const paginatedTeachers = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value;
    const end = start + pageSize.value;
    return store.teachers.slice(start, end);
});

// Form Data (for Edit/Add)
const formRef = ref<FormInstance>();
// Default Form State
const getDefaultFormData = (): Teacher => ({
    id: '',
    name: '',
    description: '',
    contractType: 'Part-time',
    bonusMultiplier: 1.0,
    salaryConfig: { hourlyRate: 0, courseRates: [], baseSalary: 0, overtimeRate: 0 },
    status: true,
    email: '',
    phone: '',
    zoomLink: '',
    tags: [],
    bio: '', 
    videoUrl: '',
    certs: [],
    avatar: '',
    isCourseFeesEnabled: false,
    courseFees: [],
    courseIds: [],
    educationExperience: '',
    teachingSpecialty: '',
    introduction: ''
});

// Form Data (for Edit/Add)
// const formRef = ref<FormInstance>();
const formData = reactive<Teacher>(getDefaultFormData());

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

// --- Actions ---

const handleAdd = () => {
    isAddMode.value = true;
    currentTeacherId.value = null;
    resetForm();
    editDrawerVisible.value = true;
};

const handleEdit = (t: Teacher) => {
    isAddMode.value = false;
    currentTeacherId.value = t.id;
    
    // 1. Reset Form first to clear old data
    resetForm();

    // 2. Clone data to form
    const data = JSON.parse(JSON.stringify(t));
    Object.assign(formData, data);
    
    // 3. Ensure structure exists (overwrites default empty if present in data, otherwise keeps default)
    if(!formData.salaryConfig) formData.salaryConfig = {};
    if(formData.isCourseFeesEnabled === undefined) formData.isCourseFeesEnabled = false;
    if(!formData.courseFees) formData.courseFees = [];
    if(!formData.courseIds) formData.courseIds = [];
    if(!formData.educationExperience) formData.educationExperience = '';
    if(!formData.teachingSpecialty) formData.teachingSpecialty = '';
    if(!formData.introduction) formData.introduction = formData.bio || ''; // Fallback to bio if intro missing
    
    activeEditTab.value = 'basic';
    editDrawerVisible.value = true;
};

const handleDetails = (t: Teacher) => {
    currentTeacherId.value = t.id;
    activeDetailsTab.value = 'info';
    detailsDrawerVisible.value = true;
};

const handleSave = async (formEl: FormInstance | undefined) => {
    if (!formEl) return;
    await formEl.validate(async (valid) => {
        if (valid) {
            // Basic validation for course fees
            if (formData.contractType === 'Part-time' && formData.isCourseFeesEnabled && formData.courseFees?.length === 0) {
                ElMessage.warning('Please add at least one course fee setting.');
                return;
            }
            await store.saveTeacher({ ...formData });
            editDrawerVisible.value = false;
            ElMessage.success('Teacher saved successfully');
        }
    });
};

const handleToggleStatus = async (t: Teacher, val: boolean) => {
    await store.toggleTeacherStatus(t.id, val);
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

     <!-- Main List -->
     <div class="teacher-cards">
        <el-card v-for="teacher in paginatedTeachers" :key="teacher.id" class="teacher-card" shadow="hover">
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
                        <el-tag size="small" :type="teacher.contractType === 'Full-time' ? 'success' : 'warning'">
                            {{ teacher.contractType }}
                        </el-tag>
                    </div>
                </el-descriptions-item>

                <!-- Item 3: Status (Fixed Width, Left Label / Center Content) -->
                <el-descriptions-item :label="$t('common.status')" width="120px" label-align="left" align="center">
                     <el-switch 
                        v-model="teacher.status" 
                        @change="(val: boolean) => handleToggleStatus(teacher, val)"
                     />
                </el-descriptions-item>

                <!-- Item 4: Email -->
                <el-descriptions-item :label="$t('common.email')">
                    {{ teacher.email }}
                </el-descriptions-item>

                <!-- Item 5: Details Action (Fixed Width, Left Label / Center Content) -->
                <el-descriptions-item :label="$t('common.details')" width="120px" label-align="left" align="center">
                     <el-button link type="primary" @click="handleDetails(teacher)">{{ $t('common.viewDetails') }}</el-button>
                </el-descriptions-item>

                <!-- Item 6: Course Tags (Full Row) -->
                <el-descriptions-item :label="$t('common.course')" :span="3">
                    <div class="tags-group">
                        <el-tag v-for="cid in teacher.courseIds" :key="cid" size="small" effect="plain">{{ getCourseName(cid) }}</el-tag>
                        <span v-if="!teacher.courseIds?.length" class="text-gray">No courses</span>
                    </div>
                </el-descriptions-item>

                <!-- Item 7: Zoom Link (Full Row) -->
                <el-descriptions-item :label="$t('teacher.zoomLink')" :span="3">
                    <div class="zoom-row">
                        <span class="link-text">{{ teacher.zoomLink || 'No Link' }}</span>
                        <el-button v-if="teacher.zoomLink" :icon="CopyDocument" circle size="small" @click="copyZoomLink(teacher.zoomLink)" />
                    </div>
                </el-descriptions-item>
            </el-descriptions>
        </el-card>
     </div>
     
     <!-- Pagination -->
     <div class="pagination-footer">
        <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="store.teachers.length"
        />
     </div>

     <!-- Edit Drawer -->
     <el-drawer v-model="editDrawerVisible" :title="isAddMode ? $t('teacher.add') : $t('teacher.edit')" size="600px">
        <el-form ref="formRef" :model="formData" :rules="rules" label-width="150px" label-position="right">
            <el-tabs v-model="activeEditTab">
                <el-tab-pane :label="$t('student.basicInfo')" name="basic">
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
                      <el-descriptions-item :label="$t('teacher.contractType')">
                          <el-tag :type="currentTeacher.contractType === 'Full-time' ? 'success' : 'warning'">{{ currentTeacher.contractType }}</el-tag>
                      </el-descriptions-item>
                      <el-descriptions-item :label="$t('common.status')">
                          <el-tag :type="currentTeacher.status ? 'success' : 'danger'">{{ currentTeacher.status ? 'On-Shelf' : 'Off-Shelf' }}</el-tag>
                      </el-descriptions-item>
                      <el-descriptions-item :label="$t('common.email')">{{ currentTeacher.email }}</el-descriptions-item>
                      <el-descriptions-item :label="$t('common.phone')">{{ currentTeacher.phone }}</el-descriptions-item>
                      <el-descriptions-item :label="$t('common.address')">台北市大安區信義路三段123號 (Mock)</el-descriptions-item>
                      <el-descriptions-item :label="$t('teacher.zoomId')">{{ currentTeacher.zoomLink ? '123-456-7890' : '-' }}</el-descriptions-item>
                      <el-descriptions-item :label="$t('teacher.zoomLink')">
                          <div class="zoom-row">
                              <span class="link-text">{{ currentTeacher.zoomLink || '-' }}</span>
                              <el-button v-if="currentTeacher.zoomLink" :icon="CopyDocument" link type="primary" size="small" @click="copyZoomLink(currentTeacher.zoomLink)">Copy</el-button>
                          </div>
                      </el-descriptions-item>
                      <el-descriptions-item :label="$t('teacher.teachingCourses')">
                          <div class="tags-group">
                              <el-tag v-for="cid in currentTeacher.courseIds" :key="cid" size="small">{{ getCourseName(cid) }}</el-tag>
                              <span v-if="!currentTeacher.courseIds?.length" class="text-gray">-</span>
                          </div>
                      </el-descriptions-item>
                      <el-descriptions-item :label="$t('teacher.joinDate')">2024-01-01 (Mock)</el-descriptions-item>
                      <el-descriptions-item :label="$t('common.lastUpdated')">2024-12-19 12:00 (Mock)</el-descriptions-item>
                  </el-descriptions>
              </el-tab-pane>

              <!-- Tab 2: Resume -->
              <el-tab-pane label="Resume" name="resume">
                  <el-descriptions border :column="1">
                      <el-descriptions-item :label="$t('teacher.educationExperience')">
                           <div style="white-space: pre-wrap;">{{ currentTeacher.educationExperience || '-' }}</div>
                      </el-descriptions-item>
                      <el-descriptions-item :label="$t('teacher.teachingSpecialty')">
                          {{ currentTeacher.teachingSpecialty || '-' }}
                      </el-descriptions-item>
                      <el-descriptions-item :label="$t('teacher.introduction')">
                          {{ currentTeacher.introduction || '-' }}
                      </el-descriptions-item>
                      <el-descriptions-item :label="$t('teacher.introVideo')">
                          <div v-if="currentTeacher.videoUrl" class="video-thumbnail" @click="openVideoModal(currentTeacher.videoUrl)">
                              <el-icon :size="40" color="#409EFF"><img v-if="false" /> <!-- Placeholder for thumbnail, using Icon for now -->
                                  <div class="play-icon-overlay"><component :is="UploadFilled" /></div> <!-- Reuse upload icon as play placeholder -->
                              </el-icon>
                              <span style="margin-left: 10px; color: #409EFF; cursor: pointer;">Click to Play Video</span>
                          </div>
                          <span v-else>No video uploaded.</span>
                      </el-descriptions-item>
                      <el-descriptions-item :label="$t('teacher.certificates')">
                          <div v-if="currentTeacher.certs && currentTeacher.certs.length" class="cert-gallery">
                               <!-- Mock Images for preview -->
                              <el-image 
                                v-for="(cert, idx) in currentTeacher.certs" 
                                :key="idx"
                                style="width: 100px; height: 100px; margin-right: 10px"
                                :src="'https://cube.elemecdn.com/6/94/4d3ea53c084bad6931a56d5158a48jpeg.jpeg'" 
                                :preview-src-list="['https://cube.elemecdn.com/6/94/4d3ea53c084bad6931a56d5158a48jpeg.jpeg']" 
                                fit="cover"
                              /> 
                              <!-- Note: Using mock elemecdn image since real certs are just filenames in store -->
                          </div>
                          <span v-else>-</span>
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

/* Details Drawer Styles */
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
