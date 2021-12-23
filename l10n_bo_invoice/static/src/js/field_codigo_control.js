odoo.define('l10n_bo_invoice.FieldCodigoControl', (require) => {
    const Widget = require('web.AbstractField');
    const registry = require('web.field_registry');

    const WebBasicFields = require('web.basic_fields');

    const FieldCodigoControl = WebBasicFields.FieldChar.extend({
        template: 'l10n_bo_invoice.field_codigo_control',
        events: _.extend({
            'keyup': 'inputPattern',
        }, Widget.prototype.events),
        init:function() {
            this._super.apply(this, arguments);
            this.code_control="";
        },
        inputPattern(ev) {
            ev.preventDefault();
            ev.stopPropagation();
            // var input = this.$el.find(".in_code_control");
            var input = this.$el;

            if (ev.type == 'keyup' && (ev.which == $.ui.keyCode.BACKSPACE || ev.which == $.ui.keyCode.DELETE)) {
                this._setValue(input.val());
                return;
            }else if(input.val().length >= 15){
                input.val(input.val().substr(0,input.val().length-1));
                this._setValue(input.val());
                return;
            }

            this.code_control=input.val().replace(/-/g, "").replace(/[^a-zA-Z0-9]/gi,'').toUpperCase();

            this.code_control = this.countChar(this.code_control,2).join('-');

            if(this.code_control.length >= 15) {
                this.code_control = this.code_control.substr(0,this.code_control.length-1);
            }

            input.val(this.code_control);

            this._setValue(this.code_control);
        },
        countChar(str, n) {
            var ret = [];
            var i;
            var len;

            for(i = 0, len = str.length; i < len; i += n) {
                ret.push(str.substr(i, n))
            }

            return ret
        },
        updateModifiersValue: function () {
            this._super.apply(this, arguments);
            this._render();
        },
    })

    registry.add('code_control', FieldCodigoControl);
})