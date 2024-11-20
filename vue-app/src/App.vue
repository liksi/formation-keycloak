<template>
  <div id="app">
    <Header />
    <router-view />
  </div>
</template>

<script>

export default {
  name: 'App',
}
</script>

<style>
  Header {
    margin-bottom: 30px;
  }
  #app {
    font-family: 'Avenir', Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-align: center;
    color: #2c3e50;
    margin-top: 0px;
    padding-top: 0px;
  }
  body {
    background-color: #f7f5f2;
    margin: 0px
  }
</style>
