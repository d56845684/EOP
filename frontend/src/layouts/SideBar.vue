<template>
  <div class="aside w-200px  overflow-unset transition-all duration-300" :class="{ '!w-56px': isCollapse }">
    <div class="aside-header h-59px box-border relative flex items-center gap-2 pt-3.5 pb-1.2 px-3 transition-all duration-300">
      <el-image :src="logo" fit="contain" class="w-10 y-10 flex-shrink-0" />
      <div class="w-full text-size-4 line-height-5 font-bold color-[#073572] overflow-hidden transition-all duration-300" :class="{ '!w-0': isCollapse }">EOP<br>ENGLISH</div>
    </div>
    <div class="w-full flex justify-end items-center">
      <div class="w-[calc(100%-28px)] h-1px bg-[#E5E7EB]"></div>
      <el-button class="w-28px h-32px rounded-l-4 rounded-r-none border-r-0 !p-4px bg-[#f3f5fa]" @click="handleCollapse">
        <div v-if="isCollapse" class="i-hugeicons:arrow-right-02" />
        <div v-else class="i-hugeicons:arrow-left-02" />
      </el-button>
    </div>
    <div class="aside-menu w-full overflow-auto">
      <el-menu
        router
        :default-active="$route.path"
        class="el-menu-vertical border-none"
        :collapse="isCollapse"
      >
        <!-- Dynamic Menu Generation -->
        <template v-for="module in visibleModules" :key="String(module.name)">
          
          <el-sub-menu v-if="module.children && module.children.length > 0" :index="String(module.name)">
            <template #title>
                <!-- Dynamic Icon -->
              <el-icon v-if="module.meta?.icon">
                  <i :class="module.meta?.icon"></i>
              </el-icon>
              <span>{{ $t(getBreadcrumbLabel( module.name as string)) || module.meta?.title }}</span>
            </template>
            
            <!-- Sub Items (Pages) -->
            <template v-for="page in module.children" :key="String(page.name)">
                <el-menu-item :index="(module.path.startsWith('/') ? module.path : '/' + module.path) + '/' + page.path">
                  <el-icon v-if="page.meta?.icon">
                      <i :class="page.meta?.icon"></i>
                  </el-icon>
                  <span>{{ $t(getBreadcrumbLabel(page.name as string)) || page.meta?.title }}</span>
                </el-menu-item>
            </template>
          </el-sub-menu>

          <!-- Flat Module -->
          <el-menu-item v-else :index="module.path.startsWith('/') ? module.path : '/' + module.path">
              <el-icon v-if="module.meta?.icon">
                  <i :class="module.meta?.icon"></i>
              </el-icon>
              <span>{{ $t(getBreadcrumbLabel(module.name as string)) || module.meta?.title }}</span>
          </el-menu-item>
          
        </template>
      </el-menu>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
  import { usePermissionStore } from '@/stores/permission';
  import { getBreadcrumbLabel } from '@/utils/route';
  import logo from '@/assets/EOP-logo.png';

  const permissionStore = usePermissionStore();
  const isCollapse = ref(false);
  const userCollapsePreference = ref(false);
  const isAutoCollapsed = ref(false);
  const AUTO_COLLAPSE_SCREEN_RATIO = 0.7;

  const emit = defineEmits(['collapse']);

  const visibleModules = computed(() => {
    // Read directly from the filtered permission store routes
    return permissionStore.routes;
  });

  const handleCollapse = () => {
    const nextCollapseStatus = !isCollapse.value;
    isCollapse.value = nextCollapseStatus;
    userCollapsePreference.value = nextCollapseStatus;
    isAutoCollapsed.value = false;
    emit('collapse', isCollapse.value);
  };

  const updateCollapse = (status: boolean) => {
    if (isCollapse.value === status) return;
    isCollapse.value = status;
    emit('collapse', isCollapse.value);
  };

  const handleResize = () => {
    const shouldAutoCollapse = window.innerWidth < window.screen.width * AUTO_COLLAPSE_SCREEN_RATIO;

    if (shouldAutoCollapse) {
      isAutoCollapsed.value = true;
      updateCollapse(true);
      return;
    }

    if (isAutoCollapsed.value) {
      isAutoCollapsed.value = false;
      updateCollapse(userCollapsePreference.value);
    }
  };

  onMounted(() => {
    handleResize();
    window.addEventListener('resize', handleResize);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('resize', handleResize);
  });

</script>

<style scoped lang="scss">
.aside {
  background-color: var(--el-bg-color);
  border-right: 1px solid var(--el-border-color);
  display: flex;
  flex-direction: column;
  
  .aside-menu {
    flex: 1;
    :deep(.el-menu) {
      border-right: none;
      .el-menu-item {
        padding: 0 16px;
        gap: 5px;
      }
      .el-sub-menu {
        &__title {
          padding-left: 16px !important;
          gap: 5px;
        }
        .el-menu-item {
          padding-left: 32px; 
          gap: 5px;
        }
      }
    }
  }
}
</style>
