<script setup lang="ts">

import VTable from 'vtbl';
import { ForwardSlots } from "vue-forward-slots";
import { ref, watchEffect } from 'vue';

defineOptions({
  inheritAttrs: false
})

const fields = defineModel<string[]>('fields', {
  required: true,
})

const items = defineModel<any[]>('items', {
  required: true,
})

const orderBy = ref(['', 'asc'] as [string, 'asc' | 'desc']);

watchEffect(() => {
  if (orderBy.value[0] == '') {
    return
  }

  items.value.sort((a, b) => {
    const parts = orderBy.value[0].split('.')
    for (const part of parts) {
      if (a != null) {
        a = a[part]
      }
      if (b != null) {
        b = b[part]
      }
    }

    if (a == null && b == null) {
      return 0
    }

    if (a == null || b == null) {
      return a < b ? -1 : 1
    }

    if (typeof a === 'number') {
      return a - b
    }

    return a.localeCompare(b)
  })

  if (orderBy.value[1] == 'desc') {
    items.value.reverse()
  }
})
</script>

<template>
  <div class="p-4">
    <ForwardSlots :slots="$slots">
      <VTable :items="items" :orderable="fields" v-model:order-by="orderBy" :fields="fields" v-bind="$attrs" />
    </ForwardSlots>
  </div>
</template>

<style lang="postcss">
.v-table {
  @apply text-sm;
}

.v-table th {
  @apply p-2 bg-blue-500 text-white capitalize hover:cursor-pointer;
  text-align: left;
}

.v-table .orderable {
  background-repeat: no-repeat;
  background-position: center right;
  background-size: auto 50%;
}

.v-table .orderable.order-by {
  background-image: url('../assets/arrow-long-up.svg');
}

.v-table .orderable.order-by.desc {
  background-image: url('../assets/arrow-long-down.svg');
}

.v-table tr {
  @apply border-t bg-zinc-100 first-of-type:border-none;
}

.v-table tr:nth-child(even) {
  @apply bg-zinc-700/50;
}

.v-table tr:nth-child(odd) {
  @apply bg-zinc-700/25;
}

.v-table td {
  @apply p-2;
  @apply align-top;
}
</style>
