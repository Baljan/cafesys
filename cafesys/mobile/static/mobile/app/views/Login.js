app.views.Login = Ext.extend(Ext.form.FormPanel, {
  id: 'login',
  dockedItems: [
    {
      xtype: 'toolbar',
      title: i18n.start.login,
      items: [app.helpers.backToStart]
    }, {
      xtype: 'toolbar',
      dock: 'bottom',
      items: [
        {
          xtype: 'spacer'
        }, {
          id: 'loginButton',
          ui: 'confirm',
          text: i18n.login.action || 'Log in',
          handler: function() {
            return app.views.login.submit({
              headers: {
                'Content-Type': "application/x-www-form-urlencoded"
              },
              waitMsg: {
                message: i18n.login.waiting
              },
              success: function(form, result) {
                return console.log('ok', form, result);
              },
              failure: function(form, result) {
                return console.log('fail', form, result);
              }
            });
          }
        }
      ]
    }
  ],
  title: i18n.tab.login,
  url: 'api/auth/login',
  items: [
    {
      xtype: 'fieldset',
      title: i18n.login.credentials,
      instructions: i18n.login.instructions,
      items: [
        {
          name: 'username',
          label: i18n.liuId || 'Liu id',
          xtype: 'textfield'
        }, {
          name: 'password',
          label: i18n.password || 'Password',
          xtype: 'passwordfield'
        }, {
          ui: 'confirm',
          text: 'Confirm'
        }
      ]
    }
  ]
});