app.views.Viewport = Ext.extend(Ext.Panel, {
  fullscreen: true,
  layout: 'card',
  cardSwitchAnimation: 'slide',
  initComponent: function() {
    Ext.apply(app.views, {
      start: new app.views.Start,
      login: new app.views.Login,
      assortment: new app.views.ItemList,
      shop: new app.views.Shop,
      static: new Ext.Panel({
        id: 'static',
        scroll: 'vertical',
        tpl: '<div class="static-page">{contents}</div>',
        dockedItems: [
          {
            xtype: 'toolbar',
            items: [app.helpers.backToStart]
          }
        ]
      })
    });
    Ext.apply(this, {
      items: [app.views.start, app.views.login, app.views.assortment, app.views.shop, app.views.static]
    });
    return app.views.Viewport.superclass.initComponent.apply(this, arguments);
  }
});