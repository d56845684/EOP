<template>
  <el-drawer v-model="show" :title="editUserId ? `${$t('common.edit')} - ${currentUser.name}` : `${$t('common.add')}${$t('account.account')}`">
    <el-form :model="form" :rules="rules" ref="formRef" label-position="top" label-width="140px" v-loading="submitting">
      <el-form-item label="暱稱" prop="name">
          <el-input v-model="form.name" />
      </el-form-item>
      
      <el-form-item label="Email帳號" prop="email">
          <el-input v-model="form.email" />
      </el-form-item>

      <el-form-item :label="$t('account.role')" prop="role_id">
          <el-select v-model="form.role_id" style="width: 100%;">
              <el-option 
                v-for="r in roles" 
                :key="r.key" 
                :label="r.name" 
                :value="r.id" 
              />
          </el-select>
      </el-form-item>
      
      <el-form-item label="員工類別" prop="employee_subtype">
          <el-input v-model="form.employee_subtype" />
      </el-form-item>

      <!-- <el-form-item :label="$t('common.status')" prop="is_active">
          <el-switch 
            v-model="form.is_active" 
            active-text="啟用" 
            inactive-text="停用" 
          />
      </el-form-item> -->

      <el-form-item>
        <el-button round @click="handleClose">{{ $t('common.cancel') }}</el-button>
        <el-button round type="primary" @click="handleSave" :loading="submitting">{{ $t('common.save') }}</el-button>
      </el-form-item>
    </el-form>
  </el-drawer>
</template>

<script setup lang="ts">
  import { ref, reactive, computed, watch, type PropType } from 'vue';
  import { ElMessage, type FormRules, type FormInstance } from 'element-plus';
  import { updateUserApi, type RoleInfo, type AccountInfo } from '@/api/user';

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
      type: Array as PropType<RoleInfo[]>,
      required: true
    },
    currentUser: {
      type: Object as PropType<AccountInfo>,
      required: true
    }
  });

  const form = ref({
    name: '',
    email: '',
    role_id: '',
    employee_subtype: '',
    is_active: false
  });

  const rules = reactive<FormRules>({
    role_id: [{ required: true, message: 'Role is required', trigger: 'change' }]
  });

  watch(() => props.currentUser, (newVal) => {
    console.log(newVal)
    if (newVal && newVal.id) {
      Object.keys(form.value).forEach((key: string) => {
        (form.value as Record<string, any>)[key] = newVal[key as keyof AccountInfo];
      });
    }
  }, { immediate: true, deep: true });
  
  const emit = defineEmits(['update:modelValue', 'fetch-users', 'clear-user']);

  const show = computed({
    get: () => props.modelValue,
    set: (value:boolean) => {
      emit('update:modelValue', value);
      emit('clear-user')
    }
  });

  const resetForm = (formEl: FormInstance | undefined) => {
    if (!formEl) return
    formEl.resetFields()
  }

  const handleClose = () => {
    resetForm(formRef.value)
    emit('update:modelValue', false);
    emit('clear-user')
  }

  const handleSave = async () => {
    if (!formRef.value) return;
    
    await formRef.value.validate(async (valid) => {
      if (valid) {
        submitting.value = true;
        try {
          await updateUserApi(props.editUserId, {
            role_id: form.value.role_id,
            employee_subtype: form.value.employee_subtype || null,
            is_active: form.value.is_active
          });
          ElMessage.success('更新成功');
          dialogVisible.value = false;
          emit('update:modelValue', false);
          emit('fetch-users');
          emit('clear-user')
        } catch (error) {
          ElMessage.error('更新失敗');
        } finally {
          submitting.value = false;
        }
      }
    });
  };
</script>

