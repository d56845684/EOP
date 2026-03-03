<template>
  <div class="course-list">
    <el-card>
      <template #header>
        <div class="header">
          <span>{{ $t('course.title') }}</span>
          <el-button type="primary" @click="openDrawer(null)">{{ $t('course.add') }}</el-button>
        </div>
      </template>
      
      <el-table :data="paginatedCourses" style="width: 100%">
        <el-table-column prop="name" :label="$t('common.name')" />
        <el-table-column prop="duration" :label="$t('course.duration')" />
        <el-table-column prop="price" :label="$t('course.price')" />
        <el-table-column :label="$t('common.actions')">
          <template #default="{ row }">
             <el-button link type="primary" @click="openDrawer(row)">{{ $t('common.edit') }}</el-button>
             <el-button link type="danger" @click="handleDelete(row)">{{ $t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-footer">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="courses.length"
          />
      </div>
    </el-card>

    <el-drawer v-model="drawerVisible" :title="form.id ? $t('course.editTitle') : $t('course.add')">
      <el-form :model="form" label-width="100px">
        <el-form-item :label="$t('common.name')">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item :label="$t('course.duration')">
          <el-input-number v-model="form.duration" :step="15" />
        </el-form-item>
        <el-form-item :label="$t('course.price')">
          <el-input-number v-model="form.price" :min="0" />
        </el-form-item>
        <el-form-item :label="$t('course.description')">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item :label="$t('course.cover')">
           <!-- Mock Upload -->
           <el-upload action="#" :auto-upload="false" :show-file-list="false">
              <el-button type="primary">{{ $t('course.upload') }}</el-button>
           </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="drawerVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSave">{{ $t('common.save') }}</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useMockStore, type Course } from '../../stores/mockStore';
import { ElMessage, ElMessageBox } from 'element-plus';

const store = useMockStore();
const courses = computed(() => store.courses);

// --- Pagination State ---
const currentPage = ref(1);
const pageSize = ref(10);
const paginatedCourses = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value;
    const end = start + pageSize.value;
    return courses.value.slice(start, end);
});
const drawerVisible = ref(false);
const form = ref<Course>({} as Course);

const openDrawer = (c: Course | null) => {
    if (c) form.value = { ...c };
    else form.value = { id: '', code: '', name: '', description: '', duration: 60, price: 500, cover: '' };
    drawerVisible.value = true;
};

const handleSave = () => {
    const idx = store.courses.findIndex(x => x.id === form.value.id);
    if (idx !== -1) store.courses[idx] = form.value;
    else {
        form.value.id = 'c' + Date.now();
        store.courses.push(form.value);
    }
    drawerVisible.value = false;
    ElMessage.success('Saved');
};

const handleDelete = (c: Course) => {
    ElMessageBox.confirm('Delete this course?', 'Warning', { type: 'warning' })
    .then(() => {
        store.courses = store.courses.filter(x => x.id !== c.id);
        ElMessage.success('Deleted');
    });
};
</script>

<style scoped>
.header { display: flex; justify-content: space-between; align-items: center; }
.pagination-footer { display: flex; justify-content: flex-end; margin-top: 20px; }
</style>
