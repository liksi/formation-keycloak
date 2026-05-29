import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { login, getAccessToken } from './keycloak.js'

const app = createApp(App)
app.use(router)

let serverPath = 'http://localhost:8091'

//login().then(() => {
  app.mount('#app')
//}, () => {})

// Vue.http.interceptors.push(function (request) {
//   request.headers.set('Authorization', 'Bearer ' + getAccessToken())
// })
