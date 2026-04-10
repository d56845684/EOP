<template>
  <el-dialog v-model="show" title="邀請連結" width="480px">
    <div>{{ ROLE_MAP[role] }}: {{ name }}({{ email }})</div>
    <el-form label-position="top" class="mt-4 mb-6">
      <el-form-item label="邀請連結" class="min-w-full mb-0">
        <el-row :gutter="10" class="min-w-full">
          <el-col :span="20">
            <el-input v-model="url" readonly />
            <div class="text-xs text-gray-400 mt-2 ml-1">此連結有效期為 7 天，僅可使用一次</div>
          </el-col>
          <el-col :span="4">
            <el-button type="primary" size="small" round class="h-30px!" @click="copyInviteUrl">
              <template #icon>
                <div class="i-hugeicons:copy-01" />
              </template>
              複製
            </el-button>
          </el-col>
        </el-row>
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="flex justify-center mb-2">
        <el-button round plain size="small" class="px-4! h-30px!" @click="show = false">
          <template #icon>
            <div class="i-hugeicons:cancel-circle-half-dot" />
          </template>
          關閉
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, type PropType } from 'vue';

const ROLE_MAP = {
  'student': '學生',
  'teacher': '教師',
  'admin': '管理員',
  'employee': '員工'
} as const

const props = defineProps({
  inviteVisible: {
    type: Boolean,
    required: true
  },
  role: {
    type: String as PropType<keyof typeof ROLE_MAP>,
    required: true
  },
  name: {
    type: String,
    required: true
  },
  email: {
    type: String,
    required: true
  },
  inviteUrl: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['update:inviteVisible'])

const show = computed({
  get: () => props.inviteVisible,
  set: (value: boolean) => {
    emit('update:inviteVisible', value)
  }
})

const url = computed(() => {
  return props.inviteUrl
})

const copyInviteUrl = () => {
  navigator.clipboard.writeText(props.inviteUrl)
  ElMessage.success('已複製邀請連結')
}
</script>
