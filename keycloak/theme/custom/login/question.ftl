<#import "template.ftl" as layout>
<@layout.registrationLayout displayInfo=social.displayInfo displayWide=(realm.password && social.providers??); section>
    <#if section = "header">
        ${msg("doLogIn")}
    <#elseif section = "form">
        <div id="kc-form" <#if realm.password && social.providers??>class="${properties.kcContentWrapperClass!}"</#if>>
            <form id="kc-form-login" onsubmit="login.disabled = true; return true;" action="${url.loginAction}"
                  method="post">
                <div id="kc-form-wrapper">
                    <p class="libelle">
                        ${question}
                    </p>
                    <div class="${properties.kcFormGroupClass!}">
                        <div class="password-input">
                            <input tabindex="2" placeholder="${msg("answer")}" id="answer"
                                   class="${properties.kcInputClass!} login-input <#if message?has_content && message.type = 'error'>${properties.kcErrorOnInputClass!}</#if>" name="answer"
                                   autocomplete="off"/>
                        </div>
                    </div>

                    <#if message?has_content && message.type = 'error'><p class="error-message">${message.summary}</p></#if>

                    <div id="kc-form-buttons" class="${properties.kcFormGroupClass!}">

                        <input tabindex="4"
                               class="${properties.kcButtonClass!} btn-login"
                               name="login" id="kc-login" type="submit" value="${msg("doSend")}"/>

                        <input tabindex="5"
                               class="${properties.kcButtonClass!} ${properties.kcButtonInvertedClass!} ${properties.kcButtonLargeClass!} btn-login"
                               name="cancel" id="kc-cancel" type="submit" value="${msg("cancel")}"/>
                    </div>
                </div>
                </#if>
            </form>
        </div>
</@layout.registrationLayout>
