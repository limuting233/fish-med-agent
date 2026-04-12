<script lang="ts" setup></script>

<template>
    <div class="login-page">
        <section class="brand-panel">
            <div class="brand-panel__glow brand-panel__glow--top"></div>
            <div class="brand-panel__glow brand-panel__glow--bottom"></div>
            <div class="brand-scene" aria-hidden="true">
                <svg class="brand-scene__art" viewBox="0 0 900 1200" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
                    <defs>
                        <linearGradient id="scene-wave" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#86def6" stop-opacity="0.32" />
                            <stop offset="100%" stop-color="#0a6a9c" stop-opacity="0.06" />
                        </linearGradient>
                        <linearGradient id="scene-fish" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#d8f3fb" stop-opacity="0.9" />
                            <stop offset="100%" stop-color="#58c4e5" stop-opacity="0.45" />
                        </linearGradient>
                    </defs>

                    <circle cx="170" cy="220" r="150" fill="#9ae8fb" fill-opacity="0.08" />
                    <circle cx="690" cy="300" r="220" fill="#9ae8fb" fill-opacity="0.05" />
                    <circle cx="760" cy="910" r="180" fill="#9ae8fb" fill-opacity="0.07" />

                    <path d="M-40 830C140 760 270 770 420 820C560 870 700 940 940 870V1240H-40V830Z" fill="url(#scene-wave)" />
                    <path d="M-30 920C150 850 320 860 500 930C650 990 790 1010 930 980V1240H-30V920Z" fill="#7fdcf0" fill-opacity="0.08" />

                    <g opacity="0.72">
                        <path d="M540 430C604 392 702 394 786 456C720 460 677 487 645 531C601 517 564 485 540 430Z" fill="url(#scene-fish)" />
                        <path d="M784 456L850 425L834 495L784 456Z" fill="#b7edf9" fill-opacity="0.72" />
                        <circle cx="728" cy="446" r="6" fill="#05334f" fill-opacity="0.7" />
                    </g>

                    <g opacity="0.42">
                        <path d="M238 654C284 627 356 629 418 672C369 676 338 697 314 729C281 718 254 694 238 654Z" fill="url(#scene-fish)" />
                        <path d="M416 672L466 649L454 704L416 672Z" fill="#b7edf9" fill-opacity="0.65" />
                    </g>

                    <g opacity="0.48" stroke="#d7f7ff" stroke-opacity="0.42" fill="none">
                        <path d="M96 262C190 224 312 234 392 296" stroke-width="4" stroke-linecap="round" />
                        <path d="M116 302C205 270 304 282 366 334" stroke-width="3" stroke-linecap="round" />
                        <path d="M512 182C594 162 666 176 730 234" stroke-width="3" stroke-linecap="round" />
                    </g>

                    <g opacity="0.4">
                        <rect x="555" y="674" width="190" height="128" rx="24" fill="#d5f5fd" fill-opacity="0.12" stroke="#d5f5fd" stroke-opacity="0.28" />
                        <rect x="582" y="708" width="82" height="12" rx="6" fill="#d5f5fd" fill-opacity="0.52" />
                        <rect x="582" y="736" width="138" height="12" rx="6" fill="#d5f5fd" fill-opacity="0.38" />
                        <rect x="582" y="764" width="112" height="12" rx="6" fill="#d5f5fd" fill-opacity="0.24" />
                    </g>

                    <g opacity="0.36">
                        <circle cx="604" cy="575" r="56" fill="none" stroke="#d7f7ff" stroke-width="3" stroke-opacity="0.34" />
                        <circle cx="604" cy="575" r="28" fill="none" stroke="#d7f7ff" stroke-width="3" stroke-opacity="0.34" />
                        <path d="M604 509V641M538 575H670" stroke="#d7f7ff" stroke-width="3" stroke-opacity="0.26" />
                    </g>
                </svg>
            </div>

            <div class="brand-panel__content">
                <div class="brand-header">
                    <img class="brand-logo" src="/images/SHOU_logo.svg" alt="上海海洋大学校徽" />
                    <span class="brand-name">上海海洋大学</span>
                </div>

                <div class="brand-copy">
                    <p class="eyebrow">Aqua Health Intelligence</p>
                    <h1 class="brand-title">Fish Med Agent</h1>
                    <p class="brand-description">面向水产健康管理的智能诊断平台，结合图像识别与养殖语境，让疾病排查更快进入有效判断。</p>
                </div>
            </div>
        </section>

        <section class="auth-panel">
            <div class="auth-card">
                <div class="auth-card__header">
                    <p class="auth-card__eyebrow">Secure Sign In</p>
                    <h2 class="auth-card__title">欢迎回来</h2>
                </div>

                <form class="auth-form" @submit.prevent>
                    <label class="field">
                        <span class="field__label">用户名或邮箱</span>
                        <input class="field__input" type="text" placeholder="请输入用户名或邮箱" />
                    </label>

                    <label class="field">
                        <span class="field__label">密码</span>
                        <input class="field__input" type="password" placeholder="请输入密码" />
                    </label>

                    <div class="auth-form__meta">
                        <label class="checkbox">
                            <input class="checkbox__input" type="checkbox" />
                            <span class="checkbox__box"></span>
                            <span class="checkbox__label">记住我</span>
                        </label>

                        <a class="auth-link">忘记密码</a>
                    </div>

                    <button class="auth-button" type="submit">登录</button>
                </form>

            </div>
        </section>
    </div>
</template>

<style scoped>
:global(body) {
    margin: 0;
}

:global(*) {
    box-sizing: border-box;
}

.login-page {
    --deep-ocean: #062b45;
    --tide-blue: #0b5f89;
    --sea-mist: #eaf6fb;
    --foam-white: #f7fcff;
    --ocean-blue: #0e7fb0;
    --reef-blue: #0a6a9c;
    --deep-slate: #102a43;
    --slate-80: rgba(16, 42, 67, 0.8);
    --slate-52: rgba(16, 42, 67, 0.52);
    --card-shadow: rgba(3, 36, 58, 0.18) 0px 12px 40px 0px;
    min-height: 100vh;
    display: grid;
    grid-template-columns: minmax(0, 1.08fr) minmax(0, 0.92fr);
    background: radial-gradient(circle at top left, rgba(88, 196, 229, 0.08), transparent 28%), linear-gradient(135deg, #dff0f7 0%, #eff8fc 42%, #f7fcff 100%);
    color: var(--deep-slate);
    font-family: 'SF Pro Text', 'SF Pro Icons', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

.brand-panel {
    position: relative;
    overflow: hidden;
    background:
        radial-gradient(circle at 16% 18%, rgba(88, 196, 229, 0.2), transparent 24%), radial-gradient(circle at 78% 24%, rgba(88, 196, 229, 0.12), transparent 20%),
        linear-gradient(160deg, #083452 0%, var(--deep-ocean) 48%, #0a577f 100%);
}

.brand-panel::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(4, 29, 45, 0.08) 0%, rgba(4, 29, 45, 0.2) 100%);
    pointer-events: none;
}

.brand-panel__content {
    position: relative;
    z-index: 2;
    min-height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    gap: 32px;
    padding: 40px clamp(28px, 5vw, 72px) 44px;
}

.brand-panel__glow {
    position: absolute;
    border-radius: 999px;
    filter: blur(8px);
    pointer-events: none;
}

.brand-panel__glow--top {
    top: -120px;
    right: -40px;
    width: 320px;
    height: 320px;
    background: radial-gradient(circle, rgba(167, 232, 249, 0.28), rgba(88, 196, 229, 0.02) 70%);
}

.brand-panel__glow--bottom {
    bottom: -180px;
    left: -60px;
    width: 420px;
    height: 420px;
    background: radial-gradient(circle, rgba(88, 196, 229, 0.16), rgba(88, 196, 229, 0) 72%);
}

.brand-scene {
    position: absolute;
    inset: 0;
    z-index: 1;
    pointer-events: none;
}

.brand-scene__art {
    width: 100%;
    height: 100%;
    opacity: 0.92;
}

.brand-header {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    width: fit-content;
    padding: 6px 12px;
    border-radius: 14px;
    border: 1px solid rgba(247, 252, 255, 0.24);
    background: rgba(247, 252, 255, 0.72);
    box-shadow: 0 12px 24px rgba(3, 36, 58, 0.12);
    backdrop-filter: blur(10px);
    color: var(--deep-slate);
}

.brand-logo {
    width: 28px;
    height: 28px;
    object-fit: contain;
    flex: 0 0 auto;
}

.brand-name,
.eyebrow,
.brand-description,
.auth-card__eyebrow,
.field__label,
.checkbox__label,
.auth-link {
    font-family: 'SF Pro Text', 'SF Pro Icons', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

.brand-name {
    font-size: 0.9rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--deep-slate);
}

.brand-copy {
    max-width: 560px;
    display: grid;
    gap: 16px;
    margin-top: auto;
    padding: 28px 30px 30px;
    border: 1px solid rgba(247, 252, 255, 0.14);
    border-radius: 28px;
    background: linear-gradient(180deg, rgba(10, 48, 72, 0.52) 0%, rgba(8, 39, 60, 0.28) 100%);
    box-shadow: inset 0 1px 0 rgba(247, 252, 255, 0.08);
    backdrop-filter: blur(10px);
}

.eyebrow,
.auth-card__eyebrow {
    margin: 0;
    color: rgba(247, 252, 255, 0.72);
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

.brand-title,
.auth-card__title {
    font-family: 'SF Pro Display', 'SF Pro Icons', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

.brand-title {
    margin: 0;
    color: var(--foam-white);
    font-size: clamp(2.65rem, 4.8vw, 4.2rem);
    font-weight: 600;
    line-height: 1.08;
    letter-spacing: -0.04em;
}

.brand-description {
    margin: 0;
    color: rgba(247, 252, 255, 0.68);
    font-size: 1rem;
    line-height: 1.7;
    letter-spacing: -0.01em;
    max-width: 31rem;
}

.auth-panel {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px;
}

.auth-card {
    width: min(460px, 100%);
    padding: clamp(28px, 4vw, 40px);
    border: 1px solid rgba(14, 127, 176, 0.08);
    border-radius: 24px;
    background: linear-gradient(180deg, rgba(247, 252, 255, 0.98) 0%, rgba(234, 246, 251, 0.95) 100%);
    box-shadow: var(--card-shadow);
}

.auth-card__header {
    display: grid;
    gap: 12px;
    margin-bottom: 28px;
}

.auth-card__eyebrow {
    color: rgba(10, 106, 156, 0.7);
}

.auth-card__title {
    margin: 0;
    color: var(--deep-slate);
    font-size: clamp(2rem, 3vw, 2.5rem);
    font-weight: 600;
    line-height: 1.1;
    letter-spacing: -0.04em;
}



.auth-form {
    display: grid;
    gap: 18px;
}

.field {
    display: grid;
    gap: 8px;
}

.field__label {
    color: var(--deep-slate);
    font-size: 0.92rem;
    font-weight: 600;
    letter-spacing: -0.02em;
}

.field__input {
    width: 100%;
    min-height: 52px;
    padding: 0 16px;
    border: 1px solid rgba(14, 127, 176, 0.12);
    border-radius: 14px;
    background: #f1f9fd;
    color: var(--deep-slate);
    font-size: 1rem;
    outline: none;
    transition:
        border-color 160ms ease,
        box-shadow 160ms ease,
        background-color 160ms ease,
        transform 160ms ease;
}

.field__input::placeholder {
    color: var(--slate-52);
}

.field__input:hover {
    border-color: rgba(14, 127, 176, 0.24);
    background: #f7fcff;
}

.field__input:focus {
    border-color: var(--ocean-blue);
    box-shadow: 0 0 0 4px rgba(14, 127, 176, 0.14);
    background: var(--foam-white);
}

.auth-form__meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
}

.checkbox {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    user-select: none;
}

.checkbox__input {
    position: absolute;
    opacity: 0;
    pointer-events: none;
}

.checkbox__box {
    width: 18px;
    height: 18px;
    border: 1.5px solid rgba(14, 127, 176, 0.28);
    border-radius: 6px;
    background: rgba(247, 252, 255, 0.92);
    transition:
        background-color 160ms ease,
        border-color 160ms ease,
        box-shadow 160ms ease;
}

.checkbox__label {
    color: var(--slate-80);
    font-size: 0.95rem;
    letter-spacing: -0.01em;
}

.checkbox__input:focus-visible + .checkbox__box {
    box-shadow: 0 0 0 4px rgba(14, 127, 176, 0.14);
    border-color: var(--ocean-blue);
}

.checkbox__input:checked + .checkbox__box {
    border-color: var(--ocean-blue);
    background: linear-gradient(135deg, var(--ocean-blue) 0%, #1692c7 100%);
    box-shadow: inset 0 0 0 4px rgba(247, 252, 255, 0.92);
}

.auth-link {
    color: var(--reef-blue);
    font-size: 0.92rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    text-decoration: none;
    transition: color 160ms ease;
}

.auth-link:hover {
    color: var(--ocean-blue);
}

.auth-link:focus-visible,
.auth-button:focus-visible {
    outline: 2px solid var(--ocean-blue);
    outline-offset: 3px;
}

.auth-button {
    min-height: 54px;
    border: 1px solid transparent;
    border-radius: 14px;
    background: linear-gradient(135deg, var(--ocean-blue) 0%, #1590c5 100%);
    color: var(--foam-white);
    font-size: 1.02rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    cursor: pointer;
    transition:
        transform 160ms ease,
        box-shadow 160ms ease,
        filter 160ms ease;
    box-shadow: 0 14px 30px rgba(14, 127, 176, 0.2);
}

.auth-button:hover {
    filter: brightness(1.03);
    transform: translateY(-1px);
}

.auth-button:active {
    transform: translateY(0);
    box-shadow: 0 10px 24px rgba(14, 127, 176, 0.16);
}

@media (max-width: 960px) {
    .login-page {
        grid-template-columns: 1fr;
    }

    .brand-panel__content {
        gap: 24px;
        padding: 28px 20px 24px;
    }

    .brand-copy {
        gap: 14px;
        padding: 22px 20px 24px;
    }

    .brand-title {
        font-size: clamp(2.2rem, 9vw, 3.3rem);
    }

    .auth-panel {
        padding: 20px 20px 28px;
        margin-top: -6px;
    }

    .auth-card {
        width: 100%;
        border-radius: 22px;
    }
}

@media (max-width: 640px) {
    .brand-copy {
        border-radius: 22px;
    }

    .auth-form__meta {
        flex-direction: column;
        align-items: flex-start;
    }

    .auth-link {
        padding-left: 28px;
    }
}
</style>
