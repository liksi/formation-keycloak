import Keycloak from 'keycloak-js'

let initOptions = {
  url: 'http://localhost:8099/auth', realm: 'formation', clientId: 'app', onLoad: 'login-required'
}

let keycloak = Keycloak(initOptions)

function scheduleRefresh () {
  setTimeout(() => {
    keycloak.updateToken(70).then((refreshed) => {
      if (refreshed) {
        console.log('Token refreshed' + refreshed)
      } else {
        console.log('Token not refreshed, valid for ' +
          Math.round(keycloak.tokenParsed.exp + keycloak.timeSkew - new Date().getTime() / 1000) + ' seconds')
      }
    }, () => {
      console.log('Failed to refresh token')
    })
  }, 60000)
}

function initKeycloak (res, rej) {
  keycloak.init({ onLoad: initOptions.onLoad }).then((auth) => {
    if (!auth) {
      window.location.reload()
    } else {
      console.log('Authenticated')
    }

    localStorage.setItem('vue-token', keycloak.token)
    localStorage.setItem('vue-refresh-token', keycloak.refreshToken)
    scheduleRefresh()
    res()
  },
  (error) => {
    console.log('Authenticated Failed ' + error)
    rej(error)
  })
}

function getUsername () {
  return keycloak.idTokenParsed['preferred_username']
}

function gotoAccount () {
  return keycloak.accountManagement()
}

function getRoles () {
  return keycloak.realmAccess.roles
}

function getAccessToken () {
  return keycloak.token
}

function logout () {
  keycloak.logout()
}

function login () {
  return new Promise((resolve, reject) =>
    initKeycloak(resolve, reject)
  )
}

export { logout, login, gotoAccount, getUsername, getAccessToken, getRoles }
