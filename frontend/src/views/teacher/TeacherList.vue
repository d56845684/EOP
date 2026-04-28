<template>
  <div class="teacher-list-page pl-2 pr-4">
    <div class="flex justify-between items-center px-1 mb-2">
      <h3 class="my-0">{{ $t('teacher.title') }}</h3>
      <el-button
        v-if="hasPermission('teachers.create')"
        type="primary"
        round
        size="small"
        class="h-30px px-2"
        @click="openDetailDrawer(null)"
      >
        <template #icon>
          <div class="i-hugeicons:plus-sign-square" />
        </template>
        {{ $t('teacher.add') }}
      </el-button>
    </div>

    <el-card shadow="never" class="mb-14px">
      <el-form :inline="true" :model="queryParams" size="small" label-position="top" class="filter-form flex items-end">
        <el-form-item :label="$t('common.searchKeyword')" class="mb-0">
          <el-input 
            v-model="queryParams.search" 
            :placeholder="$t('teacher.searchPlaceholder')"
            clearable 
            @clear="fetchTeachersList" 
            @keyup.enter="fetchTeachersList"
            class="h-30px! w-260px!"
          >
            <template #prefix>
              <div class="i-hugeicons:search-01" />
            </template>
          </el-input>
        </el-form-item>
        <el-form-item :label="$t('common.status')" class="mb-0">
          <el-select v-model="queryParams.is_active" style="width: 120px" @change="fetchTeachersList">
            <el-option :label="$t('common.all')" value="all" />
            <el-option :label="$t('common.active')" :value="true" />
            <el-option :label="$t('common.inactive')" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item class="mb-0">
          <el-button type="primary" round size="small" class="py-3!" @click="fetchTeachersList">
            <template #icon>
              <div class="i-hugeicons:search-01" />
            </template>
            {{ $t('common.search') }}
          </el-button>
          <el-button round size="small" class="py-3!" @click="handleReset">
            <template #icon>
              <div class="i-hugeicons:arrow-reload-horizontal" />
            </template>
            {{ $t('common.btnReset') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div v-loading="loading">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="24" :md="24" :lg="12" :xl="12" v-for="teacher in teachersData" :key="teacher.id" class="mb-4">
          <el-card shadow="hover" class="h-full relative flex flex-col h-full card-bg">
            <el-descriptions :title="teacher.name" direction="vertical" :column="3" border size="small" class="flex-1">
              <template #extra>
                <el-switch 
                  v-model="teacher.is_active" 
                  inline-prompt
                  :active-text="$t('common.active')"
                  :inactive-text="$t('common.inactive')"
                  size="small"
                  :before-change="() => handleToggleStatus(teacher)"
                />
              </template>
              <el-descriptions-item
                :rowspan="2"
                :width="100"
                label=""
                align="center"
              >
                <el-image
                  fit="cover"
                  style="width: 100px; height: 100px"
                  :src="teacher?.avatar_url || ''"
                >
                  <template #error>
                    <div class="w-20 h-20 rounded-full bg-[#f3f4f8] flex items-center justify-center">
                      <div class="i-hugeicons:user text-3xl color-[#b5b5c3]" />
                    </div>
                  </template>
                </el-image>
              </el-descriptions-item>
              <el-descriptions-item :label="$t('teacher.teacherNo')">{{ teacher.teacher_no || '-' }}</el-descriptions-item>
              <el-descriptions-item :label="$t('teacher.level')" align="center" :width="120">
                <template #label>
                  <div class="flex items-center justify-center gap-1">
                    <div class="i-hugeicons:star-award-02 font-size-14px" />
                    {{ $t('teacher.level') }}
                  </div>
                </template>
                LV.{{ teacher.teacher_level }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('common.phone')">{{ teacher.phone || '-' }}</el-descriptions-item>
              <el-descriptions-item :label="$t('common.accountVerified')">
                <div class="flex items-center justify-center">
                  <el-button
                    v-if="!teacher.email_verified_at"
                    type="success"
                    plain
                    round
                    size="small"
                    @click="handleVerify(teacher)"
                  >
                    <div class="i-hugeicons:mail-validation-01 mr-2px" />
                    {{ $t('common.verify') }}
                  </el-button>
                  <div v-else class="flex items-center justify-center gap-1 color-success">
                    <div class="i-hugeicons:checkmark-badge-03" />
                    {{ $t('common.verified') }}
                  </div>
                </div>
              </el-descriptions-item>
              <el-descriptions-item label="Email" :span="3">
                <div class="text-wrap break-all">{{ teacher.email }}</div>
              </el-descriptions-item>
            </el-descriptions>
            <div class="flex justify-between mt-3 gap-2 px-2">
              <div class="left flex items-center gap-2">
                <el-button
                  v-permission="'teachers.contracts'"
                  :type="!teacher.total_contracts ? 'warning' : 'success'"
                  plain
                  round
                  size="small"
                  @click="openContractDrawer(teacher)"
                >
                  <template v-if="!teacher.total_contracts">
                    <div class="i-hugeicons:add-circle-half-dot mr-2px" />
                    {{ $t('contract.addContract') }}
                  </template>
                  <template v-else>
                    <div class="i-hugeicons:legal-document-02 mr-2px" />
                    {{ $t('contract.contracts') }}
                  </template>
                </el-button>
                <!-- <div 
                  v-if="teacher.total_contracts && !teacher.active_contracts" 
                  class="color-info text-10px flex items-center gap-1"
                >
                  <div class="i-hugeicons:alert-02" />
                  {{ $t('teacher.contractPending') }}
                </div> -->
              </div>
              <div class="right">
                <el-button v-permission="'teachers.details'" type="primary" plain round size="small" @click="openDetailDrawer(teacher)">
                  <template #icon v-if="hasPermission('teachers.edit')">
                    <div class="i-hugeicons:edit-02 mr-2px" />
                  </template>
                  <template #icon v-else>
                    <div class="i-hugeicons:view mr-2px" />
                  </template>
                  {{ $t('common.basicInfo') }}
                </el-button>
                <el-button 
                  v-permission="'teachers.delete'" 
                  type="danger" 
                  link 
                  size="small" 
                  @click="handleDelete(teacher)"
                >
                  <div class="i-hugeicons:delete-02 mr-2px" />
                  {{ $t('common.delete') }}
                </el-button>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <el-empty v-if="teachersData.length === 0" :description="$t('teacher.noTeachersFound')" />
    </div>

    <div class="flex justify-end mt-4">
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

    <!-- Inner Drawer Component -->
    <TeacherDetailDrawer 
      v-model="detailDrawerVisible" 
      :teacherId="selectedTeacherId" 
      @saved="fetchTeachersList" 
    />

    <TeacherContractDrawer 
      v-model="contractDrawerVisible"
      :teacherId="selectedTeacherId"
      @saved="fetchTeachersList" 
    />

    <!-- Verify Invite Dialog -->
    <VerifyInviteDialog
      v-model:inviteVisible="verifyInviteVisible"
      role="teacher"
      :name="currentVerifyTeacher?.name || ''"
      :email="currentVerifyTeacher?.email || ''"
      :inviteUrl="inviteUrl"
    />

    <!-- Add Teacher Dialog -->
    <el-dialog v-model="addDialogVisible" :title="$t('teacher.add')" width="500px" @closed="resetAddForm">
      <el-form ref="addFormRef" :model="addForm" :rules="addRules" label-width="120px">
        <el-form-item :label="$t('common.name')" prop="name">
          <el-input v-model="addForm.name" />
        </el-form-item>
        <el-form-item :label="$t('common.email')" prop="email">
          <el-input v-model="addForm.email" />
        </el-form-item>
        <el-form-item :label="$t('common.phone')" prop="phone">
          <el-input v-model="addForm.phone" />
        </el-form-item>
        <el-form-item :label="$t('common.address')" prop="address">
          <el-input v-model="addForm.phone" />
        </el-form-item>
        <el-form-item :label="'Teacher Level'" prop="teacher_level">
          <el-input-number v-model="addForm.teacher_level" :min="1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer flex justify-end">
          <el-button @click="addDialogVisible = false" round>{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" :loading="addingFile" @click="handleAdd" round>{{ $t('common.save') }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { getTeacherOverviewList, createTeacher, updateTeacher, deleteTeacher, type TeacherOverviewParams, type TeacherOverviewItem, type TeacherResponse, type TeacherCreate } from '@/api/teacher';
import TeacherDetailDrawer from './components/TeacherDetailDrawer.vue';
import TeacherContractDrawer from './components/TeacherContractDrawer.vue';
import VerifyInviteDialog from '@/components/Auth/VerifyInviteDialog.vue';
import { generateInviteLinkApi } from '@/api/auth';
import { usePermissionStore } from '@/stores/permission';
import { code } from '@/constants/code';
import { useI18n } from 'vue-i18n';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';

const permissionStore = usePermissionStore();
const hasPermission = (permission: string) => permissionStore.hasPermission(permission);

const { t } = useI18n();

const teachersData = ref<TeacherOverviewItem[]>([]);
const totalTeachers = ref(0);
const loading = ref(false);

const queryParams = reactive({
  page: 1,
  per_page: 20,
  search: '',
  is_active: 'all' as 'all' | boolean
});

const detailDrawerVisible = ref(false);
const contractDrawerVisible = ref(false);
const selectedTeacherId = ref<string | null>(null);

const verifyInviteVisible = ref(false);
const inviteUrl = ref('');
const currentVerifyTeacher = ref<TeacherResponse | null>(null);

const addDialogVisible = ref(false);
const addingFile = ref(false);
const addFormRef = ref<FormInstance>();
const addForm = reactive<TeacherCreate>({
  name: '',
  email: '',
  phone: '',
  teacher_level: 1,
  is_active: true
});

const addRules = reactive<FormRules>({
  name: [{ required: true, message: t('teacher.nameRequired'), trigger: 'blur' }],
  email: [{ required: true, message: t('teacher.emailRequired'), trigger: 'blur', type: 'email' }]
});

const fetchTeachersList = async () => {
  loading.value = true;
  try {
    const params: TeacherOverviewParams = {
      page: queryParams.page,
      per_page: queryParams.per_page,
      search: queryParams.search || undefined,
      is_active: queryParams.is_active === 'all' ? undefined : queryParams.is_active
    };
    const res = assertApiSuccess(await getTeacherOverviewList(params), t('teacher.loadFailed'));
    teachersData.value = res.data;
    totalTeachers.value = res.total;
  } catch (e: any) {
    ElMessage.error(getApiErrorMessage(e, t('common.fetchFailed')));
  } finally {
    loading.value = false;
  }
};

const handleReset = () => {
  queryParams.search = '';
  queryParams.is_active = 'all';
  queryParams.page = 1;
  fetchTeachersList();
};

onMounted(() => {
  fetchTeachersList();
});

const openDetailDrawer = (teacher: TeacherOverviewItem | null) => {
  selectedTeacherId.value = teacher?.id || null;
  detailDrawerVisible.value = true;
};

const openContractDrawer = (teacher: TeacherOverviewItem) => {
  selectedTeacherId.value = teacher.id;
  contractDrawerVisible.value = true;
};

const resetAddForm = () => {
  if (addFormRef.value) addFormRef.value.resetFields();
  addForm.name = '';
  addForm.email = '';
  addForm.phone = '';
  addForm.teacher_level = 1;
  addForm.is_active = true;
};

const handleAdd = async () => {
  if (!addFormRef.value) return;
  await addFormRef.value.validate(async (valid) => {
    if (valid) {
      addingFile.value = true;
      try {
        const res = assertApiSuccess(await createTeacher(addForm), t('teacher.createFailed'));
        ElMessage.success(res.message || t('common.addSuccess'));
        addDialogVisible.value = false;
        fetchTeachersList();
        // optionally open drawer for newly created teacher if API returned it:
        // if (res.data?.id) { selectedTeacherId.value = res.data.id; detailDrawerVisible.value = true; }
      } catch (e: any) {
        ElMessage.error(getApiErrorMessage(e, t('common.addFailed')));
      } finally {
        addingFile.value = false;
      }
    }
  });
};

const handleToggleStatus = (teacher: TeacherResponse): Promise<boolean> => {
  return new Promise((resolve, reject) => {
    ElMessageBox.confirm(teacher.is_active ? t('teacher.toggleDisableConfirm') : t('teacher.toggleEnableConfirm'), 'Warning', {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    }).then(async () => {
      try {
        const res = assertApiSuccess(await updateTeacher(teacher.id, { is_active: !teacher.is_active }), t('teacher.statusUpdateFailed'));
        ElMessage.success(res.message || t('common.updateSuccess'));
        resolve(true);
      } catch (e) {
        ElMessage.error(getApiErrorMessage(e, t('common.updateFailed')));
        reject(false);
      }
    }).catch(() => {
      reject(false);
    });
  });
};

const handleDelete = async (teacher: TeacherResponse) => {
  try {
    await ElMessageBox.confirm(t('teacher.deleteConfirm', { name: teacher.name }), 'Warning', {
      type: 'warning'
    });
    const res = assertApiSuccess(await deleteTeacher(teacher.id), t('teacher.deleteFailed'));
    ElMessage.success(res.message || t('common.deleteSuccess'));
    fetchTeachersList();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(getApiErrorMessage(e, t('common.deleteFailed')));
  }
};

const handleVerify = async (teacher: TeacherResponse) => {
  try {
    const res = await generateInviteLinkApi({ entity_type: 'teacher', entity_id: teacher.id });
    if (res.success === false && res.error_code === code.VALIDATION_ERROR) {
      ElMessage.error(t('teacher.duplicateEmail'));
      return;
    }
    inviteUrl.value = res.invite_url || '';
    currentVerifyTeacher.value = teacher;
    verifyInviteVisible.value = true;
  } catch (err: any) {
    // console.error(err);
    if (err.error_code === code.VALIDATION_ERROR) {
      ElMessage.error(t('teacher.duplicateEmail'));
      return;
    }
    ElMessage.error(t('common.operationFailed'));
  }
};
</script>

<style scoped>
:deep(.filter-form) {
  gap: 20px;
   .el-form-item {
     margin-right: 0;
     margin-bottom: 5px;
   }
}

.card-bg {
  background-color: #fff;
}
</style>
