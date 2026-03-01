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
          <template v-for="module in visibleModules" :key="module.id">
            
            <!-- Single Page Module (Category pretending to be page) OR Category with children -->
            <!-- Our structure is Level 1 (Category) -> Level 2 (Page) -->
            <!-- Logic: If Category has children, we check if we should show a sub-menu or flat item -->
            <!-- But user requirement says: Category -> Page. -->
            
            <!-- Special Case: Flatten Portals (Teacher/Student) -->
            <template v-if="['teacher_portal', 'student_portal'].includes(module.id)">
               <template v-for="page in module.children" :key="page.id">
                 <el-menu-item 
                   v-if="hasPagePermission(page)" 
                   :index="page.path || ''">
                    <!-- Inherit parent icon or use page icon if available -->
                    <el-icon v-if="page.icon || module.icon">
                        <component :is="page.icon || module.icon" />
                    </el-icon>
                    <span>{{ $t('menu.' + page.id, page.label) }}</span>
                 </el-menu-item>
               </template>
            </template>

            <!-- Case 1: Category usually has multiple pages (Setting -> Account, Role). -->
            <!-- Case 2: Category might map directly to a page if it's "flat" like Dashboard. -->
            
            <!-- Logic: Check module.children (Pages). -->
            <el-sub-menu v-else-if="module.children && module.children.length > 0 && !module.path" :index="module.id">
              <template #title>
                 <!-- Dynamic Icon -->
                <el-icon v-if="module.icon">
                    <component :is="module.icon" />
                </el-icon>
                <span>{{ $t('menu.' + module.id) }}</span>
              </template>
              
              <!-- Sub Items (Pages) -->
              <template v-for="page in module.children" :key="page.id">
                 <el-menu-item 
                   v-if="hasPagePermission(page)" 
                   :index="page.path || ''">
                    <span>{{ $t('menu.' + page.id, page.label) }}</span>
                 </el-menu-item>
              </template>
            </el-sub-menu>

            <!-- Case: Flat Module (Dashboard) where module itself acts as link ?? -->
            <!-- But our structure in mockStore has dashboard -> children[dashboard_page] -->
            <!-- So we should perhaps handle "Single Child" optimization OR just always iterate children. -->
            
            <!-- However, Dashboard usually doesn't need a dropdown. -->
            <!-- Let's check if the module has a path. If it has a path, it's a direct link. -->
            
            <el-menu-item v-else-if="module.path && hasAnyChildPermission(module)" :index="module.path">
                <el-icon v-if="module.icon">
                    <component :is="module.icon" />
                </el-icon>
                <span>{{ $t('menu.' + module.id) }}</span>
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
import { useMockStore, SYSTEM_MODULES, type SystemModule } from '../stores/mockStore';
import { useI18n } from 'vue-i18n';
import { ArrowDown } from '@element-plus/icons-vue';

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

const hasPermission = (permissionId: string) => {
    if (!currentUser.value) return false;
    // Remove super_admin bypass to enforce granular permissions for portals
    // if (currentUser.value.role === 'super_admin') return true;
    
    // Logic: A page (Level 2) is visible if `page_id:view` is in list.
    const viewPermission = `${permissionId}:view`;
    
    // Use copied permissions from Login
    const perms = currentUser.value.permissions || [];
    return perms.includes(viewPermission);
};

const hasPagePermission = (page: SystemModule) => {
   // Page is visible if user has 'view' permission for it
   // Page children are [View, Edit].
   // We check if `page.children` contains a 'view' node, and if user has it.
   // Or we strictly follow naming convention `page.id + ':view'`.
   
   // Let's use the convention for robustness as structure dictates.
   return hasPermission(page.id);
};

// Filter modules that should be visible
const visibleModules = computed(() => {
    return SYSTEM_MODULES.filter(module => {
        // Module is visible if ANY child page is visible
        if (module.children && module.children.length > 0) {
            return module.children.some(page => {
               // Check if page (Level 2) is visible
               // Page is visible if it has 'view' action permission
               return hasPagePermission(page);
            });
        }
        return false;
    });
});

const hasAnyChildPermission = (module: SystemModule) => {
    if (!module.children) return false;
    return module.children.some(page => hasPagePermission(page));
};


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
