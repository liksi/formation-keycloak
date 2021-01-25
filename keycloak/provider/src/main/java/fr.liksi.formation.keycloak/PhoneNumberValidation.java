package fr.liksi.formation.keycloak;

import org.keycloak.Config;
import org.keycloak.authentication.FormAction;
import org.keycloak.authentication.FormActionFactory;
import org.keycloak.authentication.FormContext;
import org.keycloak.authentication.ValidationContext;
import org.keycloak.events.Details;
import org.keycloak.events.Errors;
import org.keycloak.forms.login.LoginFormsProvider;
import org.keycloak.models.*;
import org.keycloak.models.utils.FormMessage;
import org.keycloak.provider.ProviderConfigProperty;
import org.keycloak.services.validation.Validation;

import javax.ws.rs.core.MultivaluedMap;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class PhoneNumberValidation implements FormAction, FormActionFactory {

    public static final String PROVIDER_ID = "registration-phone-number-validation";

    private static final String PHONE_NUMBER_FIELD = "phoneNumber";

    @Override
    public String getHelpText() {
        return "Validates that the phone number starts with 06.";
    }

    @Override
    public List<ProviderConfigProperty> getConfigProperties() {
        ProviderConfigProperty configProperty = new ProviderConfigProperty();
        configProperty.setName("mandatory");
        configProperty.setLabel("Mandatory?");
        configProperty.setType("boolean");
        configProperty.setDefaultValue(true);
        return Arrays.asList(configProperty);
    }

    @Override
    public void validate(ValidationContext context) {
        boolean mandatory = context.getAuthenticatorConfig().getConfig().get("mandatory").equalsIgnoreCase(Boolean.TRUE.toString());
        MultivaluedMap<String, String> formData = context.getHttpRequest().getDecodedFormParameters();
        List<FormMessage> errors = new ArrayList<>();
        context.getEvent().detail(Details.REGISTER_METHOD, "form");
        String phoneNumber = formData.getFirst(PHONE_NUMBER_FIELD);
        if (mandatory && Validation.isBlank(phoneNumber)) {
            errors.add(new FormMessage(PHONE_NUMBER_FIELD, "missingPhoneNumber"));
        } else if (!Validation.isBlank(phoneNumber) && !phoneNumber.startsWith("06")) {
            errors.add(new FormMessage(PHONE_NUMBER_FIELD, "wrongPhoneNumber"));
        }

        if (errors.size() > 0) {
            context.error(Errors.INVALID_REGISTRATION);
            context.validationError(formData, errors);
            return;
        } else {
            context.success();
        }
    }

    @Override
    public void success(FormContext context) {
        UserModel user = context.getUser();
        MultivaluedMap<String, String> formData = context.getHttpRequest().getDecodedFormParameters();
        String phoneNumber = formData.getFirst(PHONE_NUMBER_FIELD);
        user.setAttribute("mobile", Arrays.asList(phoneNumber));
    }

    @Override
    public void buildPage(FormContext context, LoginFormsProvider form) {
        // DO NOTHING, could be used to initialize form fields
    }

    @Override
    public boolean requiresUser() {
        return false;
    }

    @Override
    public boolean configuredFor(KeycloakSession session, RealmModel realm, UserModel user) {
        return true;
    }

    @Override
    public void setRequiredActions(KeycloakSession session, RealmModel realm, UserModel user) {

    }

    @Override
    public boolean isUserSetupAllowed() {
        return false;
    }

    @Override
    public void close() {

    }

    @Override
    public String getDisplayType() {
        return "Phone number Validation";
    }

    @Override
    public String getReferenceCategory() {
        return null;
    }

    @Override
    public boolean isConfigurable() {
        return true;
    }

    private static AuthenticationExecutionModel.Requirement[] REQUIREMENT_CHOICES = {
            AuthenticationExecutionModel.Requirement.REQUIRED,
            AuthenticationExecutionModel.Requirement.DISABLED
    };

    @Override
    public AuthenticationExecutionModel.Requirement[] getRequirementChoices() {
        return REQUIREMENT_CHOICES;
    }

    @Override
    public FormAction create(KeycloakSession session) {
        return this;
    }

    @Override
    public void init(Config.Scope config) {
    }

    @Override
    public void postInit(KeycloakSessionFactory factory) {

    }

    @Override
    public String getId() {
        return PROVIDER_ID;
    }

}
