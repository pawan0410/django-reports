from django.db import models

# Create your models here.


class Status(models.Model):
    original_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Status'


class StatusGroup(models.Model):
    name = models.CharField(max_length=255)
    status_id = models.ManyToManyField(Status)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Resource(models.Model):
    original_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class ResourceGroup(models.Model):
    name = models.CharField(max_length=255)
    resource_id = models.ManyToManyField(Resource)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)




