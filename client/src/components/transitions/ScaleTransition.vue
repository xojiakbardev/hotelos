<script setup lang="ts">
// Dialog/modal scale + opacity transition (150ms ease-out)
</script>

<template>
  <Transition name="scale" mode="out-in">
    <slot />
  </Transition>
</template>
