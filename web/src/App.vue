<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

import Editor from '@/components/Editor.vue'
import Table from '@/components/Table.vue'
import CostCell from '@/components/CostCell.vue'
import { ArrowPathRoundedSquareIcon, Cog6ToothIcon } from '@heroicons/vue/24/solid'

import defaultConfig from '@/configs/default.json'

const config = ref(defaultConfig)
const headers = ref(['item.name', 'cost'])
const rows = ref([])
const disableRecomputeButton = ref(true)
const isLoading = ref(true)

watch(config, () => {
  disableRecomputeButton.value = false
})

async function recomputeCosts() {
  disableRecomputeButton.value = true
  isLoading.value = true
  try {
    let url = '/api/compute_costs'
    if (import.meta.env.DEV) {
      url = 'http://localhost:8000/api/compute_costs'
    }
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        config: config.value,
        iterations: 100,
      }),
    })
    if (response.ok) {
      rows.value = (await response.json()).costs
      isLoading.value = false
    }
  } catch (err) {
    isLoading.value = false
  }
}

onMounted(() => {
  recomputeCosts()
})

const qualityNames: any = {
  1: 'Common',
  2: 'Uncommon',
  3: 'Rare',
  4: 'Epic',
  5: 'Legendary',
}

function prettyItemName(item: any) {
  const title = item.name.replace(/-/gi, ' ').split(' ')
    .map((s: string) => s.charAt(0).toUpperCase() + s.substring(1))
    .join(' ');
  if (item.quality > 1) {
    return `${title} (${qualityNames[item.quality as number]})`
  }
  return title
}
</script>

<template>
  <div class="app-container">
    <div class="editor-container">
      <Editor v-model="config"></Editor>
      <button :disabled="disableRecomputeButton" @click="recomputeCosts"
        class="m-4 p-4 text-2xl font-semibold bg-blue-500 hover:bg-blue-400 disabled:bg-zinc-700 disabled:text-zinc-500">
        <ArrowPathRoundedSquareIcon class="size-10 inline" />
        Recompute
      </button>
    </div>
    <div class="table-container">
      <Table v-show="!isLoading" class="cost-table" v-model:fields="headers" v-model:items="rows" :align="{
        'item.name': 'left', 'cost': 'left'
      }" :title="{
        'item.name': 'Item'
      }">
        <template #item.name="{ item }">
          <td>{{ prettyItemName(item.item) }}</td>
        </template>
        <template #cost="{ item }">
          <td>
            <CostCell :cost="(item.cost as number)" :transformationCosts="(item.transformation_costs as any[])" />
          </td>
        </template>
      </Table>
      <div v-show="isLoading" class="block m-auto">
        <Cog6ToothIcon class="size-10 mx-auto mb-4 animate-spin" />
        <span class="text-2xl">Crunching the numbers...</span>
      </div>
    </div>
  </div>

</template>

<style>
.app-container {
  display: flex;
  width: 100%;
  height: 100%;
}

.editor-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

.editor-container .editor {
  flex: 1 1 auto;
  min-height: 0;
}

.editor-container button {
  flex: 0 0 auto;
  align-self: end;
}

.table-container {
  display: flex;
  width: 100%;
  height: 100%;
}

table.cost-table {
  display: flex;
  flex-flow: column;
  height: 100%;
  width: 100%;
}

table.cost-table thead {
  /* head takes the height it requires, and it's not scaled when table is resized */
  flex: 0 0 auto;
  width: calc(100% - 0.95em);
}

table.cost-table tbody {
  /* body takes all the remaining available space */
  flex: 1 1 auto;
  display: block;
  overflow-y: scroll;
}

table.cost-table tbody tr {
  width: 100%;
}

table.cost-table thead,
table.cost-table tbody tr {
  display: table;
  table-layout: fixed;
}
</style>
