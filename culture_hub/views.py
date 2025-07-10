import bcrypt
from django.shortcuts import render, redirect
from .models import User, Profile

# Create your views here.
def home(request):
    return render(request, 'home.html')

def register(request):
    errors = {}
    if request.method == 'POST':
        errors = User.objects.registration_validator(request.POST)
        if not errors:
            hashed_pw = bcrypt.hashpw(request.POST['password'].encode(), bcrypt.gensalt()).decode()
            user = User.objects.create(
                username=request.POST['email'],
                email=request.POST['email'],
                password=hashed_pw,
            )
            Profile.objects.create(
                user=user,
                first_name=request.POST['first_name'],
                last_name=request.POST['last_name'],
            )
            return redirect('login')
    return render(request, 'register.html', {'errors': errors})

def login_view(request):
    errors = {}
    if request.method == 'POST':
        errors = User.objects.login_validator(request.POST)
        if not errors:
            try:
                user = User.objects.get(email=request.POST['email'])
                if bcrypt.checkpw(request.POST['password'].encode(), user.password.encode()):
                    # Set session or login logic here
                    return redirect('home')
                else:
                    errors['login'] = 'Invalid email or password'
            except User.DoesNotExist:
                errors['login'] = 'Invalid email or password'
    return render(request, 'login.html', {'errors': errors})

def logout_view(request):
    request.session.clear()
    return redirect('home')