<template>
  <!-- Student Table -->
  <el-table :data="studentList" size="small" class="student-table w-full" v-loading="loading" stripe>
    <!-- Student No -->
    <el-table-column prop="student_no" :label="$t('student.studentNo')" min-width="100" />
    
    <!-- Name -->
    <el-table-column prop="name" :label="$t('common.name')" min-width="120">
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
            class="font-size-10px h-16px w-40px opacity-80"
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
          <div v-show="row.email" class="flex items-center gap-4px">
            <div class="i-hugeicons:mail-01 w-12px h-12px color-gray-500 flex-shrink-0" />
            <el-text class="text-xs" truncated>{{ row.email }}</el-text>
            <el-button type="text" size="small" round class="!px-1" @click="copyEmail(row.email)">
              <template #icon>
                <div class="i-hugeicons:copy-01" />
              </template>
            </el-button>
          </div>
          <div v-show="row.phone" class="flex items-center gap-4px">
            <div class="i-hugeicons:call-02 w-12px h-12px color-gray-500" />
            <el-text class="text-xs" truncated>{{ row.phone }}</el-text>
          </div>
        </div>
      </template>
    </el-table-column>

    <!-- Student Status -->
    <el-table-column prop="student_status" :label="$t('student.status')" width="80" align="center">
      <template #default="{ row }">
        <el-tag size="small" :type="STUDENT_STATUS_COLOR[row.student_status]" class="w-50px">
          {{ STUDENT_STATUS_LABEL[row.student_status] }}
        </el-tag>
      </template>
    </el-table-column>

    <el-table-column :label="$t('common.accountVerified')" width="90" align="center">
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
    <el-table-column :label="$t('common.actions')" label-class-name="text-center" width="240" fixed="right" class-name="action-column">
      <template #default="{ row }">
        <div>
          <el-button v-permission="'students.edit'" round size="small" @click="openDrawer(row, drawerTypeMap.MANAGE)">
            <template #icon>
              <div class="i-hugeicons:pencil-edit-01" />
            </template>
            {{ $t('student.detailsTitle') }}
          </el-button>
          <el-button 
            v-if="row.student_type === 'trial' && !row._contract_id"
            type="primary" 
            round
            size="small" 
            link
            @click="openConvertToFormalDialog(row)"
            v-permission="'students.contracts'"
          >
            轉正
          </el-button>
          <el-button
            v-if="row.student_type === 'formal'"
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
            合約
          </el-button>
        </div>
        <el-button 
          type="danger" 
          size="small"
          link
          @click="handleDelete(row)"
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
import { STUDENT_STATUS } from '@/constants/student'
import { usePermissionStore } from '@/stores/permission';

  const STUDENT_STATUS_LABEL: Record<string, string> = {
    [STUDENT_STATUS.ACTIVE]: '課程中',
    [STUDENT_STATUS.TERMINATED]: '解約',
    [STUDENT_STATUS.TRIAL]: '試上'
  };

  const STUDENT_STATUS_COLOR: Record<string, string> = {
    [STUDENT_STATUS.ACTIVE]: 'success',
    [STUDENT_STATUS.TERMINATED]: 'info',
    [STUDENT_STATUS.TRIAL]: 'warning'
  }

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