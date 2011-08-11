app.views.Start = Ext.extend Ext.Panel, {
    id: 'start'
    title: i18n.tab.about
    layout: 'fit'
    dockedItems: [{
        xtype: 'toolbar'
        title: 'Baljan'
    }]
    items: [{
        xtype: 'list'
        store: app.stores.starts
        itemTpl: '{text}'
        listeners: {
            itemtap: (view, idx, item, ev) ->
                record = view.getRecord(item)
                if record.data.type == 'static'
                    app.views.viewport.setLoading true
                    Ext.Ajax.request {
                        url: 'static/' + record.data.id
                        success: (resp, opts) ->
                            app.views.viewport.setLoading false
                            dock = app.views.static.dockedItems.items[0]
                            dock.setTitle record.data.text
                            app.views.static.update {
                                contents: resp.responseText
                            }
                            app.views.viewport.setActiveItem 'static', {
                                type: 'slide'
                                direction: 'left'
                            }
                        failure: (resp, opts) ->
                            console.log 'failed', resp, opts
                            app.views.viewport.setLoading false
                    }
                else if record.data.type == 'view'
                    console.log record.data.id
                    app.views.viewport.setActiveItem record.data.id, {
                        type: 'slide'
                        direction: 'left'
                    }
        }
    }]
    initComponent: () ->
        app.views.Start.superclass.initComponent.apply @, arguments
}
