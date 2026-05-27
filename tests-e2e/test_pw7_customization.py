from __future__ import annotations

import pytest


@pytest.mark.pw7
def test_pw7_theme_solution_patch_applies(workspace_factory):
    workspace = workspace_factory("pw7-theme", "pw7_theme_enable")
    content = (
        workspace / "keycloak/theme/custom/login/messages/messages_en.properties"
    ).read_text(encoding="utf-8")
    dockerfile = (workspace / "keycloak/Dockerfile").read_text(encoding="utf-8")

    assert "Dear user, please login to access this page" in content
    assert "COPY theme/ /opt/keycloak/themes/" in dockerfile


@pytest.mark.pw7
def test_pw7_provider_solution_patches_apply(workspace_factory):
    workspace = workspace_factory(
        "pw7-provider",
        "pw7_age_mapper",
        "pw7_required_action",
        "pw7_question_authenticator",
    )
    age_mapper = (
        workspace
        / "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/mapper/AgeMapper.java"
    ).read_text(encoding="utf-8")
    required_action = (
        workspace
        / "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/requiredaction/UpdateQuestionAction.java"
    ).read_text(encoding="utf-8")
    authenticator = (
        workspace
        / "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/authenticator/QuestionAuthenticator.java"
    ).read_text(encoding="utf-8")

    assert 'getFirstAttribute("age")' in age_mapper
    assert 'setSingleAttribute("question", question)' in required_action
    assert "equalsIgnoreCase" in authenticator
