from django.db import models

# Create your models here.


class UserRecord(models.Model): 
    lines_of_code = models.IntegerField() 
    lines_of_code_per_language = models.JSONField()
    username = models.CharField(max_length=100)
    repositories = models.JSONField()
    date_requested = models.DateTimeField(auto_now_add=True)     
    def __str__(self): 
        return self.username
    
