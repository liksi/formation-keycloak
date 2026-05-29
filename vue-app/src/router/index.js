import { createRouter, createWebHistory } from 'vue-router'
import ResourceProviderUi from '@/components/ResourceProviderUi.vue'

const routes = [
  {
    path: '/',
    name: 'ResourceProviderUi',
    component: ResourceProviderUi
  }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
