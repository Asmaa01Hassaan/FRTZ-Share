/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { MediaDialog } from '@web_editor/components/media_dialog/media_dialog';
import {onMounted,  useEffect,onRendered, xml } from "@odoo/owl";

import { deserializeDateTime,deserializeDate } from "@web/core/l10n/dates";
import { session } from '@web/session';
import { parseDate } from '@web/core/l10n/dates';

import { formatDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon
import { _lt } from "@web/core/l10n/translation";


export class Timer_js extends Component {
    setup(params) {
        this.ormService = useService("orm");
        this.dialogService = useService("dialog");
        var domain = ["task_Start","end_time","start_time","time_left"]
        var res=super.setup(params);
        onMounted(async() => {
        var self = this;
        var def = await self.ormService.searchRead(
            'project.task',
            [['id', '=', self.props.record.resId]],
            this.domain,
        ).then(function (result) {
                var currentDate = new Date();
                self.duration = 0;
                result.forEach(function (data) {
                    self.duration += data.end_time ?
                        self._getDateDifference(data.start_time, data.end_time) :
                        self._getDateDifference(new Date(data.start_time), currentDate);
                });
        });
        self.test_hour = 0;
        self.test_min = 0;
        self._startTimeCounter();
        });
        return res   
    }
    destroy() {
        this._super.apply(this, arguments);
        clearTimeout(this.timer);
    }
    _getDateDifference(dateStart, dateEnd) {
        const timeDifferenceInMilliseconds = new Date(dateEnd).getTime() - new Date(dateStart).getTime();
        return timeDifferenceInMilliseconds;

    }
    _startTimeCounter() {
        var self = this;
        if (self.props.record.data.task_Start) {
            self.timer = setTimeout(function () {
                self.duration += 1000;
                self._startTimeCounter();
            }, 1000);
        } else {
        }
        const hours = Math.floor(self.duration / (1000 * 60 * 60));
        const minutes = Math.floor((self.duration % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((self.duration % (1000 * 60)) / 1000);

        
        if (seconds == 59){
            self.test_min +=1
        }
        if (minutes == 59){
            self.test_hour +=1
        }
        const text = `${String(self.test_hour).padStart(2, '0')}:${String(self.test_min).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

        let timer_field = this.__owl__.bdom.el.querySelector('span');
        timer_field.innerHTML = text;

    }
    
}
Timer_js.template = "bi_all_in_one_project_management_system.timer";

export const timer_js = {
    component: Timer_js,
};


registry.category("fields").add("timer_concept", timer_js);
