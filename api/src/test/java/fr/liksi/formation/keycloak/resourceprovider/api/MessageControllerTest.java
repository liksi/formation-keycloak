package fr.liksi.formation.keycloak.resourceprovider.api;

import fr.liksi.formation.keycloak.resourceprovider.config.CorsGlobalConfiguration;
import fr.liksi.formation.keycloak.resourceprovider.config.OauthResourceConfiguration;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(MessageController.class)
@Import({OauthResourceConfiguration.class, CorsGlobalConfiguration.class})
class MessageControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private JwtDecoder jwtDecoder;

    @Test
    void publicEndpointShouldBeAccessibleWithoutAuth() throws Exception {
        mockMvc.perform(get("/messages/public"))
                .andExpect(status().isOk())
                .andExpect(content().json("{\"message\":\"Hello, this is not protected\"}"));
    }

    @Test
    void adminEndpointShouldReturn401WithoutAuth() throws Exception {
        mockMvc.perform(get("/messages/admin"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void adminEndpointShouldReturn403WithoutAdminRole() throws Exception {
        mockMvc.perform(get("/messages/admin")
                        .with(jwt()))
                .andExpect(status().isForbidden());
    }

    @Test
    void adminEndpointShouldReturn200WithAdminRole() throws Exception {
        mockMvc.perform(get("/messages/admin")
                        .with(jwt().authorities(new SimpleGrantedAuthority("ROLE_ADMIN"))))
                .andExpect(status().isOk())
                .andExpect(content().json("{\"message\":\"Hello Admin\"}"));
    }

    @Test
    void adminEndpointShouldReturn200WithAdminRoleAndPreferredUsername() throws Exception {
        mockMvc.perform(get("/messages/admin")
                        .with(jwt()
                                .jwt(jwt -> jwt.claim("preferred_username", "john.doe"))
                                .authorities(new SimpleGrantedAuthority("ROLE_ADMIN"))))
                .andExpect(status().isOk())
                .andExpect(content().json("{\"message\":\"Hello Admin\"}"));
    }

    @Test
    void userEndpointShouldReturn401WhenDenyAll() throws Exception {
        mockMvc.perform(get("/messages/user"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void userEndpointShouldReturn403EvenWithAuth() throws Exception {
        mockMvc.perform(get("/messages/user")
                        .with(jwt()))
                .andExpect(status().isForbidden());
    }
}
