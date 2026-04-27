<template>
  <div class="permission-tree-editor h-full flex flex-col" v-loading="loading">
    <div class="flex-1 min-h-0 overflow-y-auto pr-2">
      <el-tree
        v-if="treeData.length"
        ref="treeRef"
        size="small"
        :data="treeData"
        show-checkbox
        node-key="id"
        :props="treeProps"
        default-expand-all
        :expand-on-click-node="false"
      />
      <el-empty v-else-if="!loading" :description="$t('permissionEditor.empty')" />
    </div>

    <div class="mt-4 pt-2 border-t flex justify-end gap-2">
      <el-button
        size="small"
        round
        class="h-30px! px-4!"
        @click="$emit('cancel')"
      >
        {{ $t('common.cancel') }}
      </el-button>
      <el-button
        size="small"
        round
        class="h-30px! px-4!"
        type="primary"
        :loading="saving"
        @click="handleSave"
      >
        {{ $t('common.save') }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import type { PageResponse } from '@/api/role';

interface TreeNode extends PageResponse {
  disabled?: boolean;
  children?: TreeNode[];
}

const props = withDefaults(defineProps<{
  pages: PageResponse[];
  checkedPageIds: string[];
  loading?: boolean;
  saving?: boolean;
  forcedPageKeys?: string[];
}>(), {
  pages: () => [],
  checkedPageIds: () => [],
  loading: false,
  saving: false,
  forcedPageKeys: () => ['dashboard'],
});

const emit = defineEmits<{
  (event: 'cancel'): void;
  (event: 'save', pageIds: string[]): void;
}>();

const treeRef = ref<any>(null);
const treeProps = {
  children: 'children',
  label: 'name',
};

const buildTree = (pages: PageResponse[], forcedPageKeys: string[]) => {
  const map = new Map<string, TreeNode>();
  const tree: TreeNode[] = [];
  const forcedIds: string[] = [];

  pages.forEach((page) => {
    map.set(page.key, { ...page, children: [] });
  });

  pages.forEach((page) => {
    const node = map.get(page.key);
    if (!node) return;

    if (forcedPageKeys.includes(node.key)) {
      node.disabled = true;
      forcedIds.push(node.id);
    }

    if (page.parent_key && map.has(page.parent_key)) {
      map.get(page.parent_key)!.children!.push(node);
    } else {
      tree.push(node);
    }
  });

  const sortNodes = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0) || a.key.localeCompare(b.key));
    nodes.forEach((node) => {
      if (node.children?.length) {
        sortNodes(node.children);
      } else {
        delete node.children;
      }
    });
  };

  sortNodes(tree);
  return { tree, forcedIds };
};

const treeResult = computed(() => buildTree(props.pages, props.forcedPageKeys));
const treeData = computed(() => treeResult.value.tree);
const forcedCheckedIds = computed(() => treeResult.value.forcedIds);
const parentKeys = computed(() => new Set(props.pages.map((page) => page.parent_key).filter(Boolean)));
const pageById = computed(() => new Map(props.pages.map((page) => [page.id, page])));

const syncedCheckedIds = computed(() => {
  const leafIds = props.checkedPageIds.filter((pageId) => {
    const page = pageById.value.get(pageId);
    return page ? !parentKeys.value.has(page.key) : true;
  });
  return Array.from(new Set([...forcedCheckedIds.value, ...leafIds]));
});

const syncCheckedKeys = async () => {
  await nextTick();
  window.setTimeout(() => {
    treeRef.value?.setCheckedKeys(syncedCheckedIds.value);
  }, 50);
};

watch(
  () => [props.pages, props.checkedPageIds, props.forcedPageKeys],
  () => {
    syncCheckedKeys();
  },
  { immediate: true, deep: true },
);

const handleSave = () => {
  if (!treeRef.value) {
    emit('save', forcedCheckedIds.value);
    return;
  }

  const checkedKeys = treeRef.value.getCheckedKeys() as string[];
  const halfCheckedKeys = treeRef.value.getHalfCheckedKeys() as string[];
  const pageIds = Array.from(new Set([...checkedKeys, ...halfCheckedKeys, ...forcedCheckedIds.value]));
  emit('save', pageIds);
};
</script>
