import bcrypt
from django.shortcuts import render, redirect
from .models import User, Profile

# Create your views here.

def home(request):
    return render(request, 'home.html')

def register(request):
    # Redirect logged-in users away from register page
    if request.session.get('user_id'):
        return redirect('home')

    errors = {}
    if request.method == 'POST':
        errors = User.objects.registration_validator(request.POST)
        if not errors:
            hashed_pw = bcrypt.hashpw(request.POST['password'].encode(), bcrypt.gensalt()).decode()
            user = User.objects.create(
                username=request.POST['username'],
                email=request.POST['email'],
                password=hashed_pw,
            )
            Profile.objects.create(
                user=user,
                first_name=request.POST['first_name'],
                last_name=request.POST['last_name'],
                city=request.POST['city'],
                phone_number=request.POST['phone_number'],
            )
            return redirect('login')
    return render(request, 'register.html', {'errors': errors})

def login_view(request):
    # Redirect logged-in users away from login page
    if request.session.get('user_id'):
        return redirect('home')

    errors = {}
    if request.method == 'POST':
        errors = User.objects.login_validator(request.POST)
        if not errors:
            user = User.objects.get(email=request.POST['email'])
            request.session['user_id'] = user.id
            # Store user role and username in session
            if user.is_admin:
                request.session['user_role'] = 'admin'
            elif user.is_organizer:
                request.session['user_role'] = 'organizer'
            else:
                request.session['user_role'] = 'user'
            request.session['username'] = user.username

            # Redirect based on role
            if user.is_admin:
                return redirect('admin_dashboard')  # replace with your admin dashboard url name
            elif user.is_organizer:
                return redirect('organizer_dashboard')  # replace with your organizer dashboard url name
            else:
                return redirect('home')
    return render(request, 'login.html', {'errors': errors})

def logout_view(request):
    request.session.flush()
    return redirect('home')