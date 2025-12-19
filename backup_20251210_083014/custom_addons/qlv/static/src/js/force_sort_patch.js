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

    forceSortBySequence() {
        // 1. Target only Sale Order Lines
        if (this.props.list.resModel !== 'sale.order.line') {
            return;
        }

        // 2. Check strict sort condition
        // We want to force sort by 'sequence' ASC
        const orderBy = this.props.list.orderBy || [];
        const isSortedBySequence = orderBy.length > 0 && orderBy[0].name === 'sequence';

        if (!isSortedBySequence) {
            // Force the collection to sort by sequence
            // Note: This matches the 'default_order' we set in XML, but ensures it applies dynamically
            this.props.list.sortBy('sequence');
        } else {
            // 3. Even if "configured" to sort by sequence, 
            // for One2Many NewIds, the Framework might not re-sort automatically
            // Verify if visually sorted
            const records = this.props.list.records;
            if (!records || records.length < 2) return;

            let isVisualSorted = true;
            for (let i = 0; i < records.length - 1; i++) {
                const seqA = records[i].data.sequence || 0;
                const seqB = records[i + 1].data.sequence || 0;
                if (seqA > seqB) {
                    isVisualSorted = false;
                    break;
                }
            }

            if (!isVisualSorted) {
                this.props.list.sortBy('sequence');
            }
        }
    }
});
