import bcrypt
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.db.models import Sum, Q
from django.contrib import messages
from django.utils import timezone
from .models import User, Profile, Event, EventBooking, Payment, Blog, Category, Comment, NewsletterSubscriber
from .forms import ProfileForm
from django.contrib.auth.decorators import login_required as django_login_required
from django.core.mail import send_mail
from django.contrib.admin.views.decorators import staff_member_required
from .forms import NewsletterForm
from django.urls import reverse

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
    # Query featured and upcoming events (approved only)
    search_query = request.GET.get('q', '').strip()
    featured_events = Event.objects.filter(
        is_approved=True,
        date__gte=timezone.now().date(),
    )
    if search_query:
        featured_events = featured_events.filter(
            Q(title__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    featured_events = featured_events.order_by('date')[:6]
    context = {
        'featured_events': featured_events,
        'search_query': search_query,
    }
    return render(request, 'home.html', context)

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
    from datetime import date, datetime
    errors = {}
    form_data = {}

    # Default categories & cities
    default_categories = [
        "Music & Concerts", "Art Exhibitions", "Theatre & Plays", "Film Screenings",
        "Historical Tours", "Heritage Workshops", "Food & Culinary", "Festivals",
        "Literature & Books", "Lectures & Talks", "Markets & Bazaars", "Kids & Family",
        "Charity & Volunteer", "Conferences & Tech", "Other"
    ]
    palestinian_cities = [
        "Jerusalem (Al-Quds)", "Ramallah", "Gaza", "Hebron (Al-Khalil)", "Nablus",
        "Bethlehem", "Jericho", "Jenin", "Tulkarm", "Qalqilya", "Haifa",
        "Jaffa (Yafa)", "Acre (Akka)", "Nazareth (Al-Nasirah)"
    ]

    # Auto-create default categories if none exist
    if not Category.objects.exists():
        for name in default_categories:
            Category.objects.get_or_create(name=name)

    categories = Category.objects.all()

    if request.method == 'POST':
        user = get_object_or_404(User, id=request.session['user_id'])
        form_data = request.POST.dict()

        # Required field validation
        required_fields = ['title', 'description', 'date', 'start_time', 'end_time', 'location', 'city', 'category']
        for field in required_fields:
            if not request.POST.get(field):
                errors[field] = f'{field.replace("_", " ").capitalize()} is required.'

        # Field-specific validations
        if 'title' not in errors and len(request.POST['title']) < 5:
            errors['title'] = 'Title must be at least 5 characters.'

        if 'description' not in errors and len(request.POST['description']) < 10:
            errors['description'] = 'Description must be at least 10 characters.'

        if 'date' not in errors:
            try:
                event_date = datetime.strptime(request.POST['date'], '%Y-%m-%d').date()
                if event_date < date.today():
                    errors['date'] = 'Date cannot be in the past.'
            except ValueError:
                errors['date'] = 'Invalid date format.'

        if 'start_time' not in errors and 'end_time' not in errors and 'date' not in errors:
            try:
                start_time = datetime.strptime(request.POST['start_time'], '%H:%M').time()
                end_time = datetime.strptime(request.POST['end_time'], '%H:%M').time()
                if event_date == date.today():
                    now = datetime.now().time()
                    if start_time <= now:
                        errors['start_time'] = 'Start time must be in the future.'
                    if end_time <= now:
                        errors['end_time'] = 'End time must be in the future.'
                if end_time <= start_time:
                    errors['end_time'] = 'End time must be after start time.'
            except ValueError:
                errors['start_time'] = 'Invalid time format.'

        # Validate category ID and fetch actual object
        category_id = request.POST.get('category')
        try:
            category = Category.objects.get(id=category_id)
        except (Category.DoesNotExist, ValueError, TypeError):
            errors['category'] = 'Invalid category selected.'

        if not errors:
            event = Event.objects.create(
                title=request.POST['title'],
                description=request.POST['description'],
                date=request.POST['date'],
                start_time=request.POST['start_time'],
                end_time=request.POST['end_time'],
                location=request.POST['location'],
                city=request.POST['city'],
                is_ticketed='is_ticketed' in request.POST,
                category=category,
                user=user
            )

            if request.FILES.get('poster_image'):
                event.poster_image = request.FILES['poster_image']
                event.save()

            messages.success(request, 'Event submitted and awaiting admin approval.')
            return redirect('user_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')

    return render(request, 'create_event.html', {
        'categories': categories,
        'cities': palestinian_cities,
        'errors': errors,
        'form_data': form_data
    })

@login_required
def organizer_manage_bookings(request):
    if request.session.get('user_role') != 'organizer':
        return redirect('home')
    
    user = User.objects.get(id=request.session['user_id'])

    # Get all bookings for this organizer's events
    bookings = EventBooking.objects.select_related('event', 'user').filter(event__user=user).order_by('-created_at')

    return render(request, 'organizer_manage_bookings.html', {'bookings': bookings})

@login_required
def organizer_confirm_booking(request, booking_id):
    booking = get_object_or_404(EventBooking, id=booking_id)
    event_id = booking.event.id
    
    booking.status = 'confirmed'
    booking.save()
    
    messages.success(request, "Booking confirmed successfully.")
    return redirect('organizer_manage_bookings', event_id=event_id)

@login_required
def organizer_cancel_booking(request, booking_id):
    booking = get_object_or_404(EventBooking, id=booking_id)
    event_id = booking.event.id  # get event id from the booking
    
    # Cancel the booking
    booking.status = 'cancelled'
    booking.save()
    
    messages.success(request, "Booking cancelled successfully.")
    
    # Redirect back to the organizer's bookings page for that event
    return redirect('organizer_manage_bookings', event_id=event_id)

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

def event_list(request):
    from django.db.models import Q
    events = Event.objects.filter(is_approved=True)
    # Filtering logic (by title, city, category, date)
    title = request.GET.get('title', '')
    city = request.GET.get('city', '')
    category = request.GET.get('category', '')
    date = request.GET.get('date', '')
    if title:
        events = events.filter(title__icontains=title)
    if city:
        events = events.filter(city__icontains=city)
    if category:
        events = events.filter(category__name__icontains=category)
    if date:
        events = events.filter(date=date)
    # For filter dropdowns
    all_cities = Event.objects.values_list('city', flat=True).distinct()
    all_categories = Category.objects.values_list('name', flat=True).distinct()
    context = {
        'events': events.order_by('date'),
        'all_cities': all_cities,
        'all_categories': all_categories,
        'selected': {'title': title, 'city': city, 'category': category, 'date': date},
    }
    return render(request, 'event_list.html', context)

@login_required
def book_event(request, event_id):
    user = User.objects.get(id=request.session['user_id'])
    event = get_object_or_404(Event, id=event_id, is_approved=True)

    # Prevent duplicate bookings
    if EventBooking.objects.filter(user=user, event=event).exists():
        messages.warning(request, "You have already booked this event.")
        return redirect('event_list')

    EventBooking.objects.create(
        user=user,
        event=event,
        booking_time=timezone.now(),
        status='confirmed'  # ✅ Automatically confirmed
    )
    messages.success(request, "Booking confirmed! See you at the event.")
    return redirect('user_dashboard')

@login_required
def user_manage_bookings(request):
    user = User.objects.get(id=request.session['user_id'])
    bookings = EventBooking.objects.filter(user=user).select_related('event').order_by('-created_at')
    return render(request, 'user_manage_bookings.html', {'bookings': bookings})

@login_required
def organizer_manage_bookings(request, event_id):
    user = User.objects.get(id=request.session['user_id'])
    if not user.is_organizer:
        return redirect('home')

    # Check the event belongs to this organizer
    event = get_object_or_404(Event, id=event_id, user=user)

    # Get bookings only for this event
    bookings = EventBooking.objects.filter(event=event).order_by('-created_at')

    context = {
        'event': event,
        'bookings': bookings,
    }
    return render(request, 'organizer_manage_bookings.html', context)

@login_required
def cancel_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(EventBooking, id=booking_id, user_id=request.session['user_id'])
        if booking.status in ['pending', 'confirmed']:
            booking.status = 'cancelled'
            booking.save()
            messages.success(request, 'Booking cancelled.')
        else:
            messages.error(request, 'Cannot cancel this booking.')
    return redirect('user_manage_bookings')

@login_required
def profile_settings(request):
    user = get_object_or_404(User, id=request.session['user_id'])
    profile, created = Profile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile_settings')
    else:
        form = ProfileForm(instance=profile)
    
    return render(request, 'profile_settings.html', {'form': form})

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id, is_approved=True)
    comments = Comment.objects.filter(event=event).select_related('user').order_by('-created_at')
    user_id = request.session.get('user_id')
    user_has_commented = False
    if user_id:
        user_has_commented = Comment.objects.filter(event=event, user_id=user_id).exists()
    context = {
        'event': event,
        'user_is_logged_in': user_id is not None,
        'comments': comments,
        'user_has_commented': user_has_commented,
    }
    return render(request, 'event_detail.html', context)

@login_required
def add_comment(request, event_id):
    event = get_object_or_404(Event, id=event_id, is_approved=True)
    user = User.objects.get(id=request.session['user_id'])
    # Prevent multiple comments per user per event
    if Comment.objects.filter(event=event, user=user).exists():
        messages.error(request, 'You have already commented on this event.')
        return redirect('event_detail', event_id=event.id)
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment_text = request.POST.get('comment', '').strip()
        errors = {}
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                errors['rating'] = 'Rating must be between 1 and 5.'
        except (TypeError, ValueError):
            errors['rating'] = 'Rating is required.'
        if not comment_text:
            errors['comment'] = 'Comment cannot be empty.'
        if errors:
            comments = Comment.objects.filter(event=event).select_related('user').order_by('-created_at')
            context = {
                'event': event,
                'user_is_logged_in': True,
                'comments': comments,
                'errors': errors,
                'form_data': {'rating': rating, 'comment': comment_text},
            }
            return render(request, 'event_detail.html', context)
        Comment.objects.create(event=event, user=user, rating=rating, comment=comment_text)
        messages.success(request, 'Comment added!')
    return redirect('event_detail', event_id=event.id)

def blog_list(request):
    blogs = Blog.objects.filter(is_approved=True).order_by('-created_at')
    return render(request, 'blog_list.html', {'blogs': blogs})

def blog_detail(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id, is_approved=True)
    return render(request, 'blog_detail.html', {'blog': blog})

@login_required
def blog_submit(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    errors = {}
    form_data = {}
    if request.method == 'POST':
        form_data = request.POST.dict()
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        image = request.FILES.get('image')
        if not title:
            errors['title'] = 'Title is required.'
        if not content:
            errors['content'] = 'Content is required.'
        if len(title) < 5:
            errors['title'] = 'Title must be at least 5 characters.'
        if len(content) < 20:
            errors['content'] = 'Content must be at least 20 characters.'
        if not errors:
            user = User.objects.get(id=user_id)
            blog = Blog.objects.create(
                title=title,
                content=content,
                user=user,
                is_approved=False
            )
            if image:
                blog.image = image
                blog.save()
            return redirect('blog_submit_success')
    return render(request, 'blog_submit.html', {'errors': errors, 'form_data': form_data})

def blog_submit_success(request):
    return render(request, 'blog_submit_success.html')

def delete_event(request, event_id):
    """Allow event owner or admin to delete an event."""
    event = get_object_or_404(Event, id=event_id)
    user_id = request.session.get('user_id')
    user_role = request.session.get('user_role')
    if not user_id:
        messages.error(request, 'You must be logged in to delete events.')
        return redirect('login')
    if user_role == 'admin' or event.user_id == user_id:
        if request.method == 'POST':
            event.delete()
            messages.success(request, 'Event deleted successfully.')
            return redirect('event_list')
        else:
            messages.error(request, 'Invalid request method.')
            return redirect('event_list')
    else:
        messages.error(request, 'You do not have permission to delete this event.')
        return redirect('event_list')


def delete_blog(request, blog_id):
    """Allow blog owner or admin to delete a blog post."""
    blog = get_object_or_404(Blog, id=blog_id)
    user_id = request.session.get('user_id')
    user_role = request.session.get('user_role')
    if not user_id:
        messages.error(request, 'You must be logged in to delete blogs.')
        return redirect('login')
    if user_role == 'admin' or blog.user_id == user_id:
        if request.method == 'POST':
            blog.delete()
            messages.success(request, 'Blog post deleted successfully.')
            return redirect('blog_list')
        else:
            messages.error(request, 'Invalid request method.')
            return redirect('blog_list')
    else:
        messages.error(request, 'You do not have permission to delete this blog post.')
        return redirect('blog_list')

@login_required
def delete_comment(request, comment_id):
    user_id = request.session.get('user_id')
    user_role = request.session.get('user_role')
    comment = get_object_or_404(Comment, id=comment_id)
    event_id = comment.event.id
    # Allow admin or comment owner
    if user_role != 'admin' and comment.user_id != user_id:
        messages.error(request, 'You do not have permission to delete this comment.')
        return redirect('event_detail', event_id=event_id)
    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Comment deleted.')
    else:
        messages.error(request, 'Invalid request method.')
    return redirect('event_detail', event_id=event_id)

def subscribe(request):
    if request.method == "POST":
        email = request.POST.get("email")
        if email and not NewsletterSubscriber.objects.filter(email=email).exists():
            NewsletterSubscriber.objects.create(email=email)
            messages.success(request, "You've been subscribed!")
        else:
            messages.warning(request, "You're already subscribed.")
    return redirect(request.META.get("HTTP_REFERER", "/"))

@staff_member_required
def send_newsletter(request):
    if request.method == "POST":
        form = NewsletterForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]
            message += "\n\nAlternatively, reply to this email with 'UNSUBSCRIBE'."

            for subscriber in NewsletterSubscriber.objects.all():
                unsubscribe_url = request.build_absolute_uri(
                    reverse('unsubscribe', args=[subscriber.unsubscribe_token])
                )
                personalized_message = (
                    f"{message}\n\nTo unsubscribe, click here: {unsubscribe_url}"
                )
                send_mail(subject, personalized_message, "from@example.com", [subscriber.email])

            messages.success(request, "Newsletter sent to all subscribers with unsubscribe links.")
            return redirect("send_newsletter")
    else:
        form = NewsletterForm()
    return render(request, "send_newsletter.html", {"form": form})


def unsubscribe(request, token):
    try:
        subscriber = NewsletterSubscriber.objects.get(unsubscribe_token=token)
        subscriber.delete()
        return HttpResponse("You have been unsubscribed.")
    except NewsletterSubscriber.DoesNotExist:
        return HttpResponse("Invalid or expired unsubscribe link.")