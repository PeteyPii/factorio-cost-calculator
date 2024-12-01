<script setup lang="ts">

import VTable from 'vtbl';

import { onMounted, ref } from 'vue';

const users = ref([]);
const orderBy = ref(['id', 'asc'] as [string, 'asc' | 'desc']);

onMounted(async () => {
    const response = await fetch('https://jsonplaceholder.typicode.com/users');

    users.value = await response.json();
    reorder();
});

function reorder() {
    if (orderBy.value[0] == 'id') {
        users.value.sort((a, b) => a[orderBy.value[0]] - b[orderBy.value[0]])
    } else {
        users.value.sort((a: any, b: any) => a[orderBy.value[0]].localeCompare(b[orderBy.value[0]]))
    }

    if (orderBy.value[1] == 'desc') {
        users.value.reverse();
    }
}
</script>

<template>
  <VTable :items="users" :orderable="['id', 'name', 'username']" v-model:order-by="orderBy" @update:orderBy="reorder" :fields="(['id', 'name', 'username'])" class="w-full"  />
</template>

<style lang="postcss">
.v-table {
    @apply text-sm;
}

.v-table th {
    @apply p-2 bg-blue-500 text-white capitalize;
}

.v-table tr {
    @apply border-t border-blue-100 first-of-type:border-none;
}

.v-table tr:nth-child(even) {
    @apply bg-blue-900/5;
}

.v-table td {
    @apply p-3;
}
</style>
