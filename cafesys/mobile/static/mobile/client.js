(function() {
  var i18n;
  i18n = {
    tab: {
      title: {
        about: 'Om',
        account: 'Konto',
        work: 'Jobb'
      }
    }
  };
  Ext.setup({
    onReady: function() {
      var about, account, panel, tabBar, work;
      about = new Ext.Component({
        title: i18n.tab.title.about,
        cls: 'about',
        tpl: ['<tpl for=".">', 'hej hopp', '</tpl>']
      });
      account = new Ext.Component({
        title: i18n.tab.title.account,
        cls: 'account',
        tpl: ['<tpl for=".">', 'hej hopp', '</tpl>']
      });
      work = new Ext.Component({
        title: i18n.tab.title.work,
        cls: 'work',
        tpl: ['<tpl for=".">', 'work', '</tpl>']
      });
      panel = new Ext.TabPanel({
        fullscreen: true,
        cardSwitchAnimation: 'slide',
        items: [about, account, work]
      });
      return tabBar = panel.getTabBar();
    }
  });
}).call(this);
