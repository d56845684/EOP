<template>
  <el-form :model="addForm" :rules="addRules" ref="addFormRef" label-width="120px" label-position="top">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-form-item :label="$t('common.status')" prop="is_active">
            <el-switch v-model="addForm.is_active" :active-text="$t('common.active')" :inactive-text="$t('common.inactive')" inline-prompt />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col :span="12">
        <el-form-item :label="$t('common.name')" prop="name">
          <el-input v-model="addForm.name" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item :label="$t('common.engName')" prop="eng_name">
          <el-input v-model="addForm.eng_name" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col :span="12">
        <el-form-item :label="$t('student.idNumber')" prop="id_number">
            <el-input v-model="addForm.id_number" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item :label="$t('common.birthday')" prop="birth_date">
            <el-date-picker 
                v-model="addForm.birth_date" 
                type="date" 
                value-format="YYYY-MM-DD" 
            />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col :span="12">
        <el-form-item :label="$t('common.phone')" prop="phone">
            <el-input v-model="addForm.phone" />
        </el-form-item>
      </el-col>
      <el-col :span="12">
        <el-form-item :label="$t('student.googleDriveFolderId')" prop="google_drive_folder_id">
            <el-input v-model="addForm.google_drive_folder_id" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col :span="16">
        <el-form-item :label="$t('common.email')" prop="email">
            <el-input v-model="addForm.email" />
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
        <el-button round type="primary" @click="handleCreateStudent" :loading="saving" v-permission="'students.create'">
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
  import { useI18n } from 'vue-i18n';

  const props = defineProps({
    saving: {
      type: Boolean,
      required: true
    }
  })
  const { t } = useI18n();
  const addFormRef = ref<FormInstance>();
  const addForm = reactive<StudentCreate>({
    name: '',
    email: '',
    phone: '',
    address: '',
    birth_date: '',
    id_number: '',
    google_drive_folder_id: '',
    student_type: 'trial',
    is_active: true
  });

  const addRules = reactive<FormRules>({
    name: [{ required: true, message: t('studentAdmin.validation.nameRequired') }],
    eng_name: [{ required: true, message: t('studentAdmin.validation.engNameRequired') }],
    phone: [{ required: true, message: t('studentAdmin.validation.phoneRequired') }],
    email: [{ required: true, message: t('studentAdmin.validation.emailRequired'), type: 'email' }],
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

<style lang="scss" scoped></style>
