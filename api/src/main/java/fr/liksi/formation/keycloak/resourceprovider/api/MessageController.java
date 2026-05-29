package fr.liksi.formation.keycloak.resourceprovider.api;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;


@RestController
@RequestMapping(value = "/messages", produces = MediaType.APPLICATION_JSON_VALUE)
public class MessageController {

    private static final Logger LOGGER = LoggerFactory.getLogger(MessageController.class);

    @GetMapping("/user")
    public Message getUser() {
        return new Message("Hello User");
    }

    @GetMapping("/admin")
    public Message getAdmin(@AuthenticationPrincipal Jwt jwt) {
        if (jwt != null) {
            LOGGER.info("User {} fetches admin message", jwt.getClaimAsString("preferred_username"));
        } else {
            LOGGER.warn("The request is not authenticated");
        }
        return new Message("Hello Admin");
    }

    @GetMapping("/public")
    public Message getFree() {
        return new Message("Hello, this is not protected");
    }

}
