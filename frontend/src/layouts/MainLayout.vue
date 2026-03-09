<template>
  <el-container class="layout-container">
    <el-aside width="240px" class="aside">
      <div class="aside-top">
        <el-avatar :size="50" :src="currentUser?.avatar || ''" />
        <h3 class="nickname">{{ currentUser?.nickname }}</h3>
      </div>
      
      <el-scrollbar class="aside-menu">
        <el-menu
          router
          :default-active="$route.path"
          class="el-menu-vertical"
          :collapse="false"
        >
          <!-- Dynamic Menu Generation -->
          <template v-for="module in visibleModules" :key="String(module.name)">
            
            <el-sub-menu v-if="module.children && module.children.length > 0" :index="String(module.name)">
              <template #title>
                 <!-- Dynamic Icon -->
                <el-icon v-if="module.meta?.icon">
                    <component :is="module.meta.icon" />
                </el-icon>
                <span>{{ module.meta?.title || module.name }}</span>
              </template>
              
              <!-- Sub Items (Pages) -->
              <template v-for="page in module.children" :key="String(page.name)">
                 <el-menu-item :index="(module.path.startsWith('/') ? module.path : '/' + module.path) + '/' + page.path">
                    <el-icon v-if="page.meta?.icon || module.meta?.icon">
                        <component :is="page.meta?.icon || module.meta?.icon" />
                    </el-icon>
                    <span>{{ page.meta?.title || page.name }}</span>
                 </el-menu-item>
              </template>
            </el-sub-menu>

            <!-- Flat Module -->
            <el-menu-item v-else :index="module.path.startsWith('/') ? module.path : '/' + module.path">
                <el-icon v-if="module.meta?.icon">
                    <component :is="module.meta.icon" />
                </el-icon>
                <span>{{ module.meta?.title || module.name }}</span>
            </el-menu-item>
            
          </template>

        </el-menu>
      </el-scrollbar>

      <div class="aside-bottom">
        <el-dropdown trigger="click" @command="handleLanguageChange" class="lang-dropdown">
          <span class="el-dropdown-link">
             {{ $t('common.language') }}
            <el-icon class="el-icon--right"><arrow-down /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="en" :disabled="locale === 'en'">English</el-dropdown-item>
              <el-dropdown-item command="zh-TW" :disabled="locale === 'zh-TW'">繁體中文</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-button type="danger" plain class="logout-btn" @click="handleLogout">
          {{ $t('common.logout') }}
        </el-button>
      </div>
    </el-aside>

    <el-container>
      <el-header class="header">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ path: '/' }">{{ $t('common.home') }}</el-breadcrumb-item>
          <el-breadcrumb-item>{{ $t(getBreadcrumbLabel($route.name as string)) }}</el-breadcrumb-item>
        </el-breadcrumb>
      </el-header>

      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <!-- Keep Alive could go here -->
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
      
      <el-footer height="40px" class="footer">
        <span class="text-gray">© 2024 EOP System Prototype</span>
      </el-footer>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useMockStore } from '../stores/mockStore';
import { usePermissionStore } from '../stores/permission';
import { useI18n } from 'vue-i18n';
import { ArrowDown } from '@element-plus/icons-vue';

const permissionStore = usePermissionStore();

// i18n
const { locale } = useI18n();
const router = useRouter();

const routeKeyMap: Record<string, string> = {
  'Dashboard': 'dashboard',
  'Reports': 'reports',
  'Teachers': 'teachers',
  'Students': 'students',
  'Bookings': 'bookings',
  'Courses': 'courses',
  'Salary': 'salary',
  'AccountSettings': 'account_settings',
  'RoleSettings': 'role_settings',
  'ScheduleSettings': 'schedule_settings',
  'BookingHistory': 'booking_history',
  'TeacherProfile': 'teacher_profile',
  'ClassBooking': 'class_booking',
  'StudentProfile': 'student_profile'
};

const getBreadcrumbLabel = (routeName: string) => {
    // Safety check
    if (!routeName) return '';
    const key = routeKeyMap[routeName] || routeName.toLowerCase();
    const fullKey = `menu.${key}`;
    return fullKey;
};

const handleLanguageChange = (lang: string) => {
    locale.value = lang;
    localStorage.setItem('eop_locale', lang);
};

const store = useMockStore();
const currentUser = computed(() => store.currentUser);

// ... (No changes to permissions logic)

// Map string icon names to components
// const getIcon = (name: string) => {
//     return (Icons as any)[name] || Icons.Menu;
// };

// --- Permission Logic ---

// Filter modules that should be visible
const visibleModules = computed(() => {
    // Read directly from the filtered permission store routes
    return permissionStore.routes;
});


// Auto-logout
import { useIdle } from '@vueuse/core';
const { idle } = useIdle(10 * 60 * 1000); 

import { watch } from 'vue';
watch(idle, (isIdle) => {
  if (isIdle && store.currentUser) {
    handleLogout();
  }
});

const handleLogout = async () => {
    store.logout();
    router.push('/login');
};
</script>

<style scoped lang="scss">
.layout-container {
  height: 100vh;
}

.aside {
  background-color: var(--el-bg-color);
  border-right: 1px solid var(--el-border-color);
  display: flex;
  flex-direction: column;

  .aside-top {
    padding: 20px;
    text-align: center;
    border-bottom: 1px solid var(--el-border-color);
  }
  
  .aside-menu {
    flex: 1;
    .el-menu {
        border-right: none;
    }
  }

  .aside-bottom {
    padding: 20px;
    border-top: 1px solid var(--el-border-color);
    display: flex;
    flex-direction: column;
    gap: 15px;
    align-items: center;

    .lang-dropdown {
        cursor: pointer;
        display: flex;
        align-items: center;
        width: 100%;
        justify-content: center;
        
        .el-dropdown-link {
          display: flex;
          align-items: center;
          gap: 5px;
          color: var(--el-text-color-primary);
        }
    }
    
    .logout-btn {
        width: 100%;
    }
  }
}

.header {
  background-color: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.main-content {
  background-color: var(--el-bg-color-page);
  padding: 20px;
}

.footer {
    display: flex;
    align-items: center;
    justify-content: center;
    border-top: 1px solid var(--el-border-color);
    color: var(--el-text-color-secondary);
    font-size: 12px;
}
</style>
