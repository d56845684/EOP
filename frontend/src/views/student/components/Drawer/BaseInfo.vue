<template>
  <el-form
    :model="form" 
    :rules="rules"
    size="small"
    ref="formRef" 
    label-width="150px" 
    label-position="top" 
    class="my-4 mx-2"
  >
    <el-row :gutter="20">
      <el-col :span="10">
        <el-form-item 
          :label="$t('common.name')" 
          prop="name" 
        >
          <el-input v-model="form.name" class="w-full h-30px!" />
        </el-form-item>
      </el-col>
      <el-col :span="10">
        <el-form-item 
          :label="$t('common.engName')" 
          prop="eng_name" 
        >
          <el-input v-model="form.eng_name" class="w-full h-30px!" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col :span="10">
        <el-form-item 
          :label="$t('common.phone')" 
          prop="phone" 
        >
          <el-input v-model="form.phone" class="w-full h-30px!" />
        </el-form-item>
      </el-col>
      <el-col :span="10">
        <el-form-item 
          :label="$t('common.birthday')" 
          prop="birth_date" 
        >
          <el-date-picker 
            v-model="form.birth_date" 
            type="date" 
            value-format="YYYY-MM-DD" 
            class="w-245px! h-30px!"
          />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col :span="10">
        <el-form-item 
          :label="$t('student.idNumber')" 
          prop="id_number" 
          class="min-w-full"
        >
          <el-input v-model="form.id_number" class="w-full h-30px!" />
        </el-form-item>
      </el-col>
      <el-col :span="10">
        <el-form-item 
          :label="$t('student.googleDriveFolderId')" 
          prop="google_drive_folder_id" 
          class="min-w-full"
        >
          <el-input v-model="form.google_drive_folder_id" class="w-full h-30px!" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="10">
      <el-col :span="20">
        <el-form-item 
          :label="$t('common.email')" 
          prop="email" 
          class="min-w-full"
        >
          <el-input v-model="form.email" class="w-full h-30px!" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row>
      <el-col :span="24">
        <el-form-item 
          :label="$t('common.address')" 
          prop="address" 
          class="min-w-full"
        >
          <el-input v-model="form.address" class="w-full h-30px!" />
        </el-form-item>
      </el-col>
    </el-row>
    <el-row :gutter="10" class="mt-10px">
      <el-col :span="10">
        <el-form-item class="flex-1 min-w-full">
          <el-button 
            round 
            type="primary"
            size="small"
            class="py-3!"
            @click="handleSaveBasicInfo" 
            :loading="saving" 
            :disabled="!isFormDirty"
            v-permission="'students.edit'"
          >
            <template #icon>
              <div class="i-hugeicons:floppy-disk" />
            </template>
            {{ $t('common.save') }}
          </el-button>
        </el-form-item>
      </el-col>
    </el-row>
  </el-form>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import type { FormInstance } from 'element-plus';
  import { createFormSnapshot } from '@/utils/formDirty';

  const props = defineProps({
    form: {
      type: Object,
      required: true
    },
    rules: {
      type: Object,
      required: true
    },
    saving: {
      type: Boolean,
      required: true
    }
  });

  const formRef = ref<FormInstance>();
  const formSnapshot = ref('');
  const emit = defineEmits(['saveBasicInfo']);

  const getFormSnapshot = () => createFormSnapshot(props.form);
  const resetFormSnapshot = () => {
    formSnapshot.value = getFormSnapshot();
  };
  const isFormDirty = computed(() => getFormSnapshot() !== formSnapshot.value);

  const handleSaveBasicInfo = async () => {
    if (!formRef.value) return;
    await formRef.value.validate((valid) => {
      if (valid) {
        emit('saveBasicInfo');
        resetFormSnapshot();
      }
    });
  };

  watch(
    () => props.form,
    () => resetFormSnapshot(),
    { immediate: true, deep: false },
  );
</script>

<style lang="scss" scoped>

</style>
