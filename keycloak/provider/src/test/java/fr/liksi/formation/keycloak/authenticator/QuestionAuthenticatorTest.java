package fr.liksi.formation.keycloak.authenticator;

import jakarta.ws.rs.core.MultivaluedHashMap;
import jakarta.ws.rs.core.MultivaluedMap;
import jakarta.ws.rs.core.Response;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.keycloak.authentication.AuthenticationFlowContext;
import org.keycloak.forms.login.LoginFormsProvider;
import org.keycloak.http.HttpRequest;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.UserModel;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class QuestionAuthenticatorTest {

    private final QuestionAuthenticator authenticator = new QuestionAuthenticator();

    @Mock
    private AuthenticationFlowContext context;

    @Mock
    private KeycloakSession session;

    @Mock
    private RealmModel realm;

    @Mock
    private UserModel user;

    @Mock
    private LoginFormsProvider loginFormsProvider;

    @Mock
    private HttpRequest httpRequest;

    @Mock
    private Response response;

    @Test
    void shouldRequireUser() {
        assertThat(authenticator.requiresUser()).isTrue();
    }

    @Test
    void shouldBeConfiguredForAllUsers() {
        assertThat(authenticator.configuredFor(session, realm, user)).isTrue();
    }

    @Test
    void shouldChallengeWithFormWhenUserHasQuestion() {
        when(context.getUser()).thenReturn(user);
        when(user.getFirstAttribute("question")).thenReturn("What is your pet name?");
        when(context.form()).thenReturn(loginFormsProvider);
        when(loginFormsProvider.createForm("question.ftl")).thenReturn(response);

        authenticator.authenticate(context);

        verify(loginFormsProvider).createForm("question.ftl");
        verify(context).challenge(response);
    }

    @Test
    void shouldCallSuccessOnAction() {
        MultivaluedMap<String, String> formData = new MultivaluedHashMap<>();
        formData.putSingle("answer", "fluffy");

        when(context.getHttpRequest()).thenReturn(httpRequest);
        when(httpRequest.getDecodedFormParameters()).thenReturn(formData);

        authenticator.action(context);

        verify(context).success();
    }

    @Test
    void shouldNotOverrideRequiredActions() {
        authenticator.setRequiredActions(session, realm, user);
        verifyNoInteractions(session);
    }
}
