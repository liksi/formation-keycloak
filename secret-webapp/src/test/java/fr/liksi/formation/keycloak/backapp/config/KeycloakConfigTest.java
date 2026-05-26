package fr.liksi.formation.keycloak.backapp.config;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.security.oauth2.client.registration.ClientRegistrationRepository;
import org.springframework.test.context.TestPropertySource;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@TestPropertySource(properties = {
        "authentication-mode=keycloak",
        "spring.security.oauth2.client.provider.keycloak.issuer-uri=http://localhost:8080/realms/test",
        "spring.security.oauth2.client.registration.keycloak.client-id=test-client",
        "spring.security.oauth2.client.registration.keycloak.client-secret=test-secret"
})
class KeycloakConfigTest {

    @Autowired(required = false)
    private KeycloakConfig keycloakConfig;

    @MockBean
    private ClientRegistrationRepository clientRegistrationRepository;

    @Test
    void keycloakConfigShouldBeLoaded() {
        assertThat(keycloakConfig).isNotNull();
    }
}
