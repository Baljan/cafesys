app.views.Shop = Ext.extend Ext.TabPanel, {
    id: 'shop'
    cls: 'shop'
    layout: 'fit'
    dockedItems: [{
        xtype: 'toolbar'
        title: i18n.start.shop
        items: [app.helpers.backToStart]
    }]

    initComponent: () ->
        toolbar = new Ext.Toolbar {
            dock: 'bottom'
            items: [{
                xtype: 'spacer'
            }, {
                id: 'submit'
                ui: 'confirm'
                text: i18n.shop.submit
                scope: this
            }]
        }

        costs = {}
        currency = ''
        totalCost = () ->
            total = 0
            values = form.getValues()
            _.each values, (count, id) ->
                if count == ''
                    # do nothing
                else
                    total = total + count * costs[id].cost
            return total


        onChange = (field, newVal, oldVal) ->
            total = totalCost()
            toolbar.setTitle "#{total} #{currency}"

        form = new Ext.form.FormPanel {
            id: 'form'
            xtype: 'form'
            scroll: 'vertical'
            title: i18n.shop.cart
            autoScroll: false
            defaults:
                labelWidth: '75%'
                listeners:
                    change: onChange
                    blur: (field) ->
                        if field.getValue() == ''
                            field.setValue '0'
                        onChange()
                    focus: (field) ->
                        field.setValue ''
                        onChange()
            dockedItems: [toolbar]
        }

        app.stores.items.each (record) ->
            title = Ext.util.Format.ellipsis(record.data.title, 12)
            desc = record.data.description
            costs[record.data.id] = {
                cost: record.data.current_cost_dict.cost
                currency: record.data.current_cost_dict.currency
            }
            cur = record.data.current_cost_dict.currency
            if currency != '' and cur != currency
                throw "multiple currencies"
            currency = cur

            label = [
                title,
                '<em class="description">', desc, '</em>'
            ].join ' '
            form.add {
                xtype: 'numberfield'
                value: '0'
                minValue: 0
                name: record.data.id
                label: label
            }
        form.doLayout()

        Ext.apply this, {
            items: [form]
        }

        app.views.Shop.superclass.initComponent.apply this, arguments
}


