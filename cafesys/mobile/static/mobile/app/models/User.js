app.models.User = Ext.regModel("app.models.User", {
  fields: [
    {
      name: "id",
      type: "int"
    }, {
      name: "givenName",
      type: "string"
    }, {
      name: "familyName",
      type: "string"
    }
  ]
});