package fr.liksi.formation.keycloak.backapp.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@ConditionalOnProperty(value = "authentication-mode", havingValue = "keycloak")
public class KeycloakConfig {

	   @Bean
	   public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
			  http.authorizeHttpRequests(auth ->
							  auth.requestMatchers("/secret/**").authenticated().anyRequest().permitAll()
					  )
					  .oauth2Login(Customizer.withDefaults());
			  return http.build();
	   }


}

