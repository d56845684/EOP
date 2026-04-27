<script setup lang="ts">
import { computed } from 'vue';
import { ElConfigProvider } from 'element-plus';
import en from 'element-plus/es/locale/lang/en';
import zhTw from 'element-plus/es/locale/lang/zh-tw';
import { useI18n } from 'vue-i18n';

const { locale } = useI18n();

const elementLocale = computed(() => {
  if (locale.value === 'zh-TW') {
    return zhTw;
  }

  return en;
});
</script>

<template>
  <el-config-provider :locale="elementLocale">
    <router-view />
  </el-config-provider>
</template>

<style>
html,
body,
#app {
  height: 100%;
  margin: 0;
  padding: 0;
}
</style>
