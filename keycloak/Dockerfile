FROM jboss/keycloak:15.0.2
MAINTAINER Tristan Denmat "tristan.denmat@liksi.fr"
EXPOSE 8080

USER root
RUN mkdir /opt/config && \
    chown jboss /opt/config



ADD standalone-ha.xml /opt/jboss/keycloak/standalone/configuration
ADD profile.properties /opt/jboss/keycloak/standalone/configuration

