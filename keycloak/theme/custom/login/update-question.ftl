<#import "template.ftl" as layout>
<@layout.registrationLayout displayInfo=social.displayInfo displayWide=(realm.password && social.providers??); section>
    <#if section = "header">
        ${msg("doLogIn")}
    <#elseif section = "form">
        <div id="kc-form" <#if realm.password && social.providers??>class="${properties.kcContentWrapperClass!}"</#if>>
            <p class="libelle">${msg("uqLibelle")}</p>
            <form id="kc-update-profile-form" action="${url.loginAction}" method="post">
                <div id="kc-form-wrapper"
                     <#if realm.password && social.providers??>class="${properties.kcFormSocialAccountContentClass!} ${properties.kcFormSocialAccountClass!}"</#if>>
                    <div class="${properties.kcFormGroupClass!} ${messagesPerField.printIfExists('email',properties.kcFormGroupErrorClass!)}">
                        <input placeholder="${msg("question")}" type="text" id="question" name="question" value="${(question!'')}"
                               class="${properties.kcInputClass!} login-input <#if message?has_content && message.type = 'error'>${properties.kcErrorOnInputClass!}</#if>"/>
                        <input placeholder="${msg("answer")}" type="text" id="answer" name="answer" value="${(answer!'')}"
                               class="${properties.kcInputClass!} login-input <#if message?has_content && message.type = 'error'>${properties.kcErrorOnInputClass!}</#if>"/>
                    </div>

                    <#if message?has_content && message.type = 'error'><p
                            class="error-message">${message.summary}</p></#if>

                    <div id="kc-form-buttons" class="${properties.kcFormGroupClass!}">
                        <input class="${properties.kcButtonClass!} btn-login"
                               type="submit" value="${msg("doSave")}"/>
                    </div>
                </div>

            </form>
        </div>
    </#if>
</@layout.registrationLayout>
