<#import "template.ftl" as layout>
<#import "field.ftl" as field>
<#import "buttons.ftl" as buttons>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('question','answer') displayInfo=true; section>
    <!-- template: login.ftl -->
    <#if section = "header">
        ${msg("answerQuestionTitle")}
    <#elseif section = "form">
        <div id="kc-form">
            <div id="kc-form-wrapper">
                <form id="kc-form-login" class="${properties.kcFormClass!}" onsubmit="login.disabled = true; return true;" action="${url.loginAction}" method="post" novalidate="novalidate">
                    ${question}
                    <@field.input name="answer" label=msg("answer") autocomplete="answer" />

                    <@buttons.loginButton />
                </form>
            </div>
        </div>
    </#if>
</@layout.registrationLayout>