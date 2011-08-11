app.views.Start = Ext.extend(Ext.Panel, {
  id: 'start',
  title: i18n.tab.about,
  layout: 'fit',
  dockedItems: [
    {
      xtype: 'toolbar',
      title: 'Baljan'
    }
  ],
  items: [
    {
      xtype: 'list',
      store: app.stores.starts,
      itemTpl: '{text}',
      listeners: {
        itemtap: function(view, idx, item, ev) {
          var record;
          record = view.getRecord(item);
          if (record.data.type === 'static') {
            app.views.viewport.setLoading(true);
            return Ext.Ajax.request({
              url: 'static/' + record.data.id,
              success: function(resp, opts) {
                var dock;
                app.views.viewport.setLoading(false);
                dock = app.views.static.dockedItems.items[0];
                dock.setTitle(record.data.text);
                app.views.static.update({
                  contents: resp.responseText
                });
                return app.views.viewport.setActiveItem('static', {
                  type: 'slide',
                  direction: 'left'
                });
              },
              failure: function(resp, opts) {
                console.log('failed', resp, opts);
                return app.views.viewport.setLoading(false);
              }
            });
          } else if (record.data.type === 'view') {
            console.log(record.data.id);
            return app.views.viewport.setActiveItem(record.data.id, {
              type: 'slide',
              direction: 'left'
            });
          }
        }
      }
    }
  ],
  initComponent: function() {
    return app.views.Start.superclass.initComponent.apply(this, arguments);
  }
});