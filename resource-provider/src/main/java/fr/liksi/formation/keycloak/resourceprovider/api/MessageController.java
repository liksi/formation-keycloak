package fr.liksi.formation.keycloak.resourceprovider.api;

import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping(value = "/messages", produces = MediaType.APPLICATION_JSON_VALUE)
public class MessageController {

    @GetMapping("/user")
    private Message getUser() {
        Message result = new Message();
        result.setMessage("Hello User");
        return result;
    }

    @GetMapping("/admin")
    private Message getAdmin() {
        Message result = new Message();
        result.setMessage("Hello Admin");
        return result;
    }

}
