package fr.liksi.formation.keycloak.backapp.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.authority.mapping.GrantedAuthoritiesMapper;
import org.springframework.security.oauth2.client.oidc.web.logout.OidcClientInitiatedLogoutSuccessHandler;
import org.springframework.security.oauth2.client.registration.ClientRegistrationRepository;
import org.springframework.security.oauth2.core.oidc.OidcIdToken;
import org.springframework.security.oauth2.core.oidc.user.OidcUserAuthority;
import org.springframework.security.web.SecurityFilterChain;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Configuration
@ConditionalOnProperty(value = "authentication-mode", havingValue = "keycloak")
public class KeycloakConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http, ClientRegistrationRepository clientRegistrationRepository) throws Exception {
        http.authorizeHttpRequests(auth -> auth
                        .requestMatchers("/secret/**").authenticated()
                        .requestMatchers("/admin/**").hasRole("ADMIN")
                        .anyRequest().permitAll())
                .oauth2Login(oauth2 -> oauth2
                        .userInfoEndpoint(userInfo -> userInfo
                               .userAuthoritiesMapper(this.userAuthoritiesMapper()))
                )
                .logout(logout -> logout.logoutSuccessHandler(oidcLogoutSuccessHandler(clientRegistrationRepository)));
        return http.build();
    }

    private OidcClientInitiatedLogoutSuccessHandler oidcLogoutSuccessHandler(ClientRegistrationRepository clientRegistrationRepository) {
        OidcClientInitiatedLogoutSuccessHandler successHandler = new OidcClientInitiatedLogoutSuccessHandler(clientRegistrationRepository);
        successHandler.setPostLogoutRedirectUri("/");
        return successHandler;
    }

    public GrantedAuthoritiesMapper userAuthoritiesMapper() {
        return (authorities) -> {
            Set<GrantedAuthority> mappedAuthorities = new HashSet<>();
            authorities.forEach(authority -> {
                    OidcUserAuthority oidcUserAuthority = (OidcUserAuthority)authority;
                    OidcIdToken idToken = oidcUserAuthority.getIdToken();
                    Map<String, Object> realmsAccessClaim = idToken.getClaimAsMap("realm_access");
                    if (realmsAccessClaim != null) {
                        List<String> realmsRoles = (List<String>) realmsAccessClaim.get("roles");
                        if (realmsRoles != null) {
                             realmsRoles.stream()
                                    .map(role -> new SimpleGrantedAuthority(role))
                                    .forEach(mappedAuthorities::add);
                        }
                    }
            });
            return mappedAuthorities;
        };
    }

}

