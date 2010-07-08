from django.db import models

class Role(models.Model):
    """Board member, worker, regular, and so on."""
    title = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=100)

    def __str__(self):
        return "%s: %s" % (self.title, self.description)

class Student(models.Model):
    liu_id = models.CharField(max_length=8, unique=True)
    balance = models.IntegerField(default=0)
    role = models.ForeignKey(Role)

    def __str__(self):
        return "%s (%s)" % (self.liu_id, self.role.title)
