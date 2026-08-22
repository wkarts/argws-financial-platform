<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import ControlDashboardPage from './ControlDashboardPage.vue'
import TenantDashboardPage from './TenantDashboardPage.vue'

const auth = useAuthStore()
const dashboardComponent = computed(() =>
  auth.isControlPlane ? ControlDashboardPage : TenantDashboardPage,
)
</script>

<template>
  <component :is="dashboardComponent" />
</template>
