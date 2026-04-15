import { createI18n } from 'vue-i18n';
import en from './locales/en';
import zhTW from './locales/zh-TW';

// Get saved locale from localStorage or default to zh-TW
const savedLocale = localStorage.getItem('eop_locale') || 'zh-TW';

const i18n = createI18n({
    legacy: false, // Use Composition API
    locale: savedLocale,
    fallbackLocale: 'en',
    globalInjection: true,
    messages: {
        en,
        'zh-TW': zhTW,
    },
});

export default i18n;
