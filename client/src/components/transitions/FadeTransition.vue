<script setup lang="ts">
// Page content fade transition (150ms ease)
</script>

<template>
  <Transition name="fade" mode="out-in">
    <slot />
  </Transition>
</template>
