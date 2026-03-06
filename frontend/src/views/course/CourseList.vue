<template>
  <div class="course-list">
    <el-card>
      <template #header>
        <div class="header">
          <span>{{ $t('course.title') }}</span>
          <el-button type="primary" @click="openDrawer(null)">{{ $t('course.add') }}</el-button>
        </div>
      </template>
      
      <!-- Filter Section -->
      <div class="filter-container" style="margin-bottom: 20px;">
        <el-form :inline="true" :model="queryParams" @submit.prevent>
          <el-form-item>
            <el-input
              v-model="queryParams.search"
              :placeholder="$t('course.searchPlaceholder')"
              clearable
              @keyup.enter="handleSearch"
              style="width: 250px"
            />
          </el-form-item>
          <el-form-item :label="$t('course.labelStatus')">
            <el-select v-model="queryParams.is_active" style="width: 120px" @change="handleSearch">
              <el-option :label="$t('course.statusAll')" value="all" />
              <el-option :label="$t('course.statusActive')" :value="true" />
              <el-option :label="$t('course.statusInactive')" :value="false" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :icon="Search" @click="handleSearch">{{ $t('course.btnSearch') }}</el-button>
            <el-button :icon="Refresh" @click="handleReset">{{ $t('course.btnReset') }}</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table v-loading="loading" :data="tableData" style="width: 100%">
        <el-table-column prop="course_code" :label="$t('course.courseCode')" width="160px" />
        <el-table-column prop="course_name" :label="$t('course.courseName')" width="200px" />
        <el-table-column prop="description" :label="$t('course.description')" min-width="200px" />
        <el-table-column prop="duration_minutes" :label="$t('course.duration')" width="120px" align="center" />
        <el-table-column prop="is_active" :label="$t('common.active') + $t('common.status')" width="120px" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? 'Yes' : 'No' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')">
          <template #default="{ row }">
             <el-button link type="primary" @click="openDrawer(row)">{{ $t('common.edit') }}</el-button>
             <el-button link type="danger" @click="handleDelete(row)">{{ $t('common.delete') }}</el-button>
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
            @size-change="fetchData"
            @current-change="fetchData"
          />
      </div>
    </el-card>

    <el-drawer v-model="drawerVisible" :title="form.id ? $t('course.editTitle') : $t('course.add')">
      <el-form :model="form" label-width="120px">
        <el-form-item :label="$t('course.courseCode')">
          <el-input v-model="form.course_code" />
        </el-form-item>
        <el-form-item :label="$t('course.courseName')">
          <el-input v-model="form.course_name" />
        </el-form-item>
        <el-form-item :label="$t('course.duration')">
          <el-input-number v-model="form.duration_minutes" :step="5" />
        </el-form-item>
        <el-form-item :label="$t('course.description')">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item :label="$t('common.active')">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="drawerVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">{{ $t('common.save') }}</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { getCourseList, createCourse, updateCourse, deleteCourse, type CourseResponse } from '@/api/course';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Search, Refresh } from '@element-plus/icons-vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const loading = ref(false);
const tableData = ref<CourseResponse[]>([]);
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

const fetchData = async () => {
    loading.value = true;
    try {
        const apiParams: any = { ...queryParams };
        if (apiParams.is_active === 'all') {
            apiParams.is_active = undefined;
        }
        
        const res: any = await getCourseList(apiParams);
        const dataList = res;
        tableData.value = dataList.data || [];
        total.value = dataList.total || 0;
    } catch (error: any) {
        console.error(error);
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

const openDrawer = (c: CourseResponse | null) => {
    if (c) {
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
            await updateCourse(form.value.id, form.value);
        } else {
            await createCourse(form.value);
        }
        ElMessage.success(t('common.done') || 'Saved');
        drawerVisible.value = false;
        fetchData();
    } catch (error: any) {
        console.error(error);
    } finally {
        saving.value = false;
    }
};

const handleDelete = (c: CourseResponse) => {
    ElMessageBox.confirm(t('common.deleteConfirm') || 'Delete this course?', 'Warning', { type: 'warning' })
    .then(async () => {
        try {
            await deleteCourse(c.id);
            ElMessage.success(t('common.done') || 'Deleted');
            fetchData();
        } catch (error: any) {
            console.error(error);
        }
    }).catch(() => {});
};
</script>

<style scoped>
.header { display: flex; justify-content: space-between; align-items: center; }
.pagination-footer { display: flex; justify-content: flex-end; margin-top: 20px; }
</style>
