from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('terms_Privacy/', views.terms_privacy, name='terms_privacy'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('dashboard/route/', views.dashboard_route, name='dashboard_route'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('organizer/dashboard/', views.organizer_dashboard, name='organizer_dashboard'),
    path('profile/settings/', views.profile_settings, name='profile_settings'),

    # Admin management URLs
    path('admin/events/pending/', views.admin_pending_events, name='admin_pending_events'),
    path('admin/events/<int:event_id>/approve/', views.admin_approve_event, name='admin_approve_event'),
    path('admin/events/<int:event_id>/reject/', views.admin_reject_event, name='admin_reject_event'),

    path('admin/users/<int:user_id>/toggle/', views.admin_toggle_user_active, name='admin_toggle_user_active'),
    path('admin/users/<int:user_id>/toggle_organizer/', views.admin_toggle_organizer, name='admin_toggle_organizer'),
    path('admin/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    
    path('admin/users/', views.admin_manage_users, name='admin_manage_users'),
    path('admin/bookings/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('admin/bookings/<int:booking_id>/confirm/', views.booking_confirm, name='booking_confirm'),
    path('admin/bookings/<int:booking_id>/cancel/', views.booking_cancel, name='booking_cancel'),

    path('admin/blogs/pending/', views.admin_pending_blogs, name='admin_pending_blogs'),
    path('admin/blogs/<int:blog_id>/approve/', views.admin_approve_blog, name='admin_approve_blog'),
    path('admin/blogs/<int:blog_id>/reject/', views.admin_reject_blog, name='admin_reject_blog'),

    path('event/create/', views.create_event, name='create_event'),
    path('event/<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('events/', views.event_list, name='event_list'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    path('event/<int:event_id>/book/', views.book_event, name='book_event'),
    path('event/<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('event/<int:event_id>/add_comment/', views.add_comment, name='add_comment'),

    path('organizer/bookings/<int:event_id>/', views.organizer_manage_bookings, name='organizer_manage_bookings'),
    path('organizer/bookings/<int:booking_id>/confirm/', views.organizer_confirm_booking, name='organizer_confirm_booking'),
    path('organizer/bookings/<int:booking_id>/cancel/', views.organizer_cancel_booking, name='organizer_cancel_booking'),

    path('manage-bookings/', views.user_manage_bookings, name='user_manage_bookings'),
    path('manage-bookings/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('blogs/', views.blog_list, name='blog_list'),
    path('blogs/submit/', views.blog_submit, name='blog_submit'),
    path('blogs/submit/success/', views.blog_submit_success, name='blog_submit_success'),
    path('blogs/<int:blog_id>/', views.blog_detail, name='blog_detail'),
    path('blogs/<int:blog_id>/delete/', views.delete_blog, name='delete_blog'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),

]
