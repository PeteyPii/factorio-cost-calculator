<script setup lang="ts">
import JsonEditorVue from 'json-editor-vue'
import { Mode } from 'vanilla-jsoneditor'
import 'vanilla-jsoneditor/themes/jse-theme-dark.css'
</script>

<template>
  <JsonEditorVue class="jse-theme-dark p-4 h-full" v-bind="{
    mainMenuBar: true,
    mode: Mode.tree,
    statusBar: true,
    navigationBar: false,
    askToFormat: false,
    validator: null
  }" />
</template>

<style lang="postcss">
.jse-main,
.jse-modal {
  --jse-font-size-mono: 16px;
  --jse-main-border: 0;
  --jse-background-color: theme(colors.zinc.800);
  --jse-theme-color: theme(colors.blue.500)
}
</style>
