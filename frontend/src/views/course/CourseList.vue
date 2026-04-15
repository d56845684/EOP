<template>
  <div class="course-list pl-2 pr-4">
    <div class="flex justify-between items-center px-1 mb-2">
      <h3 class="my-0">{{ $t('menu.course_mgmt') }}</h3>
      <el-button
        v-if="hasPermission('courses.create')"
        type="primary"
        round
        size="small"
        class="h-30px px-2"
        @click="openDrawer(null, 'create')"
      >
        <template #icon>
          <div class="i-hugeicons:plus-sign-square" />
        </template>
        {{ $t('course.add') }}
      </el-button>
    </div>
    <el-card shadow="never">
      <!-- Filter Section -->
      <div class="filter-container" style="margin-bottom: 20px;">
        <el-form 
          :inline="true" 
          :model="queryParams" 
          label-position="top" 
          size="small"
          class="flex items-end"
          @submit.prevent
        >
          <el-form-item label="關鍵字搜尋">
            <el-input
              v-model="queryParams.search"
              :placeholder="$t('course.searchPlaceholder')"
              clearable
              @keyup.enter="handleSearch"
              class="h-30px! w-250px!"
            >
              <template #prefix>
                <div class="i-hugeicons:search-01" />
              </template>
            </el-input>
          </el-form-item>
          <el-form-item :label="$t('course.labelStatus')">
            <el-select v-model="queryParams.is_active" style="width: 120px" @change="handleSearch">
              <el-option :label="$t('course.statusAll')" value="all" />
              <el-option :label="$t('course.statusActive')" :value="true" />
              <el-option :label="$t('course.statusInactive')" :value="false" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" round class="h-30px!" @click="handleSearch">
              <template #icon>
                <div class="i-hugeicons:search-01" />
              </template>
              {{ $t('course.btnSearch') }}
            </el-button>
            <el-button round class="h-30px!" @click="handleReset">
              <template #icon>
                <div class="i-hugeicons:arrow-reload-horizontal" />
              </template>
              {{ $t('course.btnReset') }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table v-loading="loading" :data="tableData" size="small" class="w-full">
        <el-table-column prop="course_code" :label="$t('course.courseCode')" width="160px">
          <template #default="{ row }">
            <el-tag type="primary" size="small" class="text-11px">{{ row.course_code }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="course_name" :label="$t('course.courseName')" width="200px" />
        <el-table-column prop="description" :label="$t('course.description')" min-width="200px" />
        <el-table-column prop="duration_minutes" :label="$t('course.duration')" width="120px" align="center" />
        <el-table-column prop="is_active" :label="$t('common.active') + $t('common.status')" width="120px" align="center">
          <template #default="{ row }">
            <el-switch
              v-if="hasPermission('courses.edit')"
              v-model="row.is_active"
              size="small"
              :loading="statusChangingIds.has(row.id)"
              @change="handleStatusChange(row)"
            />
            <el-tag v-else :type="row.is_active ? 'success' : 'info'" size="small" effect="light" class="w-36px! text-10px text-center">{{ row.is_active ? '啟用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')" fixed="right" width="180px" align="center">
          <template #default="{ row }">
             <el-button type="primary" link size="small" @click="openDrawer(row, 'edit')">{{ $t('common.edit') }}</el-button>
             <el-button type="danger" link size="small" @click="handleDelete(row)">
              <div class="i-hugeicons:delete-02 mr-2px" />
              {{ $t('common.delete') }}
            </el-button>
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
            size="small"
            @size-change="fetchData"
            @current-change="fetchData"
          />
      </div>
    </el-card>

    <el-drawer v-model="drawerVisible" size="400px" :title="form.id ? $t('course.editTitle') : $t('course.add')">
      <el-form :model="form" size="small" label-position="top" label-width="120px">
        <el-row>
          <el-col :span="20">
            <el-form-item :label="$t('course.courseCode')">
              <el-input v-model="form.course_code" class="w-full! h-30px!" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="20">
            <el-form-item :label="$t('course.courseName')">
              <el-input v-model="form.course_name" class="w-full! h-30px!" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="10">
            <el-form-item :label="$t('course.duration')">
              <el-input-number v-model="form.duration_minutes" :step="5" class="w-full! h-30px!" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="10">
          <el-col :span="24">
            <el-form-item :label="$t('course.description')">
              <el-input v-model="form.description" type="textarea" :rows="4" class="w-full!" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button round size="small" class="px-5! h-30px!" @click="drawerVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" round size="small" class="px-5! h-30px!" :loading="saving" @click="handleSave">{{ $t('common.save') }}</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { getCourseList, createCourse, updateCourse, deleteCourse, type CourseResponse, type CourseResponseData } from '@/api/course';
import { assertApiSuccess, getApiErrorMessage } from '@/api/response';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { usePermissionStore } from '@/stores/permission';

const { t } = useI18n();

const permissionStore = usePermissionStore();
const hasPermission = (permission: string) => permissionStore.hasPermission(permission);

const loading = ref(false);
const tableData = ref<CourseResponseData[]>([]);
const total = ref(0);

const queryParams = reactive({
    page: 1,
    per_page: 20,
    search: '',
    is_active: 'all' as string | boolean | null | undefined
});

const drawerVisible = ref(false);
const form = ref<any>({});
const saving = ref(false);
const statusChangingIds = ref<Set<string>>(new Set());

const fetchData = async () => {
    loading.value = true;
    try {
        const apiParams: any = { ...queryParams };
        if (apiParams.is_active === 'all') {
            apiParams.is_active = undefined;
        }
        
        const dataList = assertApiSuccess(await getCourseList(apiParams), '載入課程列表失敗');
        tableData.value = dataList.data || [];
        total.value = dataList.total || 0;
    } catch (error: any) {
        console.error(error);
        ElMessage.error(getApiErrorMessage(error, '載入課程列表失敗'));
    } finally {
        loading.value = false;
    }
};

const handleSearch = () => {
    queryParams.page = 1;
    fetchData();
};

const handleReset = () => {
    queryParams.page = 1;
    queryParams.per_page = 20;
    queryParams.search = '';
    queryParams.is_active = 'all';
    fetchData();
};

onMounted(() => {
    fetchData();
});

const openDrawer = (c: CourseResponseData | null, type: string) => {
    if (type === 'edit' && c) {
        form.value = { ...c };
    } else {
        form.value = { 
            id: '', 
            course_code: '', 
            course_name: '', 
            description: '', 
            duration_minutes: 60, 
            is_active: true 
        };
    }
    drawerVisible.value = true;
};

const handleSave = async () => {
    saving.value = true;
    try {
        if (form.value.id) {
            const res = assertApiSuccess(await updateCourse(form.value.id, form.value), '更新課程失敗');
            ElMessage.success(res.message || t('common.done') || 'Saved');
        } else {
            const res = assertApiSuccess(await createCourse(form.value), '新增課程失敗');
            ElMessage.success(res.message || t('common.done') || 'Saved');
        }
        drawerVisible.value = false;
        fetchData();
    } catch (error: any) {
        console.error(error);
        ElMessage.error(getApiErrorMessage(error, '儲存課程失敗'));
    } finally {
        saving.value = false;
    }
};

const handleStatusChange = async (row: CourseResponseData) => {
  statusChangingIds.value = new Set([...statusChangingIds.value, row.id]);
  try {
    const res = assertApiSuccess(await updateCourse(row.id, { is_active: row.is_active }), '狀態更新失敗');
    ElMessage.success(res.message || t('common.updateSuccess'));
  } catch (error: any) {
    // Revert on failure
    row.is_active = !row.is_active;
    console.error(error);
    ElMessage.error(getApiErrorMessage(error, '狀態更新失敗'));
  } finally {
    const next = new Set(statusChangingIds.value);
    next.delete(row.id);
    statusChangingIds.value = next;
  }
};

const handleDelete = (c: CourseResponseData) => {
    ElMessageBox.confirm(t('common.deleteConfirm') || 'Delete this course?', 'Warning', { type: 'warning' })
    .then(async () => {
        try {
            const res = assertApiSuccess(await deleteCourse(c.id), '刪除課程失敗');
            ElMessage.success(res.message || t('common.done') || 'Deleted');
            fetchData();
        } catch (error: any) {
            console.error(error);
            ElMessage.error(getApiErrorMessage(error, '刪除課程失敗'));
        }
    }).catch(() => {});
};
</script>

<style scoped>
.header { display: flex; justify-content: space-between; align-items: center; }
.pagination-footer { display: flex; justify-content: flex-end; margin-top: 20px; }
</style>
