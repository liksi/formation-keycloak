package fr.liksi.formation.keycloak.requiredaction;

import org.keycloak.Config;
import org.keycloak.authentication.RequiredActionFactory;
import org.keycloak.authentication.RequiredActionProvider;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;

public class UpdateQuestionActionFactory implements RequiredActionFactory {

        private static final UpdateQuestionAction SINGLETON = new UpdateQuestionAction();

        @Override
        public RequiredActionProvider create(KeycloakSession session) {
            return SINGLETON;
        }


        @Override
        public String getId() {
            return UpdateQuestionAction.PROVIDER_ID;
        }

        @Override
        public String getDisplayText() {
            return "Update question";
        }

        @Override
        public void init(Config.Scope config) {

        }

        @Override
        public void postInit(KeycloakSessionFactory factory) {

        }

        @Override
        public void close() {

        }



    }
