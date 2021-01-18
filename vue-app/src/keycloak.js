import Keycloak from 'keycloak-js'

let initOptions = {
  url: 'http://localhost:8099/auth', realm: 'formation', clientId: 'app', onLoad: 'login-required'
}

let keycloak = Keycloak(initOptions)

function initKeycloak (res, rej) {
  keycloak.init({ onLoad: initOptions.onLoad }).then((auth) => {
    if (!auth) {
      window.location.reload()
    } else {
      console.log('Authenticated')
    }
    //scheduleRefresh()
    res()
  },
  (error) => {
    console.log('Authenticated Failed ' + error)
    rej(error)
  })
}

// function scheduleRefresh () {
//   setInterval(() => {
//     keycloak.updateToken(30).then((refreshed) => {
//       if (refreshed) {
//         console.log('Token refreshed' + refreshed)
//       } else {
//         console.log('Token not refreshed, valid for ' +
//           Math.round(keycloak.tokenParsed.exp + keycloak.timeSkew - new Date().getTime() / 1000) + ' seconds')
//       }
//     }, () => {
//       console.log('Failed to refresh token')
//     })
//   }, 10000)
// }

function getUsername () {
  if (keycloak.idTokenParsed != null) {
    return keycloak.idTokenParsed['preferred_username']
  }
  return 'Anonymous'
}

function gotoAccount () {
  return keycloak.accountManagement()
}

function getRoles () {
  if(keycloak.realmAccess != null) {
    return keycloak.realmAccess.roles
  }
  return []
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
