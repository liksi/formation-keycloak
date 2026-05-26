package fr.liksi.formation.keycloak.requiredaction;

import jakarta.ws.rs.core.MultivaluedHashMap;
import jakarta.ws.rs.core.Response;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.keycloak.authentication.RequiredActionContext;
import org.keycloak.forms.login.LoginFormsProvider;
import org.keycloak.http.HttpRequest;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class UpdateQuestionActionTest {

    private final UpdateQuestionAction action = new UpdateQuestionAction();

    @Mock
    private RequiredActionContext context;

    @Mock
    private LoginFormsProvider loginFormsProvider;

    @Mock
    private HttpRequest httpRequest;

    @Mock
    private Response response;

    @Test
    void shouldChallengeWithQuestionForm() {
        when(context.form()).thenReturn(loginFormsProvider);
        when(loginFormsProvider.createForm("update-question.ftl")).thenReturn(response);

        action.requiredActionChallenge(context);

        verify(context).challenge(response);
    }

    @Test
    void shouldProcessActionAndCallSuccess() {
        var formData = new MultivaluedHashMap<String, String>();
        formData.putSingle("question", "What is your pet name?");
        formData.putSingle("answer", "fluffy");

        when(context.getHttpRequest()).thenReturn(httpRequest);
        when(httpRequest.getDecodedFormParameters()).thenReturn(formData);

        action.processAction(context);

        verify(context).success();
    }
}
