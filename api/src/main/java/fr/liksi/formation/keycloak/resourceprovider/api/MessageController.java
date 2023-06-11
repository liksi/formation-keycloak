package fr.liksi.formation.keycloak.resourceprovider.api;

import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;


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
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication instanceof JwtAuthenticationToken) {
            JwtAuthenticationToken jwtAuthenticationToken = (JwtAuthenticationToken) authentication;
            final String username = jwtAuthenticationToken.getToken().getClaimAsString("preferred_username");
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
