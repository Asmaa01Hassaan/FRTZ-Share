/** @odoo-module **/

import { localizationService } from "@web/core/l10n/localization_service";
import { patch } from "@web/core/utils/patch";

const { Settings } = luxon;

patch(localizationService, {
    async start(...args) {
        const localization = await super.start(...args);
        const locale = Settings.defaultLocale || localization.code || "";
        if (/^ar/i.test(locale)) {
            Settings.defaultNumberingSystem = "latn";
        }
        return localization;
    },
});
