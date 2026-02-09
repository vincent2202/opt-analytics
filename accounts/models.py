from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    Custom user model - extend later as needed
    """
    email = models.EmailField(unique=True)
    
    # Add any custom fields here later
    # phone = models.CharField(max_length=20, blank=True, null=True)
    # company = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = 'accounts_users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.email or self.username