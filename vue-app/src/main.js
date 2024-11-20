// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
/* eslint-disable */
import Vue from 'vue'
import App from './App'
import router from './router'
import VueResource from 'vue-resource'
import { login, getAccessToken } from './keycloak.js'

Vue.config.productionTip = false
Vue.use(VueResource)

let serverPath = 'http://localhost:8091'

//login().then(() => {
  /* eslint-disable no-new */
  new Vue({
    el: '#app',
    router,
    components: { App },
    template: '<App/>',
    http: {
      options: {
        root: serverPath
      },
      root: serverPath
    }
  })
//}, () => {})

// Vue.http.interceptors.push(function (request) {
//   request.headers.set('Authorization', 'Bearer ' + getAccessToken())
// })
