<template>
  <div>
    <h1 v-bind:class="{ forbidden : !hasRole}">{{ kind }}</h1>
        <a
          @click="getGet"
        >
          Click to fetch {{ kind }} message
        </a>
    <p>{{ msg }}</p>

  </div>
</template>

<script>
import { getRoles } from '../keycloak'

export default {
  name: 'FetchBox',
  data () {
    return {
      msg: '',
      hasRole: getRoles().includes("ROLE_" + this.kind.toUpperCase())
    }
  },

  props: ['kind'],

  methods: {
    getGet () {
      // POST /someUrl
      this.$http.get('http://localhost:8091/messages/' + this.kind).then(res => {
        console.log('succeeded to call message API', res)
        this.msg = res.body.message
      },
      error => {
        console.log('Failed to call message API', error)
        this.msg = error.body.status + ' ' + error.body.error
      })
    }

  }

}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
div {
  min-width: 300px;
  margin: 10px 30px;
  padding-bottom: 30px;
  display: block;
  border: 2px solid #2c3e50;
}
h1, h2 {
  padding: 10px;
  margin-top: 0px;
  background-color: #2c3e50;
  color: antiquewhite;
  font-weight: normal;
}

h1.forbidden {
  text-decoration: line-through;
}

a {
  padding: 30px;
  color: #42b983;
}
  a:hover {
    text-decoration: underline;
  }
</style>
