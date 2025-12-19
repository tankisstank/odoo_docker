/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";

patch(WebClient.prototype, "qlv.WebClient", {
    setup() {
        this._super();
        this.title.setParts({ zopenerp: "QLV" });
    },
});
