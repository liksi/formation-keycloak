<template>
  <div>
  <HeaderComponent/>
  <div>
    <h1> Hello {{ name }} !</h1>
    <div class="hello">
      <FetchBox kind="admin" />
      <FetchBox kind="user" />
    </div>
  </div>
  </div>
</template>

<script>
import FetchBox from './FetchBox'
import { getUsername } from '../keycloak'
import HeaderComponent from "@/components/HeaderComponent.vue";

export default {
  name: 'ResourceProviderUi',
  components: { FetchBox, HeaderComponent },
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
