app.views.ItemList = Ext.extend Ext.Panel, {
    id: 'assortment'
    cls: 'items'
    layout: 'fit'
    dockedItems: [{
        xtype: 'toolbar'
        title: i18n.assortment
        items: [app.helpers.backToStart]
    }]
    items: [{
        xtype: 'list'
        store: app.stores.items
        multiSelect: false
        singleSelect: false
        itemTpl: [
            '<span class="title">{title}</span>'
            '<em class="description">{description}</em>'
            '<span class="cost">{current_cost_dict.cost} {current_cost_dict.currency}</span>'
        ]
    }]
}

