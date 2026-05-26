FROM maven:3-eclipse-temurin-25 AS builder
WORKDIR /build
COPY pom.xml .
RUN mvn dependency:go-offline -B -q
COPY src src
RUN mvn package -DskipTests -B -q

FROM eclipse-temurin:25-jre
COPY --from=builder /build/target/*.jar /app.jar
ENV AUTHENTICATION_MODE=none
EXPOSE 8090
ENTRYPOINT ["sh", "-c", "java -jar /app.jar --authentication-mode=${AUTHENTICATION_MODE}"]
