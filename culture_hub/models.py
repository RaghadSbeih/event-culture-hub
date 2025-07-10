import re
import bcrypt
from django.db import models

# Create your models here.

class UserManager(models.Manager):
    def registration_validator(self, postData):
        errors = {}
        EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
        # Username validation
        if len(postData.get('username', '')) < 5:
            errors['username'] = "Username must be at least 2 characters"
        if User.objects.filter(username=postData.get('username', '')).exists():
            errors['username'] = "Username already exists"
        # Email validation
        if not EMAIL_REGEX.match(postData.get('email', '')):
            errors['email'] = "Invalid email address"
        if User.objects.filter(email=postData.get('email', '')).exists():
            errors['email'] = "Email already exists"
        # Password validation
        if len(postData.get('password', '')) < 8:
            errors['password'] = "Password must be at least 8 characters"
        if postData.get('password') != postData.get('confirm_password'):
            errors['confirm_password'] = "Passwords do not match"

        return errors

    def login_validator(self, postData):
        errors = {}
        user = User.objects.filter(email=postData.get('email')).first()
        if not user:
            errors['login'] = "Invalid email/password"
        elif not bcrypt.checkpw(postData.get('password', '').encode(), user.password.encode()):
            errors['login'] = "Invalid email/password"
        return errors

class User(models.Model):
    username = models.CharField(max_length=50)
    email = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    is_organizer = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=45)
    last_name = models.CharField(max_length=45)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=45)
    phone_number = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Category(models.Model):
    name = models.CharField(max_length=45)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    poster_image = models.TextField(blank=True, null=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    is_ticketed = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class EventBooking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    booking_time = models.DateTimeField()
    status = models.CharField(max_length=45)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Payment(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=45)
    payment_method = models.CharField(max_length=45)
    payment_reference = models.CharField(max_length=100)
    ticket_code = models.CharField(max_length=50)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    booking = models.ForeignKey(EventBooking, on_delete=models.CASCADE)

class Comment(models.Model):
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)

class NewsletterSubscriber(models.Model):
    email = models.CharField(max_length=100)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Blog(models.Model):
    title = models.CharField(max_length=45)
    content = models.TextField()
    image = models.TextField(blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
