from django.db import models

# FIXME: Is there a way to get rid of this import and reach the Student model
# in some other way?
from liu.models import Student, Role

class Item(models.Model):
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=100)
    cost = models.IntegerField()
    initial_count = models.IntegerField(default=0)
    img = models.ImageField(upload_to='img/items')

    def __str__(self):
        return "%s - %s (%g SEK)" % (self.title, self.description, self.cost)

class OrderManager(models.Manager):
    pass

def _maybe_new_student_from_liu_id(liu_id):
    students = Student.objects.filter(liu_id=liu_id)
    if len(students) == 0:
        regular = Role.objects.filter(title='regular')[0]
        student = Student(liu_id=liu_id, role=regular)
    elif len(students) == 1:
        student = students[0]
    else:
        raise Exception('more than one student with id %s' % liu_id)

    student.save()
    return student

class Order(models.Model):
    when = models.DateTimeField(auto_now_add=True)
    student = models.ForeignKey('liu.Student')
    
    @staticmethod
    def from_liu_id(liu_id, *args, **kwargs):
        student = _maybe_new_student_from_liu_id(liu_id)
        assert not kwargs.has_key('student')
        kwargs.update({'student': student})
        return Order(*args, **kwargs)

    objects = OrderManager()

    class Meta:
        ordering = ['-when']

    def __str__(self):
        order_items = self.orderitem_set.all()
        return '%s: %s' % (self.student.liu_id, ', '.join([str(x) for x in order_items]))

class OrderItem(models.Model):
    order = models.ForeignKey(Order)
    item = models.ForeignKey(Item)
    count = models.IntegerField(default=0)

    def __str__(self):
        return "%d x %s" % (self.count, self.item.title)

class TagShown(models.Model):
    student = models.ForeignKey('liu.Student')
    when = models.DateTimeField(auto_now_add=True)
    pending = models.BooleanField(default=True)

    @staticmethod
    def from_liu_id(liu_id, *args, **kwargs):
        student = _maybe_new_student_from_liu_id(liu_id)
        assert not kwargs.has_key('student')
        kwargs.update({'student': student})
        return TagShown(student=student)

    class Meta:
        ordering = ['-when']

    def __str__(self):
        fmt = "%s at %s" % (
                self.student.liu_id, self.when.strftime('%Y-%m-%d %H:%M'))
        if self.pending:
            fmt = "%s (pending)" % fmt
        return fmt