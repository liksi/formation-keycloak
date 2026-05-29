package fr.liksi.formation.keycloak.mapper;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.keycloak.models.ClientSessionContext;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.ProtocolMapperModel;
import org.keycloak.models.UserModel;
import org.keycloak.models.UserSessionModel;
import org.keycloak.representations.IDToken;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;

@ExtendWith(MockitoExtension.class)
class AgeMapperTest {

    private final AgeMapper mapper = new AgeMapper();

    @Mock
    private IDToken token;

    @Mock
    private ProtocolMapperModel protocolMapperModel;

    @Mock
    private UserSessionModel userSession;

    @Mock
    private KeycloakSession keycloakSession;

    @Mock
    private ClientSessionContext clientSessionCtx;

    @Test
    void shouldHaveCorrectId() {
        assertThat(mapper.getId()).isEqualTo("AGE_MAPPER");
    }

    @Test
    void shouldHaveCorrectDisplayType() {
        assertThat(mapper.getDisplayType()).isEqualTo("Age Mapper");
    }

    @Test
    void shouldHaveCorrectHelpText() {
        assertThat(mapper.getHelpText()).isEqualTo("Adds isAdult flag");
    }

    @Test
    void shouldHaveConfigProperties() {
        assertThat(mapper.getConfigProperties()).isNotEmpty();
    }
}
