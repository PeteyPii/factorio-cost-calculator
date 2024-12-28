<script setup lang="ts">
import { ref } from 'vue'
// import { For} from 'for'
import { ChevronDownIcon } from '@heroicons/vue/24/solid'
import { ChevronUpIcon } from '@heroicons/vue/24/solid'

const props = defineProps<{
  cost: number | null,
  transformationCosts: any[]
}>()

const isExpanded = ref(false)
const isHovered = ref(false)

function prettifyCost(c: number | null) {
  if (c == null) {
    return ''
  }

  return c.toFixed(3);
}
</script>


<template>
  <div class="cost-cell hover:cursor-pointer" @mouseenter="isHovered = true" @mouseleave="isHovered = false"
    @click="isExpanded = !isExpanded">
    <span>{{ prettifyCost(props.cost) }}</span>
    <ChevronDownIcon v-show="isHovered && !isExpanded" class="float-right size-5" />
    <ChevronUpIcon v-show="isHovered && isExpanded" class="float-right size-5" />
    <ul v-show="isExpanded">
      <li v-for="transformationCost in props.transformationCosts">
        {{ transformationCost[0] }} - {{ prettifyCost(transformationCost[1]) }}
      </li>
    </ul>
  </div>
</template>

<style lang="postcss">
.cost-cell ul {
  list-style-type: disc;
  padding-left: 2em;
}

.cost-cell li {
  list-style-position: outside;
}
</style>
