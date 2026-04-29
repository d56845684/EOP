<template>
  <!-- Student Table -->
  <el-table :data="studentList" size="small" class="student-table w-full" v-loading="loading" stripe>
    <!-- Student No -->
    <el-table-column prop="student_no" :label="$t('student.studentNo')" min-width="120" />
    
    <!-- Name -->
    <el-table-column prop="name" :label="$t('common.name')" min-width="220">
      <template #default="{ row }">
        <div class="flex items-center justify-between gap-2">
          <div class="flex flex-col">
            <span>{{ row.name }}</span>
            <span class="text-xs italic text-gray-500">{{ row.eng_name }}</span>
          </div>
          <el-tag 
            :type="row.student_type === 'formal' ? 'success' : 'info'" 
            :color="row.student_type === 'formal' ? '#d5f0e1' : '#dfe0f2'" 
            effect="dark" 
            size="small"
            class="font-size-10px h-16px w-40px mr-1 opacity-80"
            :style="{ 
              borderColor: row.student_type === 'formal'? '#91b5a1' : '#afb0c4' ,
              color: row.student_type === 'formal'? '#288a52' : '#707187' 
            }"
          >
            {{ row.student_type === 'formal' ? $t('student.type.formal') : $t('student.type.trial') }}
          </el-tag>
        </div>
      </template>
    </el-table-column>
    
    <!-- Email -->
    <el-table-column prop="email" :label="$t('common.contactInfo')" min-width="250">
      <template #default="{ row }">
        <div class="flex flex-col">
          <div v-show="row.email" class="flex items-center gap-6px">
            <div class="i-hugeicons:mail-01 w-12px h-12px color-gray-500 flex-shrink-0" />
            <el-text class="text-xs" truncated>{{ row.email }}</el-text>
            <el-button type="text" size="small" round class="!px-1" @click="copyEmail(row.email)">
              <template #icon>
                <div class="i-hugeicons:copy-01" />
              </template>
            </el-button>
          </div>
          <div v-show="row.phone" class="flex items-center gap-6px">
            <div class="i-hugeicons:call-02 w-12px h-12px color-gray-500" />
            <el-text class="text-xs" truncated>{{ row.phone }}</el-text>
          </div>
        </div>
      </template>
    </el-table-column>

    <!-- Student Status -->
    <el-table-column prop="student_status" :label="$t('student.status')" min-width="110" align="center">
      <template #default="{ row }">
        <el-tag size="small" :type="STUDENT_STATUS_TAG_MAP[row.student_status]" class="w-50px min-w-max">
          {{ formatStudentStatusLabel(row.student_status, row.student_status, t) }}
        </el-tag>
      </template>
    </el-table-column>

    <el-table-column :label="$t('common.accountVerified')" min-width="110" align="center">
        <template #default="{ row }">
        <template v-if="row.email_verified_at">
          <el-tag size="small" type="success" effect='plain'>
            <div class="flex items-center gap-2px">
              <div class="i-hugeicons:checkmark-badge-01 w-14px h-14px" />
              <span>{{ $t('common.verified') }}</span>
            </div>
          </el-tag>
        </template>
        <template v-else>
          <el-button type="text" size="small" round @click="handleVerify(row)">
            {{ $t('common.verify') }}
          </el-button>
        </template>
        </template>
    </el-table-column>

    <!-- Actions -->
    <el-table-column :label="$t('common.actions')" label-class-name="text-center" min-width="260" fixed="right" class-name="action-column">
      <template #default="{ row }">
        <div class="min-w-max">
          <el-button v-permission="'students.edit'" round size="small" @click="openDrawer(row, drawerTypeMap.MANAGE)">
            <template #icon>
              <div class="i-hugeicons:pencil-edit-01" />
            </template>
            {{ $t('student.detailsTitle') }}
          </el-button>
          <el-button 
            v-if="row.student_status === 'trial' && row.active_contracts === 0"
            type="primary" 
            round
            size="small" 
            link
            @click="openConvertToFormalDialog(row)"
            v-permission="'students.contracts'"
          >
            {{ $t('student.convertToFormal') }}
          </el-button>
          <el-button
            v-else
            v-permission="'students.contracts'"
            round
            size="small"
            plain
            color="#82aa57"
            @click="openDrawer(row, TAB_MAP.CONTRACT)"
          >
            <template #icon>
              <div class="i-hugeicons:legal-document-02" />
            </template>
            {{ $t('contract.contracts') }}
          </el-button>
        </div>
        <el-button 
          type="danger" 
          size="small"
          link
          @click="handleDelete(row)"
          class="ml-1"
          v-permission="'students.delete'"
        >
          <div class="i-hugeicons:delete-02 mr-2px" />
          {{ $t('common.delete') }}
        </el-button>
      </template>
    </el-table-column>

    <!-- Status -->
    <el-table-column :label="$t('common.status')" width="80" align="center" fixed="right">
        <template #default="{ row }">
        <template v-if="hasPermission('students.edit')">
          <el-switch v-model="row.is_active" size="small" @change="handleStatusChange(row)" />
        </template>
        <template v-else>
          <el-tag size="small" :type="row.is_active ? 'success' : 'info'" effect='plain' class="w-50px">
            {{ row.is_active ? $t('common.active') : $t('common.inactive') }}
          </el-tag>
        </template>
        </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { StudentResponse } from '@/api/student'
import { STUDENT_STATUS_TAG_MAP } from '@/constants/display';
import { usePermissionStore } from '@/stores/permission';
import { formatStudentStatusLabel } from '@/utils/i18n-formatters';
import { useI18n } from 'vue-i18n';

  const TAB_MAP = {
    BASIC: 'basic',
    RECORDS: 'records',
    CONTRACT: 'contract',
  } as const;

  const DRAWER_TYPE_MAP = {
    CREATE: 'create',
    MANAGE: 'manage',
    CONTRACT: 'contract',
  } as const;

  const drawerTypeMap = DRAWER_TYPE_MAP;

  const props = defineProps({
    studentList: {
      type: Array,
      required: true,
    },
    loading: {
      type: Boolean,
      required: true,
    },
  })

  const permissionStore = usePermissionStore();
  const { t } = useI18n();
  const hasPermission = (permission: string) => permissionStore.hasPermission(permission);
  const emit = defineEmits(['openDrawer', 'openConvertToFormalDialog', 'handleDelete', 'handleStatusChange', 'handleVerify', 'copyEmail'])
  const openDrawer = (student: StudentResponse, type: string) => {
    emit('openDrawer', student, type)
  }
  const openConvertToFormalDialog = (student: StudentResponse) => {
    emit('openConvertToFormalDialog', student)
  }
  const handleDelete = (student: StudentResponse) => {
    emit('handleDelete', student)
  }
  const handleStatusChange = (student: StudentResponse) => {
    emit('handleStatusChange', student)
  }
  const handleVerify = (student: StudentResponse) => {
    emit('handleVerify', student)
  }
  const copyEmail = (email: string) => {
    emit('copyEmail', email)
  }
</script>

<style lang="scss" scoped>
.student-table.el-table {
  :deep(.text-center) {
    text-align: center;
    justify-content: center;
    .cell {
      text-align: center !important;
      justify-content: center !important;
    }
  }
  :deep(.action-column) {
    .cell {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }
}
</style>
