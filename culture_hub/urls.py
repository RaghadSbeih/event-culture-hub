from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('dashboard/route/', views.dashboard_route, name='dashboard_route'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Admin management URLs
    path('admin/events/pending/', views.admin_pending_events, name='admin_pending_events'),
    path('admin/events/<int:event_id>/approve/', views.admin_approve_event, name='admin_approve_event'),
    path('admin/events/<int:event_id>/reject/', views.admin_reject_event, name='admin_reject_event'),

    path('admin/users/', views.admin_manage_users, name='admin_manage_users'),
    path('admin/bookings/<int:booking_id>/', views.booking_detail, name='booking_detail'),

    path('admin/blogs/pending/', views.admin_pending_blogs, name='admin_pending_blogs'),
    path('admin/blogs/<int:blog_id>/approve/', views.admin_approve_blog, name='admin_approve_blog'),
    path('admin/blogs/<int:blog_id>/reject/', views.admin_reject_blog, name='admin_reject_blog'),
]
