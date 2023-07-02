package fr.liksi.formation.keycloak.requiredaction;

import org.keycloak.authentication.RequiredActionContext;
import org.keycloak.authentication.RequiredActionProvider;
import org.keycloak.utils.StringUtil;

import javax.ws.rs.core.MultivaluedMap;

public class UpdateQuestionAction implements RequiredActionProvider {

    public static final String PROVIDER_ID = "update_question";

    @Override
    public void evaluateTriggers(RequiredActionContext context) {
        if (false) { // FIXME
            context.getUser().addRequiredAction(PROVIDER_ID);
        }
    }

    @Override
    public void requiredActionChallenge(RequiredActionContext context) {
        context.challenge(context.form().createForm("update-question.ftl"));
    }

    @Override
    public void processAction(RequiredActionContext context) {
        MultivaluedMap<String, String> formData = context.getHttpRequest().getDecodedFormParameters();

        String answer = null; // FIXME
        String question = null; // FIXME

        // FIXME - store answer and question in user attributes

        context.success();
    }

    @Override
    public void close() {

    }
}
