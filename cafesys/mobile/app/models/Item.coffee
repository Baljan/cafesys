app.models.Item = Ext.regModel "app.models.Item", {
    fields: [{
        name: 'id'
        type: 'int'
    }, {
        name: 'title'
        type: 'string'
    }, {
        name: 'description'
        type: 'string'
    }, {
        name: 'current_cost_dict'
    }]
}

app.stores.items = new Ext.data.Store {
    autoLoad: true
    model: 'app.models.Item'
    proxy: {
        type: 'ajax'
        url: 'api/items'
    }
}

