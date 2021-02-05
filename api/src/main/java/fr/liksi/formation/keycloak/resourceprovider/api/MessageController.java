package fr.liksi.formation.keycloak.resourceprovider.api;

import org.keycloak.KeycloakSecurityContext;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.servlet.http.HttpServletRequest;

@RestController
@RequestMapping(value = "/messages", produces = MediaType.APPLICATION_JSON_VALUE)
public class MessageController {

    private static final Logger LOGGER = LoggerFactory.getLogger(MessageController.class);

    @GetMapping("/user")
    private Message getUser() {
        Message result = new Message();
        result.setMessage("Hello User");
        return result;
    }

    @GetMapping("/admin")
    private Message getAdmin(HttpServletRequest httpServletRequest) {
        final KeycloakSecurityContext keycloakSecurityContext = (KeycloakSecurityContext) httpServletRequest
                .getAttribute(KeycloakSecurityContext.class.getName());
        if (keycloakSecurityContext != null) {
            final String username = keycloakSecurityContext.getToken().getPreferredUsername();
            LOGGER.info("User {} fetches admin message", username);
        } else {
            LOGGER.warn("The request is not authenticated");
        }
        Message result = new Message();
        result.setMessage("Hello Admin");
        return result;
    }

    @GetMapping("/public")
    private Message getFree() {
        Message result = new Message();
        result.setMessage("Hello, this is not protected");
        return result;
    }

}
