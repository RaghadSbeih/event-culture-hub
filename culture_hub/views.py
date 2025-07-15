import bcrypt
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.contrib import messages

from .models import User, Profile, Event, EventBooking, Payment, Blog, Category

# ──────────────── Decorators ──────────────── #

def login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.session.get('user_role') != 'admin':
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper

# ──────────────── Public Views ──────────────── #

def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

def terms_privacy(request):
    return render(request, 'terms_privacy.html')

def register(request):
    if request.session.get('user_id'):
        if request.session.get('user_role') == 'admin':
            return redirect('admin_dashboard')
        else:
            return redirect('user_dashboard')

    errors = {}
    form_data = {}
    if request.method == 'POST':
        errors = User.objects.registration_validator(request.POST)
        form_data = request.POST.dict()
        # Remove passwords from form_data for security reasons
        form_data.pop('password', None)
        form_data.pop('confirm_password', None)

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
                city=request.POST.get('city', ''),
                phone_number=request.POST.get('phone_number', ''),
            )
            # Log the user in by setting session variables
            request.session['user_id'] = user.id
            request.session['user_role'] = (
                'admin' if user.is_admin else 'organizer' if user.is_organizer else 'user'
            )
            request.session['username'] = user.username
            print('DEBUG REGISTER SESSION:', dict(request.session))
            # Redirect to the correct dashboard
            if user.is_admin:
                return redirect('admin_dashboard')
            else:
                return redirect('user_dashboard')
    return render(request, 'register.html', {'errors': errors, 'form_data': form_data})

def login_view(request):
    if request.session.get('user_id'):
        if request.session.get('user_role') == 'admin':
            return redirect('admin_dashboard')
        else:
            return redirect('user_dashboard')

    errors = {}
    form_data = {}
    if request.method == 'POST':
        errors = User.objects.login_validator(request.POST)
        form_data = request.POST.dict()
        form_data.pop('password', None)

        if not errors:
            user = User.objects.get(email=request.POST['email'])

            # Check if user is active
            if not user.is_active:
                errors['inactive'] = "Your account is deactivated. Please contact admin."
            else:
                request.session['user_id'] = user.id
                request.session['user_role'] = (
                    'admin' if user.is_admin else 'organizer' if user.is_organizer else 'user'
                )
                request.session['username'] = user.username

                return redirect('admin_dashboard' if user.is_admin else 'user_dashboard' if user.is_organizer else 'home')

    return render(request, 'login.html', {'errors': errors, 'form_data': form_data})

def logout_view(request):
    request.session.flush()
    return redirect('home')

@login_required
def user_dashboard(request):
    user = User.objects.get(id=request.session['user_id'])

    user_bookings = EventBooking.objects.filter(user=user).select_related('event').order_by('-created_at')[:5]
    
    context = {
        'user': user,
        'user_bookings': user_bookings,
        'total_bookings': EventBooking.objects.filter(user=user).count(),
        'confirmed_bookings': EventBooking.objects.filter(user=user, status='confirmed').count(),
        'pending_bookings': EventBooking.objects.filter(user=user, status='pending').count(),
    }

    # If the user is an organizer, include their events
    if user.is_organizer:
        organizer_events = Event.objects.filter(user=user)
        context['organizer_events'] = organizer_events

    return render(request, 'user_dashboard.html', context)


# ──────────────── Admin Dashboard & Bookings ──────────────── #

@admin_required
def admin_dashboard(request):
    context = {
        'total_users': User.objects.count(),
        'total_events': Event.objects.count(),
        'total_bookings': EventBooking.objects.filter(status='confirmed').count(),
        'pending_approvals': EventBooking.objects.filter(status='pending').count(),
        'recent_users': User.objects.order_by('-date_joined')[:5],
        'recent_bookings': EventBooking.objects.select_related('event', 'user').order_by('-created_at')[:5],
    }
    return render(request, 'admin_dashboard.html', context)

@admin_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(EventBooking, id=booking_id)
    return render(request, 'booking_detail.html', {'booking': booking})

@admin_required
def booking_confirm(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(EventBooking, id=booking_id)
        booking.status = 'confirmed'
        booking.save()
        messages.success(request, 'Booking confirmed successfully.')
    return redirect('booking_detail', booking_id=booking_id)

@admin_required
def booking_cancel(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(EventBooking, id=booking_id)
        booking.status = 'cancelled'
        booking.save()
        messages.success(request, 'Booking cancelled.')
    return redirect('booking_detail', booking_id=booking_id)

# ──────────────── Organizer Dashboard ──────────────── #

@login_required
def organizer_dashboard(request):
    if request.session.get('user_role') != 'organizer':
        return redirect('home')
    user = User.objects.get(id=request.session['user_id'])
    events = Event.objects.filter(user=user)
    return render(request, 'organizer_dashboard.html', {'events': events})

# ──────────────── Admin: Events ──────────────── #

@admin_required
def admin_pending_events(request):
    pending_events = Event.objects.filter(is_approved=False)
    return render(request, 'admin_pending_events.html', {'pending_events': pending_events})

@admin_required
def admin_approve_event(request, event_id):
    if request.method == 'POST':
        event = get_object_or_404(Event, id=event_id)
        event.is_approved = True
        event.save()

        # Promote the user to organizer
        organizer = event.user
        if not organizer.is_organizer:
            organizer.is_organizer = True
            organizer.save()

        # Update session role only if the logged-in user is the organizer
        if request.session.get('user_id') == organizer.id:
            request.session['user_role'] = 'organizer'  # update session role

        messages.success(request, 'Event approved and organizer promoted (if needed).')
    return redirect('admin_pending_events')

@admin_required
def admin_reject_event(request, event_id):
    if request.method == 'POST':
        event = get_object_or_404(Event, id=event_id)
        event.delete()
        messages.error(request, 'Event rejected and deleted.')
    return redirect('admin_pending_events')

# ──────────────── Admin: Users ──────────────── #

@admin_required
def admin_manage_users(request):
    users = User.objects.all()
    return render(request, 'admin_manage_users.html', {'users': users})

# ──────────────── Admin: Blogs ──────────────── #

@admin_required
def admin_pending_blogs(request):
    pending_blogs = Blog.objects.filter(is_approved=False)
    return render(request, 'admin_pending_blogs.html', {'pending_blogs': pending_blogs})

@admin_required
def admin_approve_blog(request, blog_id):
    if request.method == 'POST':
        blog = get_object_or_404(Blog, id=blog_id)
        blog.is_approved = True
        blog.save()
        messages.success(request, 'Blog approved.')
    return redirect('admin_pending_blogs')

@admin_required
def admin_reject_blog(request, blog_id):
    if request.method == 'POST':
        blog = get_object_or_404(Blog, id=blog_id)
        blog.delete()
        messages.error(request, 'Blog rejected and deleted.')
    return redirect('admin_pending_blogs')

def dashboard_route(request):
    user_id = request.session.get('user_id')
    user_role = request.session.get('user_role')
    if not user_id:
        return redirect('login')
    if user_role == 'admin':
        return redirect('admin_dashboard')
    else:
        return redirect('user_dashboard')
    
@login_required
def create_event(request):
    if request.method == 'POST':
        user = User.objects.get(id=request.session['user_id'])
        event = Event.objects.create(
            title=request.POST['title'],
            description=request.POST['description'],
            date=request.POST['date'],
            start_time=request.POST['start_time'],
            end_time=request.POST['end_time'],
            location=request.POST['location'],
            city=request.POST['city'],
            is_ticketed='is_ticketed' in request.POST,
            category_id=request.POST['category'],
            user=user
        )
        if request.FILES.get('poster_image'):
            event.poster_image = request.FILES['poster_image']
            event.save()
        messages.success(request, 'Event submitted and awaiting admin approval.')
        return redirect('user_dashboard')  # or home
    categories = Category.objects.all()
    return render(request, 'create_event.html', {'categories': categories})

@login_required
def organizer_manage_bookings(request):
    if request.session.get('user_role') != 'organizer':
        return redirect('home')
    
    user = User.objects.get(id=request.session['user_id'])

    # Get all bookings for this organizer's events
    bookings = EventBooking.objects.select_related('event', 'user').filter(event__user=user).order_by('-created_at')

    return render(request, 'organizer_manage_bookings.html', {'bookings': bookings})

@login_required
def edit_event(request, event_id):
    user = User.objects.get(id=request.session['user_id'])
    event = get_object_or_404(Event, id=event_id, user=user)

    if request.method == 'POST':
        event.title = request.POST['title']
        event.description = request.POST['description']
        event.date = request.POST['date']
        event.start_time = request.POST['start_time']
        event.end_time = request.POST['end_time']
        event.location = request.POST['location']
        event.city = request.POST['city']
        event.is_ticketed = 'is_ticketed' in request.POST
        event.category_id = request.POST['category']
        
        if request.FILES.get('poster_image'):
            event.poster_image = request.FILES['poster_image']
        
        event.is_approved = False  # Reset approval on edit
        event.save()

        messages.success(request, 'Event updated and pending approval again.')
        return redirect('user_dashboard')

    categories = Category.objects.all()
    return render(request, 'edit_event.html', {'event': event, 'categories': categories})

@admin_required
def admin_toggle_user_active(request, user_id):
    user = get_object_or_404(User, id=user_id)
    # Prevent toggling own active status (optional safety)
    if user.id == request.session.get('user_id'):
        messages.error(request, "You cannot deactivate yourself.")
        return redirect('admin_manage_users')

    user.is_active = not user.is_active
    user.save()
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f"User '{user.username}' has been {status}.")
    return redirect('admin_manage_users')

@admin_required
def admin_toggle_organizer(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if not user.is_admin:
            user.is_organizer = not user.is_organizer
            user.save()
            if user.is_organizer:
                messages.success(request, f'{user.username} promoted to Organizer.')
            else:
                messages.success(request, f'{user.username} demoted to User.')
    return redirect('admin_manage_users')

@admin_required
def admin_delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        # Prevent deleting admins
        if user.is_admin:
            messages.error(request, "You cannot delete an admin user.")
        else:
            username = user.username
            user.delete()
            messages.success(request, f"User {username} has been deleted.")
    return redirect('admin_manage_users')