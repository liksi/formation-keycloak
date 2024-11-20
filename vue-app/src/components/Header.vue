<template>
  <div class="header">
    <img src="../assets/keycloak_logo.png" />
    <h1>Keycloak Demo App</h1>
    <ul>
      <li>
        <a
                href="/"
        >
          Home
        </a>
      </li>
      <li>
        <a
                @click=account() style="cursor: pointer;"
        >
          My account
        </a>
      </li>
      <li>
        <a
                @click=logout() style="cursor: pointer;"
        >
          Log out
        </a>
      </li>
    </ul>
  </div>
</template>

<script>
import { logout as keycloakLogout, gotoAccount } from '../keycloak'

export default {
  name: 'HeaderComponent',

  methods: {
    logout () {
      keycloakLogout()
    },
    account () {
      gotoAccount()
    }
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
  template {
    margin-top: 0px;
    padding-top: 0px;
  }

  .header {
    height: 50px;
    background-color: #42b983;
    color: antiquewhite;
    padding-right: 20px;
    display: flex;
    align-items: center;
    margin-bottom: 30px;
  }

  img {
    padding: 5px;
    max-height: 80%;
    height: auto;
  }

  h1, h2 {
    display: inline;
    font-weight: normal;
  }

  ul {
    list-style-type: none;
    padding: 0;
    margin-left: auto;
  }

  li {
    text-align: right;
    display: inline-block;
    margin-left: 10px;
  }

  a {
    text-decoration: none;
    color: antiquewhite;
  }
  a:hover {
    color: #2c3e50;
  }
</style>
