var i18n;
i18n = {
  liuId: 'Liu-id',
  password: 'Lösenord',
  back: 'Tillbaka',
  assortment: 'Sortiment',
  shop: {
    cart: 'Kundvagn',
    pick: 'Välj varor',
    finalize: 'Slutför',
    submit: 'Slutför'
  },
  start: {
    openclosed: 'Öppettider',
    contact: 'Kontakt',
    order: 'Beställa',
    shop: 'Handla direkt',
    highscores: 'Topplistor',
    login: 'Logga in'
  },
  login: {
    credentials: 'Inloggningsuppgifter',
    action: 'Logga in',
    waiting: 'Loggar in',
    instructions: 'Lösenordet skickas över en krypterad anslutning och sparas ej på Baljans servrar.'
  },
  toolbar: {
    unauthed: 'Ej inloggad'
  },
  tab: {
    about: 'Om',
    login: 'Logga in',
    title: {
      about: 'Om',
      account: 'Konto',
      work: 'Jobb'
    }
  }
};
Ext.regApplication({
  name: 'app',
  launch: function() {
    this.launched = true;
    return this.mainLaunch();
  },
  mainLaunch: function() {
    return this.views.viewport = new this.views.Viewport;
  }
});
Ext.ns('app.helpers');
Ext.apply(app.helpers, {
  backToStart: {
    text: i18n.back,
    ui: 'back',
    handler: function() {
      return app.views.viewport.setActiveItem('start', {
        type: 'slide',
        direction: 'right'
      });
    }
  }
});