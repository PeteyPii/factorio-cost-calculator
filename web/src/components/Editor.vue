<script setup lang="ts">
import JsonEditorVue from 'json-editor-vue'
import { Mode } from 'vanilla-jsoneditor'
import { ref } from 'vue'
import 'vanilla-jsoneditor/themes/jse-theme-dark.css'

const value = ref('[{"foo": "bar"}]')

</script>

<template>
  <JsonEditorVue class="jse-theme-dark m-4 max-h-full" v-model="value" v-bind="{
    mainMenuBar: false,
    mode: Mode.text,
    statusBar: false,
    navigationBar: false,
    askToFormat: false,
    validator: null
  }" />
  <!-- <JsonEditorVue v-model="value" main-menu-bar="disabled" /> -->
</template>



<style lang="postcss">
.cm-gutters {
  display: none !important;
}

.jse-error {
  display: none !important;
}

div.jse-text-mode {
  @apply rounded-xl;
  /* border-radius: 0.75rem; */
  /* height: 100vh; */
}

div {
  --jse-main-border: 0;
  --jse-background-color: theme(colors.zinc.800);
}
</style>
