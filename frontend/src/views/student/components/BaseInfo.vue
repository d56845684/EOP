<template>
    <el-form :model="form" :rules="rules" ref="formRef" label-width="150px" label-position="top" class="flex flex-wrap justify-between gap-1 my-10px mx-5px">
    <el-form-item :label="$t('common.name')" prop="name" class="min-w-[calc(50%-8px)]">
        <el-input v-model="form.name" />
    </el-form-item>
    <el-form-item :label="$t('common.phone')" prop="phone" class="min-w-[calc(50%-8px)]">
        <el-input v-model="form.phone" />
    </el-form-item>
    <el-form-item :label="$t('common.email')" prop="email" class="flex-1 min-w-full">
        <el-input v-model="form.email" />
    </el-form-item>
    <el-form-item :label="$t('common.address')" prop="address" class="flex-1 min-w-full">
        <el-input v-model="form.address" />
    </el-form-item>
    <el-form-item :label="$t('common.birthday')" prop="birth_date" class="min-w-[calc(50%-8px)]">
        <el-date-picker 
            v-model="form.birth_date" 
            type="date" 
            value-format="YYYY-MM-DD" 
        />
    </el-form-item>
    <el-form-item class="flex-1 min-w-full">
        <el-button type="primary" @click="handleSaveBasicInfo" :loading="saving" v-permission="'students.edit'">
            {{ $t('common.save') }}
        </el-button>
    </el-form-item>
    </el-form>
</template>

<script setup lang="ts">
  import { ref } from 'vue';
  import type { FormInstance } from 'element-plus';

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
  const emit = defineEmits(['saveBasicInfo']);

  const handleSaveBasicInfo = async () => {
    if (!formRef.value) return;
    await formRef.value.validate((valid) => {
      if (valid) {
        emit('saveBasicInfo');
      }
    });
  };
</script>

<style lang="scss" scoped>

</style>