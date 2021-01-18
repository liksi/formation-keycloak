import Vue from 'vue'
import Router from 'vue-router'
import ResourceProviderUi from '@/components/ResourceProviderUi'

Vue.use(Router)

export default new Router({
  routes: [
    {
      path: '/',
      name: 'ResourceProviderUi',
      component: ResourceProviderUi
    }
  ]
})
