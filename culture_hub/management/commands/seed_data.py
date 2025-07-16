from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.files.base import ContentFile
from django.conf import settings
import os
import random
import bcrypt
from culture_hub.models import User, Profile, Category, Event, EventBooking, Payment, Comment, NewsletterSubscriber, Blog

CITIES = [
    "Jerusalem (Al-Quds)", "Ramallah", "Gaza", "Hebron (Al-Khalil)", "Nablus", "Bethlehem",
    "Jericho", "Jenin", "Tulkarm", "Qalqilya", "Haifa", "Jaffa (Yafa)", "Acre (Akka)", "Nazareth (Al-Nasirah)"
]
CATEGORIES = [
    "Music & Concerts", "Art Exhibitions", "Theatre & Plays", "Film Screenings", "Historical Tours",
    "Heritage Workshops", "Food & Culinary", "Festivals", "Literature & Books", "Lectures & Talks",
    "Markets & Bazaars", "Kids & Family", "Charity & Volunteer", "Conferences & Tech", "Other"
]
EVENT_TITLES = [
    "Palestinian Music Night", "Art for Peace", "Theatre of Hope", "Cinema Under the Stars",
    "Old City Heritage Walk", "Traditional Cooking Workshop", "Spring Festival", "Book Lovers Gathering",
    "Tech for Palestine", "Family Fun Day"
]

PROFILE_PIC_PATH = os.path.join(settings.BASE_DIR, 'culture_hub/static/img/logo.png')
POSTER_IMG_PATH = os.path.join(settings.BASE_DIR, 'culture_hub/static/img/logo.png')

class Command(BaseCommand):
    help = 'Seed the database with test/demo data for all models.'

    def handle(self, *args, **kwargs):
        # Users
        if not User.objects.filter(username='admin').exists():
            admin_pw = bcrypt.hashpw('adminpass'.encode(), bcrypt.gensalt()).decode()
            admin = User.objects.create(username='admin', email='admin@hub.com', password=admin_pw, is_admin=True)
            Profile.objects.create(user=admin, first_name='Admin', last_name='User', city='Ramallah', phone_number='123456789')
        else:
            admin = User.objects.get(username='admin')
        if not User.objects.filter(username='organizer').exists():
            org_pw = bcrypt.hashpw('organizerpass'.encode(), bcrypt.gensalt()).decode()
            organizer = User.objects.create(username='organizer', email='organizer@hub.com', password=org_pw, is_organizer=True)
            Profile.objects.create(user=organizer, first_name='Organizer', last_name='User', city='Jerusalem (Al-Quds)', phone_number='987654321')
        else:
            organizer = User.objects.get(username='organizer')
        for i in range(1, 6):
            uname = f'user{i}'
            if not User.objects.filter(username=uname).exists():
                pw = bcrypt.hashpw(f'user{i}pass'.encode(), bcrypt.gensalt()).decode()
                user = User.objects.create(username=uname, email=f'{uname}@hub.com', password=pw)
                Profile.objects.create(user=user, first_name=f'User{i}', last_name='Test', city=random.choice(CITIES), phone_number=f'0599{i}12345')
        # Profile pictures
        for profile in Profile.objects.all():
            if not profile.profile_picture:
                with open(PROFILE_PIC_PATH, 'rb') as f:
                    profile.profile_picture.save(f'{profile.user.username}_profile.png', ContentFile(f.read()), save=True)
        # Categories
        for cat in CATEGORIES:
            Category.objects.get_or_create(name=cat)
        # Events
        all_users = list(User.objects.filter(is_admin=False))
        all_cats = list(Category.objects.all())
        for i, title in enumerate(EVENT_TITLES):
            if not Event.objects.filter(title=title).exists():
                user = random.choice(all_users)
                cat = all_cats[i % len(all_cats)]
                event = Event.objects.create(
                    title=title,
                    description=f"Description for {title}.",
                    date=timezone.now().date() + timezone.timedelta(days=i),
                    start_time=timezone.now().time(),
                    end_time=(timezone.now() + timezone.timedelta(hours=2)).time(),
                    location=f"Venue {i+1}",
                    city=random.choice(CITIES),
                    is_ticketed=bool(i % 2),
                    is_approved=True,
                    is_featured=bool(i % 3 == 0),
                    category=cat,
                    user=user
                )
                with open(POSTER_IMG_PATH, 'rb') as f:
                    event.poster_image.save(f'event_{i+1}_poster.png', ContentFile(f.read()), save=True)
        # Bookings
        all_events = list(Event.objects.all())
        for user in User.objects.filter(is_admin=False):
            for event in random.sample(all_events, min(3, len(all_events))):
                if not EventBooking.objects.filter(user=user, event=event).exists():
                    booking = EventBooking.objects.create(
                        user=user,
                        event=event,
                        booking_time=timezone.now(),
                        status=random.choice(['pending', 'confirmed', 'cancelled'])
                    )
                    # Payment
                    if event.is_ticketed and booking.status == 'confirmed':
                        Payment.objects.get_or_create(
                            booking=booking,
                            defaults={
                                'amount': random.randint(20, 100),
                                'status': 'paid',
                                'payment_method': 'credit_card',
                                'payment_reference': f'REF{random.randint(10000,99999)}',
                                'ticket_code': f'TICKET{random.randint(1000,9999)}',
                                'paid_at': timezone.now()
                            }
                        )
        # Comments
        for event in all_events:
            for user in User.objects.filter(is_admin=False):
                if not Comment.objects.filter(user=user, event=event).exists():
                    if random.random() < 0.5:
                        Comment.objects.create(
                            user=user,
                            event=event,
                            rating=random.randint(3, 5),
                            comment=f"Great event: {event.title}!"
                        )
        # Newsletter Subscribers
        for i in range(1, 6):
            email = f'subscriber{i}@hub.com'
            NewsletterSubscriber.objects.get_or_create(email=email)
        # Blogs
        for i in range(1, 6):
            title = f"Blog Post {i}"
            if not Blog.objects.filter(title=title).exists():
                Blog.objects.create(
                    title=title,
                    content=f"This is the content for blog post {i}.",
                    is_approved=bool(i % 2),
                    user=random.choice(all_users)
                )
        self.stdout.write(self.style.SUCCESS('Database seeded with test/demo data.')) 