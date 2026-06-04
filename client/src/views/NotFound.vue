<script setup lang="ts">
import { RouterLink } from 'vue-router'
import BlankLayout from '@/layouts/BlankLayout.vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
</script>

<template>
  <BlankLayout>
    <Card class="text-center p-12">
      <CardContent class="flex flex-col items-center gap-4 p-0">
        <h1 class="text-6xl font-bold tracking-tighter">404</h1>
        <p class="text-muted-foreground">Bu sahifa mavjud emas yoki o'chirilgan.</p>
        <RouterLink to="/">
          <Button>Bosh sahifaga qaytish</Button>
        </RouterLink>
      </CardContent>
    </Card>
  </BlankLayout>
</template>
