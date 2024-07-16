from django.db import models

# Create your models here.
class Bank(models.Model):
    status = models.BooleanField(default=False)
    name = models.CharField(max_length=255, default=None, null=True)

    def __str__(self) -> str:
        return self.name