package fr.liksi.formation.keycloak.authenticator;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class QuestionAuthenticatorFactoryTest {

    private final QuestionAuthenticatorFactory factory = new QuestionAuthenticatorFactory();

    @Test
    void shouldHaveCorrectProviderId() {
        assertThat(factory.getId()).isEqualTo("secret-question-authenticator");
    }

    @Test
    void shouldHaveCorrectDisplayType() {
        assertThat(factory.getDisplayType()).isEqualTo("Ask secret question");
    }

    @Test
    void shouldHaveCorrectHelpText() {
        assertThat(factory.getHelpText()).isEqualTo("Secret question authenticator");
    }

    @Test
    void shouldNotBeConfigurable() {
        assertThat(factory.isConfigurable()).isFalse();
    }

    @Test
    void shouldAllowUserSetup() {
        assertThat(factory.isUserSetupAllowed()).isTrue();
    }

    @Test
    void shouldHaveNoConfigProperties() {
        assertThat(factory.getConfigProperties()).isNull();
    }

    @Test
    void shouldReturnRequirementChoices() {
        assertThat(factory.getRequirementChoices()).hasSize(3);
    }

    @Test
    void shouldCreateSingletonAuthenticator() {
        var auth1 = factory.create(null);
        var auth2 = factory.create(null);
        assertThat(auth1).isSameAs(auth2);
    }
}
