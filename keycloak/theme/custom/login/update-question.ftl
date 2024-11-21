<#import "template.ftl" as layout>
<#import "field.ftl" as field>
<#import "buttons.ftl" as buttons>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('question','answer') displayInfo=true; section>
    <!-- template: login.ftl -->
    <#if section = "header">
        ${msg("updateQuestionTitle")}
    <#elseif section = "form">
         <div id="kc-form">
            <div id="kc-form-wrapper">
                <form id="kc-form-question-update" class="${properties.kcFormClass!}" onsubmit="login.disabled = true; return true;" action="${url.loginAction}" method="post" novalidate="novalidate">

                    <@field.input name="question" label=msg("question") autofocus=true autocomplete="question" />
                    <@field.input name="answer" label=msg("answer") autocomplete="answer" />

                    <@buttons.loginButton />
                </form>
            </div>
         </div>
    </#if>
</@layout.registrationLayout>
