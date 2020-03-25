// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from 'vue'
import App from './App'
import router from './router'
import VueResource from 'vue-resource'
import { login, getAccessToken } from './keycloak.js'

Vue.config.productionTip = false
Vue.use(VueResource)

Vue.http.options.root = 'http://localhost:8090'

Vue.http.interceptors.push(function (request) {
  // modify headers
  request.headers.set('Authorization', 'Bearer ' + getAccessToken())
})

login().then(() => {
  /* eslint-disable no-new */
  new Vue({
    el: '#app',
    router,
    components: { App },
    template: '<App/>',
    http: {
      root: 'http://localhost:8090'
    }
  })
}, () => {})
