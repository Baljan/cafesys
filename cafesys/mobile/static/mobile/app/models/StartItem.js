app.models.StartStructure = {
  items: [
    {
      id: 'openclosed',
      text: i18n.start.openclosed,
      type: 'static'
    }, {
      id: 'assortment',
      text: i18n.assortment,
      type: 'view'
    }, {
      id: 'shop',
      text: i18n.start.shop,
      type: 'view'
    }, {
      id: 'order',
      text: i18n.start.order,
      type: 'static'
    }, {
      id: 'highscores',
      text: i18n.start.highscores,
      type: 'static'
    }, {
      id: 'contact',
      text: i18n.start.contact,
      type: 'static'
    }, {
      id: 'login',
      text: i18n.start.login,
      type: 'view'
    }
  ]
};
app.models.StartItem = Ext.regModel("app.models.StartItem", {
  fields: [
    {
      name: 'id',
      type: 'string'
    }, {
      name: 'text',
      type: 'string'
    }, {
      name: 'type',
      type: 'string'
    }
  ]
});
app.stores.starts = new Ext.data.Store({
  autoLoad: true,
  model: 'app.models.StartItem',
  data: app.models.StartStructure,
  proxy: {
    type: 'memory',
    reader: {
      type: 'json',
      root: 'items'
    }
  }
});