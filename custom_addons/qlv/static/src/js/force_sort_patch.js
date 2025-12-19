/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onMounted, onPatched } from "@odoo/owl";

patch(ListRenderer.prototype, "qlv.ListRenderer", {
    setup() {
        this._super();
        onPatched(() => {
            this.forceSortBySequence();
        });
        onMounted(() => {
            this.forceSortBySequence();
        });
    },

    async forceSortBySequence() {
        // 1. Target only Sale Order Lines
        if (this.props.list.resModel !== 'sale.order.line') {
            return;
        }

        // 2. Logic to detect if sort is needed
        const orderBy = this.props.list.orderBy || [];
        const isSortedBySequence = orderBy.length > 0 && orderBy[0].name === 'sequence';
        let needSort = !isSortedBySequence;

        if (!needSort) {
            const records = this.props.list.records;
            if (records && records.length >= 2) {
                for (let i = 0; i < records.length - 1; i++) {
                    const seqA = records[i].data.sequence || 0;
                    const seqB = records[i + 1].data.sequence || 0;
                    if (seqA > seqB) {
                        needSort = true;
                        break;
                    }
                }
            }
        }

        if (needSort) {
            // 3. CAPTURE FOCUS
            // Find which record currently has focus
            let focusRecordId = null;
            const activeEl = document.activeElement;
            if (activeEl) {
                // Try to find parent row
                const row = activeEl.closest('.o_data_row');
                if (row && row.dataset.id) {
                    focusRecordId = row.dataset.id;
                }
            }

            // 4. EXECUTE SORT
            await this.props.list.sortBy('sequence');

            // 5. RESTORE FOCUS
            // If we had a focused record, try to find it again
            // Or if we just added a NEW record (usually NewId), it might be the "last created" one?
            // Actually Odoo "Add Line" puts focus on the new line. If we captured it above, we are good.

            if (focusRecordId) {
                console.log("[QLV Debug] Focus captured before sort. Record ID:", focusRecordId);

                // Polling mechanism to find the row after re-render
                // Try for up to 500ms
                const start = Date.now();
                const checkAndFocus = () => {
                    if (Date.now() - start > 500) {
                        console.warn("[QLV Debug] Focus restore timed out for Record ID:", focusRecordId);
                        return;
                    }

                    const selector = `.o_data_row[data-id="${focusRecordId}"]`;
                    const newRow = document.querySelector(selector);

                    if (newRow) {
                        console.log("[QLV Debug] Found row after sort. Restoring Focus.");

                        // Find all candidates
                        const candidates = Array.from(newRow.querySelectorAll('input, textarea, select'));

                        // Filter for the "Real" input:
                        // 1. Not a checkbox (row selector)
                        // 2. Not hidden
                        // 3. Not disabled/readonly
                        const inputToFocus = candidates.find(el => {
                            return el.type !== 'checkbox' &&
                                el.type !== 'hidden' &&
                                !el.disabled &&
                                !el.readOnly &&
                                el.offsetParent !== null; // Visible check
                        });

                        if (inputToFocus) {
                            console.log("[QLV Debug] Focusing VALID Input:", inputToFocus);
                            inputToFocus.focus();
                        } else {
                            console.log("[QLV Debug] No valid input found. Focusing Row.");
                            newRow.focus();
                        }
                    } else {
                        // Not found yet, retry next frame
                        requestAnimationFrame(checkAndFocus);
                    }
                };

                // Start polling after a microtask
                requestAnimationFrame(checkAndFocus);
            } else {
                console.log("[QLV Debug] No focus captured before sort.");
            }
        }
    }
});
