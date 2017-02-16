# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        key_len = 25 # search for 25, this is not the only place
        # Adding field 'Profile.private_key'
        db.add_column('baljan_profile', 'private_key', self.gf('django.db.models.fields.CharField')(default=None, null=True, unique=True, max_length=key_len), keep_default=False)

        import random
        import string
        def random_string(length):
            pool = string.letters + string.digits
            return ''.join(random.choice(pool) for dummy in range(key_len))

        def generate_private_key():
            private_key = random_string(key_len)
            while len(orm.Profile.objects.filter(private_key=private_key)) != 0:
                private_key = random_string(key_len)
            return private_key
	
	if not db.dry_run:
	        for profile in orm.Profile.objects.all():
        	    profile.private_key = generate_private_key()
	            profile.save()

        db.alter_column('baljan_profile', 'private_key', self.gf('django.db.models.fields.CharField')(null=False, unique=True, max_length=key_len))


    def backwards(self, orm):
        
        # Deleting field 'Profile.private_key'
        db.delete_column('baljan_profile', 'private_key')


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
            'code': ('django.db.models.fields.CharField', [], {'default': "'OtyyzMh1'", 'unique': 'True', 'max_length': '8'}),
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
        'baljan.oldcoffeecard': {
            'Meta': {'ordering': "('-card_id',)", 'object_name': 'OldCoffeeCard'},
            'card_id': ('django.db.models.fields.IntegerField', [], {}),
            'code': ('django.db.models.fields.IntegerField', [], {}),
            'count': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imported': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'left': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'set': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['baljan.OldCoffeeCardSet']"}),
            'time_stamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'baljan.oldcoffeecardset': {
            'Meta': {'ordering': "('-set_id',)", 'object_name': 'OldCoffeeCardSet'},
            'created': ('django.db.models.fields.DateTimeField', [], {}),
            'file': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'set_id': ('django.db.models.fields.IntegerField', [], {}),
            'time_stamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
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
            'put_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
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
            'card_id': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'friend_profiles': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'friend_profiles_rel_+'", 'null': 'True', 'to': "orm['baljan.Profile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'made': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'mobile_phone': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'picture': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'private_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'unique': 'True', 'max_length': '25'}),
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
            'issued': ('django.db.models.fields.DateField', [], {'default': 'datetime.date(2010, 12, 4)'}),
            'least_valid_until': ('django.db.models.fields.DateField', [], {'default': 'datetime.date(2011, 12, 4)'}),
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
            'span': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
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
