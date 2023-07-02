package fr.liksi.formation.keycloak.mapper;

import org.keycloak.models.ClientSessionContext;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.ProtocolMapperModel;
import org.keycloak.models.UserSessionModel;
import org.keycloak.protocol.oidc.mappers.*;
import org.keycloak.provider.ProviderConfigProperty;
import org.keycloak.representations.IDToken;

import java.util.ArrayList;
import java.util.List;

public class AgeMapper  extends AbstractOIDCProtocolMapper implements OIDCAccessTokenMapper, OIDCIDTokenMapper, UserInfoTokenMapper {

    private static final List<ProviderConfigProperty> configProperties = new ArrayList<>();
    static {
        OIDCAttributeMapperHelper.addIncludeInTokensConfig(configProperties, AgeMapper.class);
    }

    private static final int MIN_AGE = 21;

    @Override
    protected void setClaim(IDToken token, ProtocolMapperModel protocolMapperModel, UserSessionModel userSession, KeycloakSession keycloakSession, ClientSessionContext clientSessionCtx) {
        String ageStr = ""; //FIXME
        Integer age = convertToInt(ageStr);
        if (age != null) {
            boolean isAdult = age >= MIN_AGE;
            // FIXME - add new claim
        }
    }

    private Integer convertToInt(String ageStr) {
        Integer result = null;
        if (ageStr != null) {
            try {
                result = Integer.parseInt(ageStr);
            } catch (Exception ex) {
                // Not an int
            }
        }
        return result;
    }


    @Override
    public String getId() {
        return "AGE_MAPPER";
    }

    @Override
    public String getDisplayType() {
        return "Age Mapper";
    }

    @Override
    public String getDisplayCategory() {
        return TOKEN_MAPPER_CATEGORY;
    }

    @Override
    public String getHelpText() {
        return "Adds isAdult flag";
    }

    @Override
    public List<ProviderConfigProperty> getConfigProperties() {
        return configProperties;
    }

}
