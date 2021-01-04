FROM jboss/keycloak:12.0.1
MAINTAINER Tristan Denmat "tristan.denmat@liksi.fr"
EXPOSE 8080

USER root
RUN mkdir /opt/config && \
    chown jboss /opt/config



ADD standalone-ha.xml /opt/jboss/keycloak/standalone/configuration
ADD profile.properties /opt/jboss/keycloak/standalone/configuration

