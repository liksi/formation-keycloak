package fr.liksi.formation.keycloak.authenticator;

import org.keycloak.authentication.AbstractFormAuthenticator;
import org.keycloak.authentication.AuthenticationFlowContext;
import org.keycloak.forms.login.LoginFormsProvider;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.UserModel;
import org.keycloak.utils.StringUtil;

import javax.ws.rs.core.MultivaluedMap;

public class QuestionAuthenticator extends AbstractFormAuthenticator {
    @Override
    public void authenticate(AuthenticationFlowContext context) {
        String question = context.getUser().getFirstAttribute("question");
        if (StringUtil.isBlank(question)) {
            // FIXME
        } else {
            LoginFormsProvider forms = context.form();
            // FIXME
            context.challenge(context.form().createForm("question.ftl"));
        }
    }

    @Override
    public void action(AuthenticationFlowContext context) {
        MultivaluedMap<String, String> formData = context.getHttpRequest().getDecodedFormParameters();
        String answer = formData.getFirst("answer"); // FIXME

        if (true) { // FIXME
            context.success();
        } else {
            LoginFormsProvider forms = context.form();
            forms.setError("Wrong answer");
            // FIXME
            context.challenge(forms.createForm("question.ftl"));
        }
    }

    @Override
    public boolean requiresUser() {
        return true;
    }

    @Override
    public boolean configuredFor(KeycloakSession keycloakSession, RealmModel realmModel, UserModel userModel) {
        return true;
    }

    @Override
    public void setRequiredActions(KeycloakSession keycloakSession, RealmModel realmModel, UserModel userModel) {

    }

}
