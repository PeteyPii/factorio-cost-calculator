<script setup lang="ts">
import { ref, watchEffect } from 'vue'

import Editor from '@/components/Editor.vue'
import Table from '@/components/Table.vue'
import CostCell from '@/components/CostCell.vue'

import defaultConfig from '@/configs/default.json'

const config = ref(defaultConfig)
const headers = ['item.name', 'cost']
const rows = ref([])

watchEffect(async () => {
  try {
    const response = await fetch('http://localhost:8000/compute_costs', {
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
    }
  } catch (err) {
    // Do nothing
  }
})

function prettifyItemName(s: string) {
  return s.replace(/-/gi, ' ').split(' ')
    .map((s) => s.charAt(0).toUpperCase() + s.substring(1))
    .join(' ');
}

function prettifyCost(c: number | undefined) {
  if (c == null) {
    return ''
  }

  return c.toFixed(3);
}
</script>

<template>
  <div class="app-container">
    <div class="editor-container">
      <Editor v-model="config"></Editor>
    </div>
    <div class="table-container">
      <Table class="cost-table" v-model:fields="headers" v-model:items="rows" :align="{
        'item.name': 'left', 'cost': 'left'
      }" :title="{
        'item.name': 'Item'
      }">
        <template #item.name="{ item }">
          <td>{{ prettifyItemName(item.item.name) }}</td>
        </template>
        <template #cost="{ item }">
          <td>
            <CostCell :cost="(item.cost as number)" :transformationCosts="(item.transformation_costs as any[])" />
          </td>
        </template>
      </Table>
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
  width: 100%;
  height: 100%;
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
  width: calc(100% - 0.85em);
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
