<template>
  <div>
    <h1> Hello {{ name }} !</h1>
    <div class="hello">
      <FetchBox kind="admin" />
      <FetchBox kind="user" />
    </div>
  </div>
</template>

<script>
import FetchBox from './FetchBox'
import { getUsername } from '../keycloak'

export default {
  name: 'ResourceProviderUi',
  components: { FetchBox },
  data () {
    return {
      name: getUsername()
    }
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
  h1 {
    text-align: left;
    margin-left: 30px;
  }

  div .hello{
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
  }
</style>
