from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


class WorkspaceManager:
    def __init__(
        self, source_root: Path, tests_root: Path, keep_workspaces: bool = False
    ) -> None:
        self.source_root = source_root
        self.tests_root = tests_root
        self.keep_workspaces = keep_workspaces
        self._created: list[Path] = []

    def create(self, name: str) -> Path:
        root = Path(tempfile.mkdtemp(prefix=f"formation-keycloak-{name}-"))
        destination = root / "repo"
        shutil.copytree(
            self.source_root,
            destination,
            ignore=shutil.ignore_patterns(
                ".git",
                ".playwright-mcp",
                ".pytest_cache",
                "__pycache__",
                "*.pyc",
                "node_modules",
                "target",
                ".venv",
                "artifacts",
            ),
        )
        self._created.append(root)
        return destination

    def apply_solution(self, workspace: Path, solution_name: str) -> None:
        handlers = {
            "pw1_basic": self._apply_pw1_basic,
            "pw1_form": self._apply_pw1_form,
            "pw2_secret_webapp_local_keycloak": self._apply_pw2_secret_webapp_local_keycloak,
            "pw6_oauth2_proxy_compose": self._apply_pw6_oauth2_proxy_compose,
            "pw5_api_local_issuer": self._apply_pw5_api_local_issuer,
            "pw5_api_user_endpoint_roles": self._apply_pw5_api_user_endpoint_roles,
            "pw5_vue_login": self._apply_pw5_vue_login,
            "pw5_vue_bearer_token": self._apply_pw5_vue_bearer_token,
            "pw5_vue_token_refresh": self._apply_pw5_vue_token_refresh,
            "pw7_theme_enable": self._apply_pw7_theme_enable,
            "pw7_age_mapper": self._apply_pw7_age_mapper,
            "pw7_required_action": self._apply_pw7_required_action,
            "pw7_question_authenticator": self._apply_pw7_question_authenticator,
        }
        try:
            handlers[solution_name](workspace)
        except KeyError as exc:
            raise ValueError(f"Unknown solution {solution_name}") from exc

    def replace(self, workspace: Path, relative_path: str, old: str, new: str) -> None:
        target = workspace / relative_path
        target.write_text(
            target.read_text(encoding="utf-8").replace(old, new),
            encoding="utf-8",
        )

    def _replace_checked(
        self, workspace: Path, relative_path: str, old: str, new: str
    ) -> None:
        target = workspace / relative_path
        content = target.read_text(encoding="utf-8")
        if new in content and old not in content:
            return
        if old not in content:
            raise ValueError(f"Expected snippet not found in {relative_path}")
        target.write_text(content.replace(old, new), encoding="utf-8")

    def _append_if_missing(
        self, workspace: Path, relative_path: str, text: str
    ) -> None:
        target = workspace / relative_path
        content = target.read_text(encoding="utf-8")
        if text not in content:
            target.write_text(content.rstrip() + "\n" + text + "\n", encoding="utf-8")

    def _apply_pw1_basic(self, workspace: Path) -> None:
        self._replace_checked(
            workspace,
            "secret-webapp/src/main/resources/application.yml",
            "authentication-mode: none\n#authentication-mode: basic",
            "#authentication-mode: none\nauthentication-mode: basic",
        )

    def _apply_pw1_form(self, workspace: Path) -> None:
        self._replace_checked(
            workspace,
            "secret-webapp/src/main/resources/application.yml",
            "authentication-mode: none\n#authentication-mode: basic\n#authentication-mode: form",
            "#authentication-mode: none\n#authentication-mode: basic\nauthentication-mode: form",
        )

    def _apply_pw2_secret_webapp_local_keycloak(self, workspace: Path) -> None:
        self._replace_checked(
            workspace,
            "secret-webapp/src/main/resources/application.yml",
            "authentication-mode: none\n#authentication-mode: basic\n#authentication-mode: form\n#authentication-mode: keycloak",
            "#authentication-mode: none\n#authentication-mode: basic\n#authentication-mode: form\nauthentication-mode: keycloak",
        )
        self._replace_checked(
            workspace,
            "secret-webapp/src/main/resources/application-keycloak.yml",
            "issuer-uri: https://lemur-5.cloud-iam.com/auth/realms/keycloak-training",
            "issuer-uri: http://localhost:8080/realms/training",
        )

    def _apply_pw5_api_local_issuer(self, workspace: Path) -> None:
        self._replace_checked(
            workspace,
            "api/src/main/resources/application.yml",
            "issuer-uri: http://localhost:8080/realms/test",
            "issuer-uri: http://localhost:8080/realms/training",
        )

    def _apply_pw5_api_user_endpoint_roles(self, workspace: Path) -> None:
        self._replace_checked(
            workspace,
            "api/src/main/java/fr/liksi/formation/keycloak/resourceprovider/config/OauthResourceConfiguration.java",
            '.requestMatchers("/messages/user").denyAll()',
            '.requestMatchers("/messages/user").hasAnyRole("ADMIN", "USER")',
        )

    def _apply_pw5_vue_login(self, workspace: Path) -> None:
        self._replace_checked(
            workspace,
            "vue-app/src/main.js",
            "//login().then(() => {\n  app.mount('#app')\n//}, () => {})",
            "login().then(() => {\n  app.mount('#app')\n}, () => {})",
        )
        self._replace_checked(
            workspace,
            "vue-app/src/keycloak.js",
            "url: 'http://localhost:8080', realm: 'test', clientId: 'vue', onLoad: 'login-required'",
            "url: 'http://localhost:8080', realm: 'training', clientId: 'vue', onLoad: 'login-required'",
        )

    def _apply_pw5_vue_bearer_token(self, workspace: Path) -> None:
        target = workspace / "vue-app/src/components/FetchBox.vue"
        content = target.read_text(encoding="utf-8")
        content = content.replace(
            "import { getRoles } from '@/keycloak'",
            "import { getAccessToken, getRoles } from '@/keycloak'",
        )
        if "Authorization: 'Bearer ' + getAccessToken()" not in content:
            content = content.replace(
                "  fetch('http://localhost:8091/messages/' + props.kind)\n",
                "  fetch('http://localhost:8091/messages/' + props.kind, {\n"
                "    headers: {\n"
                "      Authorization: 'Bearer ' + getAccessToken()\n"
                "    }\n"
                "  })\n",
            )
            content = content.replace(
                "      fetch('http://localhost:8091/messages/' + this.kind)\n",
                "      fetch('http://localhost:8091/messages/' + this.kind, {\n"
                "        headers: {\n"
                "          Authorization: 'Bearer ' + getAccessToken()\n"
                "        }\n"
                "      })\n",
            )
        target.write_text(content, encoding="utf-8")

    def _apply_pw5_vue_token_refresh(self, workspace: Path) -> None:
        self._replace_checked(
            workspace,
            "vue-app/src/keycloak.js",
            "    //scheduleRefresh()",
            "    scheduleRefresh()",
        )
        self._replace_checked(
            workspace,
            "vue-app/src/keycloak.js",
            "// function scheduleRefresh () {\n"
            "//   setInterval(() => {\n"
            "//     keycloak.updateToken(30).then((refreshed) => {\n"
            "//       if (refreshed) {\n"
            "//         console.log('Token refreshed' + refreshed)\n"
            "//       } else {\n"
            "//         console.log('Token not refreshed, valid for ' +\n"
            "//           Math.round(keycloak.tokenParsed.exp + keycloak.timeSkew - new Date().getTime() / 1000) + ' seconds')\n"
            "//       }\n"
            "//     }, () => {\n"
            "//       console.log('Failed to refresh token')\n"
            "//     })\n"
            "//   }, 10000)\n"
            "// }\n",
            "function scheduleRefresh () {\n"
            "  setInterval(() => {\n"
            "    keycloak.updateToken(30).then((refreshed) => {\n"
            "      if (refreshed) {\n"
            "        console.log('Token refreshed' + refreshed)\n"
            "      } else {\n"
            "        console.log('Token not refreshed, valid for ' +\n"
            "          Math.round(keycloak.tokenParsed.exp + keycloak.timeSkew - new Date().getTime() / 1000) + ' seconds')\n"
            "      }\n"
            "    }, () => {\n"
            "      console.log('Failed to refresh token')\n"
            "    })\n"
            "  }, 10000)\n"
            "}\n",
        )

    def _apply_pw6_oauth2_proxy_compose(self, workspace: Path) -> None:
        target = workspace / "docker-compose.yml"
        content = target.read_text(encoding="utf-8")
        content = content.replace(
            '      OAUTH2_PROXY_COOKIE_SECRET: "SECRET_KEY123456"',
            '      OAUTH2_PROXY_COOKIE_SECRET: "0123456789abcdef0123456789abcdef"',
        )
        content = content.replace(
            '      OAUTH2_PROXY_COOKIE_SECRET: "0123456789abcdef0123456789abcdef01234567="',
            '      OAUTH2_PROXY_COOKIE_SECRET: "0123456789abcdef0123456789abcdef"',
        )
        target.write_text(content, encoding="utf-8")

    def _apply_pw7_theme_enable(self, workspace: Path) -> None:
        self._replace_checked(
            workspace,
            "keycloak/Dockerfile",
            "#COPY theme/ /opt/keycloak/themes/",
            "COPY theme/ /opt/keycloak/themes/",
        )
        self._append_if_missing(
            workspace,
            "keycloak/theme/custom/login/messages/messages_en.properties",
            "loginAccountTitle=Dear user, please login to access this page\n"
            "updateQuestionTitle=Set your secret question\n"
            "answerQuestionTitle=Answer your secret question\n"
            "question=Question\n"
            "answer=Answer",
        )

    def _apply_pw7_age_mapper(self, workspace: Path) -> None:
        self._replace_checked(
            workspace,
            "keycloak/Dockerfile",
            "#COPY provider/target/*.jar /opt/keycloak/providers/",
            "COPY provider/target/*.jar /opt/keycloak/providers/",
        )
        self._replace_checked(
            workspace,
            "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/mapper/AgeMapper.java",
            'String ageStr = ""; //FIXME',
            'String ageStr = userSession.getUser().getFirstAttribute("age");',
        )
        self._replace_checked(
            workspace,
            "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/mapper/AgeMapper.java",
            "// FIXME - add new claim",
            'token.getOtherClaims().put("is_adult", isAdult);',
        )
        self._replace_checked(
            workspace,
            "keycloak/provider/src/main/resources/META-INF/services/org.keycloak.protocol.ProtocolMapper",
            "#fr.liksi.formation.keycloak.mapper.AgeMapper",
            "fr.liksi.formation.keycloak.mapper.AgeMapper",
        )

    def _apply_pw7_required_action(self, workspace: Path) -> None:
        self._apply_pw7_theme_enable(workspace)
        self._replace_checked(
            workspace,
            "keycloak/Dockerfile",
            "#COPY provider/target/*.jar /opt/keycloak/providers/",
            "COPY provider/target/*.jar /opt/keycloak/providers/",
        )
        self._replace_checked(
            workspace,
            "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/requiredaction/UpdateQuestionAction.java",
            "if (false) { // FIXME",
            'if (StringUtil.isBlank(context.getUser().getFirstAttribute("question"))) {',
        )
        self._replace_checked(
            workspace,
            "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/requiredaction/UpdateQuestionAction.java",
            "String answer = null; // FIXME",
            'String answer = formData.getFirst("answer");',
        )
        self._replace_checked(
            workspace,
            "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/requiredaction/UpdateQuestionAction.java",
            "String question = null; // FIXME",
            'String question = formData.getFirst("question");',
        )
        self._replace_checked(
            workspace,
            "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/requiredaction/UpdateQuestionAction.java",
            "// FIXME - store answer and question in user attributes",
            'context.getUser().setSingleAttribute("answer", answer);\n'
            '        context.getUser().setSingleAttribute("question", question);',
        )
        self._replace_checked(
            workspace,
            "keycloak/provider/src/main/resources/META-INF/services/org.keycloak.authentication.RequiredActionFactory",
            "#fr.liksi.formation.keycloak.requiredaction.UpdateQuestionActionFactory",
            "fr.liksi.formation.keycloak.requiredaction.UpdateQuestionActionFactory",
        )

    def _apply_pw7_question_authenticator(self, workspace: Path) -> None:
        self._apply_pw7_theme_enable(workspace)
        self._replace_checked(
            workspace,
            "keycloak/Dockerfile",
            "#COPY provider/target/*.jar /opt/keycloak/providers/",
            "COPY provider/target/*.jar /opt/keycloak/providers/",
        )
        self._replace_checked(
            workspace,
            "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/authenticator/QuestionAuthenticator.java",
            "        if (StringUtil.isBlank(question)) {\n            // FIXME\n        } else {",
            "        if (StringUtil.isBlank(question)) {\n            context.success();\n        } else {",
        )
        self._replace_checked(
            workspace,
            "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/authenticator/QuestionAuthenticator.java",
            '            // FIXME\n            context.challenge(context.form().createForm("question.ftl"));',
            '            forms.setAttribute("question", question);\n            context.challenge(context.form().createForm("question.ftl"));',
        )
        self._replace_checked(
            workspace,
            "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/authenticator/QuestionAuthenticator.java",
            "if (true) { // FIXME",
            'if (answer != null && answer.equalsIgnoreCase(context.getUser().getFirstAttribute("answer"))) {',
        )
        self._replace_checked(
            workspace,
            "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/authenticator/QuestionAuthenticator.java",
            '            // FIXME\n            context.challenge(forms.createForm("question.ftl"));',
            '            forms.setAttribute("question", context.getUser().getFirstAttribute("question"));\n            context.challenge(forms.createForm("question.ftl"));',
        )
        self._replace_checked(
            workspace,
            "keycloak/provider/src/main/resources/META-INF/services/org.keycloak.authentication.AuthenticatorFactory",
            "#fr.liksi.formation.keycloak.authenticator.QuestionAuthenticatorFactory",
            "fr.liksi.formation.keycloak.authenticator.QuestionAuthenticatorFactory",
        )

    def cleanup(self) -> None:
        if self.keep_workspaces:
            return
        for root in self._created:
            shutil.rmtree(root, ignore_errors=True)
