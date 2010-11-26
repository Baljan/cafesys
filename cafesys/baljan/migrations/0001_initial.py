# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Profile'
        db.create_table('baljan_profile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('mobile_phone', self.gf('django.db.models.fields.CharField')(max_length=10, null=True, blank=True)),
            ('balance', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('balance_currency', self.gf('django.db.models.fields.CharField')(default=u'SEK', max_length=5)),
            ('picture', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('show_email', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('show_profile', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('baljan', ['Profile'])

        # Adding M2M table for field friend_profiles on 'Profile'
        db.create_table('baljan_profile_friend_profiles', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_profile', models.ForeignKey(orm['baljan.profile'], null=False)),
            ('to_profile', models.ForeignKey(orm['baljan.profile'], null=False))
        ))
        db.create_unique('baljan_profile_friend_profiles', ['from_profile_id', 'to_profile_id'])

        # Adding model 'JoinGroupRequest'
        db.create_table('baljan_joingrouprequest', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.Group'])),
        ))
        db.send_create_signal('baljan', ['JoinGroupRequest'])

        # Adding model 'FriendRequest'
        db.create_table('baljan_friendrequest', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('sent_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='friendrequests_sent', to=orm['auth.User'])),
            ('sent_to', self.gf('django.db.models.fields.related.ForeignKey')(related_name='friendrequests_received', to=orm['auth.User'])),
            ('accepted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('answered_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True, blank=True)),
        ))
        db.send_create_signal('baljan', ['FriendRequest'])

        # Adding model 'TradeRequest'
        db.create_table('baljan_traderequest', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('wanted_signup', self.gf('django.db.models.fields.related.ForeignKey')(related_name='traderequests_wanted', to=orm['baljan.ShiftSignup'])),
            ('offered_signup', self.gf('django.db.models.fields.related.ForeignKey')(related_name='traderequests_offered', to=orm['baljan.ShiftSignup'])),
            ('accepted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('answered', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('baljan', ['TradeRequest'])

        # Adding model 'Semester'
        db.create_table('baljan_semester', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('start', self.gf('django.db.models.fields.DateField')(unique=True)),
            ('end', self.gf('django.db.models.fields.DateField')(unique=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=6)),
            ('signup_possible', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('baljan', ['Semester'])

        # Adding model 'ShiftCombination'
        db.create_table('baljan_shiftcombination', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('semester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['baljan.Semester'])),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=10)),
        ))
        db.send_create_signal('baljan', ['ShiftCombination'])

        # Adding M2M table for field shifts on 'ShiftCombination'
        db.create_table('baljan_shiftcombination_shifts', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('shiftcombination', models.ForeignKey(orm['baljan.shiftcombination'], null=False)),
            ('shift', models.ForeignKey(orm['baljan.shift'], null=False))
        ))
        db.create_unique('baljan_shiftcombination_shifts', ['shiftcombination_id', 'shift_id'])

        # Adding model 'Shift'
        db.create_table('baljan_shift', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('semester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['baljan.Semester'])),
            ('when', self.gf('django.db.models.fields.DateField')()),
            ('span', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=True)),
            ('exam_period', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('baljan', ['Shift'])

        # Adding model 'ShiftSignup'
        db.create_table('baljan_shiftsignup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('shift', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['baljan.Shift'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('tradable', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('baljan', ['ShiftSignup'])

        # Adding model 'OnCallDuty'
        db.create_table('baljan_oncallduty', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('shift', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['baljan.Shift'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('baljan', ['OnCallDuty'])

        # Adding model 'Good'
        db.create_table('baljan_good', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('img', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('position', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal('baljan', ['Good'])

        # Adding model 'GoodCost'
        db.create_table('baljan_goodcost', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('good', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['baljan.Good'])),
            ('cost', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('currency', self.gf('django.db.models.fields.CharField')(default=u'SEK', max_length=5)),
            ('from_date', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
        ))
        db.send_create_signal('baljan', ['GoodCost'])

        # Adding model 'Order'
        db.create_table('baljan_order', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('put_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('paid', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('currency', self.gf('django.db.models.fields.CharField')(default=u'SEK', max_length=5)),
            ('accepted', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('baljan', ['Order'])

        # Adding model 'OrderGood'
        db.create_table('baljan_ordergood', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('order', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['baljan.Order'])),
            ('good', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['baljan.Good'])),
            ('count', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
        ))
        db.send_create_signal('baljan', ['OrderGood'])

        # Adding model 'RefillSeries'
        db.create_table('baljan_refillseries', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('issued', self.gf('django.db.models.fields.DateField')(default=datetime.date(2010, 11, 21))),
            ('least_valid_until', self.gf('django.db.models.fields.DateField')(default=datetime.date(2011, 11, 21))),
            ('made_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('code_count', self.gf('django.db.models.fields.PositiveIntegerField')(default=16)),
            ('code_value', self.gf('django.db.models.fields.PositiveIntegerField')(default=100)),
            ('code_currency', self.gf('django.db.models.fields.CharField')(default=u'SEK', max_length=5)),
        ))
        db.send_create_signal('baljan', ['RefillSeries'])

        # Adding model 'RefillSeriesPDF'
        db.create_table('baljan_refillseriespdf', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('refill_series', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['baljan.RefillSeries'])),
            ('generated_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('baljan', ['RefillSeriesPDF'])

        # Adding model 'BalanceCode'
        db.create_table('baljan_balancecode', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('code', self.gf('django.db.models.fields.CharField')(default='OSNUO2Md', unique=True, max_length=8)),
            ('value', self.gf('django.db.models.fields.PositiveIntegerField')(default=100)),
            ('currency', self.gf('django.db.models.fields.CharField')(default=u'SEK', max_length=5)),
            ('refill_series', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['baljan.RefillSeries'])),
            ('used_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('used_at', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
        ))
        db.send_create_signal('baljan', ['BalanceCode'])

        # Adding model 'BoardPost'
        db.create_table('baljan_boardpost', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('made', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('semester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['baljan.Semester'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('post', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('baljan', ['BoardPost'])


    def backwards(self, orm):
        
        # Deleting model 'Profile'
        db.delete_table('baljan_profile')

        # Removing M2M table for field friend_profiles on 'Profile'
        db.delete_table('baljan_profile_friend_profiles')

        # Deleting model 'JoinGroupRequest'
        db.delete_table('baljan_joingrouprequest')

        # Deleting model 'FriendRequest'
        db.delete_table('baljan_friendrequest')

        # Deleting model 'TradeRequest'
        db.delete_table('baljan_traderequest')

        # Deleting model 'Semester'
        db.delete_table('baljan_semester')

        # Deleting model 'ShiftCombination'
        db.delete_table('baljan_shiftcombination')

        # Removing M2M table for field shifts on 'ShiftCombination'
        db.delete_table('baljan_shiftcombination_shifts')

        # Deleting model 'Shift'
        db.delete_table('baljan_shift')

        # Deleting model 'ShiftSignup'
        db.delete_table('baljan_shiftsignup')

        # Deleting model 'OnCallDuty'
        db.delete_table('baljan_oncallduty')

        # Deleting model 'Good'
        db.delete_table('baljan_good')

        # Deleting model 'GoodCost'
        db.delete_table('baljan_goodcost')

        # Deleting model 'Order'
        db.delete_table('baljan_order')

        # Deleting model 'OrderGood'
        db.delete_table('baljan_ordergood')

        # Deleting model 'RefillSeries'
        db.delete_table('baljan_refillseries')

        # Deleting model 'RefillSeriesPDF'
        db.delete_table('baljan_refillseriespdf')

        # Deleting model 'BalanceCode'
        db.delete_table('baljan_balancecode')

        # Deleting model 'BoardPost'
        db.delete_table('baljan_boardpost')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'baljan.balancecode': {
            'Meta': {'ordering': "('-id', '-refill_series__id')", 'object_name': 'BalanceCode'},
            'code': ('django.db.models.fields.CharField', [], {'default': "'4GNbG3ZV'", 'unique': 'True', 'max_length': '8'}),
            'currency': ('django.db.models.fields.CharField', [], {'default': "u'SEK'", 'max_length': '5'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'refill_series': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['baljan.RefillSeries']"}),
            'used_at': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'used_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.PositiveIntegerField', [], {'default': '100'})
        },
        'baljan.boardpost': {
            'Meta': {'ordering': "('-semester__start', 'user__first_name', 'user__last_name')", 'object_name': 'BoardPost'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'post': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['baljan.Semester']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'baljan.friendrequest': {
            'Meta': {'object_name': 'FriendRequest'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'answered_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'sent_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'friendrequests_sent'", 'to': "orm['auth.User']"}),
            'sent_to': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'friendrequests_received'", 'to': "orm['auth.User']"})
        },
        'baljan.good': {
            'Meta': {'object_name': 'Good'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'position': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'baljan.goodcost': {
            'Meta': {'ordering': "['-from_date']", 'object_name': 'GoodCost'},
            'cost': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'currency': ('django.db.models.fields.CharField', [], {'default': "u'SEK'", 'max_length': '5'}),
            'from_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'good': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['baljan.Good']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'baljan.joingrouprequest': {
            'Meta': {'object_name': 'JoinGroupRequest'},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'baljan.oncallduty': {
            'Meta': {'ordering': "('-shift__when', 'shift__span')", 'object_name': 'OnCallDuty'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'shift': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['baljan.Shift']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'baljan.order': {
            'Meta': {'ordering': "['-put_at']", 'object_name': 'Order'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'default': "u'SEK'", 'max_length': '5'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'paid': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'put_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'baljan.ordergood': {
            'Meta': {'object_name': 'OrderGood'},
            'count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'good': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['baljan.Good']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'order': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['baljan.Order']"})
        },
        'baljan.profile': {
            'Meta': {'object_name': 'Profile'},
            'balance': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'balance_currency': ('django.db.models.fields.CharField', [], {'default': "u'SEK'", 'max_length': '5'}),
            'friend_profiles': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'friend_profiles_rel_+'", 'null': 'True', 'to': "orm['baljan.Profile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'mobile_phone': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'picture': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'show_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'show_profile': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'baljan.refillseries': {
            'Meta': {'ordering': "('-id',)", 'object_name': 'RefillSeries'},
            'code_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '16'}),
            'code_currency': ('django.db.models.fields.CharField', [], {'default': "u'SEK'", 'max_length': '5'}),
            'code_value': ('django.db.models.fields.PositiveIntegerField', [], {'default': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issued': ('django.db.models.fields.DateField', [], {'default': 'datetime.date(2010, 11, 21)'}),
            'least_valid_until': ('django.db.models.fields.DateField', [], {'default': 'datetime.date(2011, 11, 21)'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'made_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'baljan.refillseriespdf': {
            'Meta': {'ordering': "('-made', '-id', '-refill_series__id')", 'object_name': 'RefillSeriesPDF'},
            'generated_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'refill_series': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['baljan.RefillSeries']"})
        },
        'baljan.semester': {
            'Meta': {'object_name': 'Semester'},
            'end': ('django.db.models.fields.DateField', [], {'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '6'}),
            'signup_possible': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'start': ('django.db.models.fields.DateField', [], {'unique': 'True'})
        },
        'baljan.shift': {
            'Meta': {'ordering': "('-when', 'span')", 'object_name': 'Shift'},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'exam_period': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['baljan.Semester']"}),
            'span': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': 'True'}),
            'when': ('django.db.models.fields.DateField', [], {})
        },
        'baljan.shiftcombination': {
            'Meta': {'ordering': "('shifts__when', 'shifts__span')", 'object_name': 'ShiftCombination'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['baljan.Semester']"}),
            'shifts': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['baljan.Shift']", 'symmetrical': 'False'})
        },
        'baljan.shiftsignup': {
            'Meta': {'ordering': "('-shift__when',)", 'object_name': 'ShiftSignup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'shift': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['baljan.Shift']"}),
            'tradable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'baljan.traderequest': {
            'Meta': {'object_name': 'TradeRequest'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'answered': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'offered_signup': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'traderequests_offered'", 'to': "orm['baljan.ShiftSignup']"}),
            'wanted_signup': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'traderequests_wanted'", 'to': "orm['baljan.ShiftSignup']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['baljan']
