<template>
  <el-drawer v-model="show">
    <el-form :model="form" :rules="rules" ref="formRef" label-width="140px" v-loading="submitting">
      <el-form-item label="Name">
          <span>{{ form.name || '-' }}</span>
      </el-form-item>
      
      <el-form-item label="Email">
          <span>{{ form.email }}</span>
      </el-form-item>

      <el-form-item :label="$t('account.role')" prop="role_id">
          <el-select v-model="form.role_id" style="width: 100%;">
              <el-option 
                v-for="r in roles" 
                :key="r.id" 
                :label="r.name" 
                :value="r.id" 
              />
          </el-select>
      </el-form-item>
      
      <el-form-item label="Employee Subtype" prop="employee_subtype">
          <el-input v-model="form.employee_subtype" />
      </el-form-item>

      <el-form-item :label="$t('common.status')" prop="is_active">
          <el-switch 
            v-model="form.is_active" 
            active-text="啟用" 
            inactive-text="停用" 
          />
      </el-form-item>

      <el-form-item>
        <el-button @click="dialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSave" :loading="submitting">{{ $t('common.save') }}</el-button>
      </el-form-item>
    </el-form>
  </el-drawer>
</template>

<script setup lang="ts">
  import { ref, reactive, computed } from 'vue';
  import { ElMessage, type FormRules, type FormInstance } from 'element-plus';
  import { updateUserApi, type RoleInfo } from '@/api/user';

  const submitting = ref(false);
  const formRef = ref<FormInstance>();
  const dialogVisible = ref(false);

  const props = defineProps({
    editUserId: {
      type: String,
      required: true
    },
    modelValue: {
      type: Boolean,
      required: true
    },
    roles: {
      type: Array<RoleInfo>,
      required: true
    }
  });

  const show = computed({
    get: () => props.modelValue,
    set: (value:boolean) => {
      emit('update:modelValue', value);
    }
  });


  const rules = reactive<FormRules>({
    role_id: [{ required: true, message: 'Role is required', trigger: 'change' }]
  });
  
  const form = reactive({
    name: '',
    email: '',
    role_id: '',
    employee_subtype: '',
    is_active: false
  });

  const emit = defineEmits(['update:modelValue', 'fetch-users']);

  const handleSave = async () => {
    if (!formRef.value) return;
    
    await formRef.value.validate(async (valid) => {
      if (valid) {
        submitting.value = true;
        try {
          await updateUserApi(props.editUserId, {
            role_id: form.role_id,
            employee_subtype: form.employee_subtype || null,
            is_active: form.is_active
          });
          ElMessage.success('更新成功');
          dialogVisible.value = false;
          emit('update:modelValue', false);
          emit('fetch-users');
        } catch (error) {
          ElMessage.error('更新失敗');
        } finally {
          submitting.value = false;
        }
      }
    });
  };
</script>

