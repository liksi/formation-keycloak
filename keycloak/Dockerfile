FROM quay.io/keycloak/keycloak:21.1.1 as builder

ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true
ENV KC_DB=postgres
ENV KC_HTTP_RELATIVE_PATH=/auth
ENV KC_FEATURES=declarative-user-profile

COPY conf/keycloak.conf /opt/keycloak/conf/

RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:21.1.1

ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true
ENV KC_DB=postgres
ENV KC_HTTP_RELATIVE_PATH=/auth
ENV KC_FEATURES=declarative-user-profile

COPY --from=builder /opt/keycloak/ /opt/keycloak/
WORKDIR /opt/keycloak

ENTRYPOINT ["/opt/keycloak/bin/kc.sh", "start"]
