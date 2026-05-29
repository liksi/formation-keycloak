package fr.liksi.formation.keycloak.requiredaction;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class UpdateQuestionActionFactoryTest {

    private final UpdateQuestionActionFactory factory = new UpdateQuestionActionFactory();

    @Test
    void shouldHaveCorrectId() {
        assertThat(factory.getId()).isEqualTo("update_question");
    }

    @Test
    void shouldHaveCorrectDisplayText() {
        assertThat(factory.getDisplayText()).isEqualTo("Update question");
    }

    @Test
    void shouldCreateSingletonProvider() {
        var provider1 = factory.create(null);
        var provider2 = factory.create(null);
        assertThat(provider1).isSameAs(provider2);
    }
}
