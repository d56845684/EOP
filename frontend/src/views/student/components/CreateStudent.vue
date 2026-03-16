<template>
  <el-form :model="addForm" :rules="addRules" ref="addFormRef" label-width="120px" label-position="top">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-form-item label="學生編號" prop="student_no">
            <el-input v-model="addForm.student_no" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item label="狀態" prop="is_active">
            <el-switch v-model="addForm.is_active" active-text="啟用" inactive-text="停用" inline-prompt />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col :span="12">
        <el-form-item :label="$t('common.name')" prop="name">
          <el-input v-model="addForm.name" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col :span="12">
        <el-form-item :label="$t('common.email')" prop="email">
            <el-input v-model="addForm.email" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item :label="$t('common.phone')" prop="phone">
            <el-input v-model="addForm.phone" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col :span="12">
        <el-form-item label="生日" prop="birth_date">
            <el-date-picker 
                v-model="addForm.birth_date" 
                type="date" 
                value-format="YYYY-MM-DD" 
            />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item label="身份別" prop="student_type">
            <el-select v-model="addForm.student_type">
                <el-option label="正式生" value="formal" />
                <el-option label="試上生" value="trial" />
            </el-select>
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col :span="24">
        <el-form-item :label="$t('common.address')" prop="address">
            <el-input v-model="addForm.address" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-form-item>
        <el-button type="primary" @click="handleCreateStudent" :loading="saving" v-permission="'students.create'">
          <template #icon><div class="i-hugeicons:floppy-disk" /></template>
          {{ $t('common.save') }}
        </el-button>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
  import { reactive, ref } from 'vue';
  import { type StudentCreate } from '@/api/student';
  import { type FormInstance, type FormRules } from 'element-plus';

  const props = defineProps({
    saving: {
      type: Boolean,
      required: true
    }
  })
  const addFormRef = ref<FormInstance>();
  const addForm = reactive<StudentCreate>({
    student_no: '',
    name: '',
    email: '',
    phone: '',
    address: '',
    birth_date: '',
    student_type: 'formal',
    is_active: true
  });

  const addRules = reactive<FormRules>({
    student_no: [{ required: true, message: 'Student No is required' }],
    name: [{ required: true, message: 'Name is required' }],
    email: [{ required: true, message: 'Email is required', type: 'email' }],
    birth_date: [{ required: true, message: 'Birth Date is required' }],
  });

  const emit = defineEmits(['createStudent'])

  const handleCreateStudent = async () => {
    if (!addFormRef.value) return;
    await addFormRef.value.validate(async (valid) => {
      if (valid) {
        emit('createStudent', addForm as StudentCreate)
      }
    });
  }
</script>

<style lang="scss" scoped>

</style>