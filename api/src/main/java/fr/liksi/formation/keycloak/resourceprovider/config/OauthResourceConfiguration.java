package fr.liksi.formation.keycloak.resourceprovider.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.convert.converter.Converter;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.oauth2.server.resource.authentication.JwtGrantedAuthoritiesConverter;
import org.springframework.security.web.SecurityFilterChain;

import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Configuration
public class OauthResourceConfiguration {

	   @Bean
	   public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
			  http
					  .authorizeHttpRequests(auth -> auth
							  .requestMatchers(HttpMethod.OPTIONS).permitAll()
							  .requestMatchers("/messages/admin").hasRole("ADMIN")
							  .requestMatchers("/messages/user").denyAll()
							  .anyRequest().permitAll()
					  )
					  .oauth2ResourceServer(oauth2 -> oauth2
							  .jwt(jwt -> jwt.jwtAuthenticationConverter(jwtAuthenticationConverter())));
			  return http.build();
	   }

	   public JwtAuthenticationConverter jwtAuthenticationConverter() {
			  JwtAuthenticationConverter jwtAuthenticationConverter = new JwtAuthenticationConverter();
			  jwtAuthenticationConverter.setJwtGrantedAuthoritiesConverter(new Converter<Jwt, Collection<GrantedAuthority>>() {
					 @Override
					 public Collection<GrantedAuthority> convert(Jwt source) {
							Map<String, Object> realmsAccessClaim = source.getClaimAsMap("realm_access");
							if (realmsAccessClaim != null) {
								   List<String> realmsRoles = (List<String>) realmsAccessClaim.get("roles");
								   if (realmsRoles != null) {
										  return realmsRoles.stream()
												  .map(role -> new SimpleGrantedAuthority(role))
												  .collect(Collectors.toList());
								   }
							}
							return Collections.emptyList();
					 }
			  });
			  return jwtAuthenticationConverter;
	   }
}
