<script setup lang="ts">
// Panel slide-in from right transition (200ms ease)
</script>

<template>
  <Transition name="slide-right" mode="out-in">
    <slot />
  </Transition>
</template>
