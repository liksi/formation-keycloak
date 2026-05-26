package fr.liksi.formation.keycloak.backapp.config;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = {
        "authentication-mode=none"
})
class NoneConfigTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void secretPageShouldBeAccessibleWithoutAuth() throws Exception {
        mockMvc.perform(get("/secret/index.html"))
                .andExpect(status().isOk());
    }

    @Test
    void adminPageShouldBeAccessibleWithoutAuth() throws Exception {
        mockMvc.perform(get("/admin/index.html"))
                .andExpect(status().isOk());
    }

    @Test
    void rootPageShouldBeAccessibleWithoutAuth() throws Exception {
        mockMvc.perform(get("/"))
                .andExpect(status().isOk());
    }
}
