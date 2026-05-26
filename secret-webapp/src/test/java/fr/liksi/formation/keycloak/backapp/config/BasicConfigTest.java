package fr.liksi.formation.keycloak.backapp.config;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = {
        "authentication-mode=basic"
})
class BasicConfigTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void secretPageShouldReturn401WithoutAuth() throws Exception {
        mockMvc.perform(get("/secret/index.html"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void secretPageShouldReturn200WithValidCredentials() throws Exception {
        mockMvc.perform(get("/secret/index.html")
                        .with(httpBasic("user", "pwd")))
                .andExpect(status().isOk());
    }

    @Test
    void secretPageShouldReturn401WithInvalidCredentials() throws Exception {
        mockMvc.perform(get("/secret/index.html")
                        .with(httpBasic("user", "wrong")))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void rootPageShouldBeAccessibleWithoutAuth() throws Exception {
        mockMvc.perform(get("/"))
                .andExpect(status().isOk());
    }
}
