from django.urls import path
from .views import (
    ChatMessageCreate,
    ChatMessageDelete,
    ChatMessageUpdate,
    ChatPage,
    AccountRecoveryPage,
    CoupleEventCreate,
    CoupleEventList,
    CustomLoginView,
    DashboardView,
    RegisterPage,
    SettingsPage,
    SharedFileCreate,
    SharedFileDelete,
    SharedFileList,
    SharedFileUpdate,
    TaskCreate,
    TaskDelete,
    TaskDetail,
    TaskList,
    TaskUpdate,
    chat_notifications,
    download_chat_attachment,
    download_shared_file,
)
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('todo/', TaskList.as_view(), name = "task"),
    path('task-create/', TaskCreate.as_view(), name = 'task-create'),
    path('files/', SharedFileList.as_view(), name='files'),
    path('files/upload/', SharedFileCreate.as_view(), name='file-upload'),
    path('files/<int:pk>/download/', download_shared_file, name='file-download'),
    path('files/<int:pk>/edit/', SharedFileUpdate.as_view(), name='file-edit'),
    path('files/<int:pk>/delete/', SharedFileDelete.as_view(), name='file-delete'),
    path('events/', CoupleEventList.as_view(), name='events'),
    path('events/create/', CoupleEventCreate.as_view(), name='event-create'),
    path('chat/', ChatPage.as_view(), name='chat'),
    path('chat/send/', ChatMessageCreate.as_view(), name='chat-send'),
    path('chat/<int:pk>/edit/', ChatMessageUpdate.as_view(), name='chat-message-edit'),
    path('chat/<int:pk>/delete/', ChatMessageDelete.as_view(), name='chat-message-delete'),
    path('chat/attachments/<int:pk>/', download_chat_attachment, name='chat-attachment'),
    path('chat/notifications/', chat_notifications, name='chat-notifications'),
    path('settings/', SettingsPage.as_view(), name='settings'),
    path('login/', CustomLoginView.as_view(), name = 'login'),
    path('recover-account/', AccountRecoveryPage.as_view(), name='recover-account'),
    path('logout/', LogoutView.as_view(next_page='login'), name = 'logout'),
    path('register/', RegisterPage.as_view(), name = 'register'),
    path('task/<int:pk>', TaskDetail.as_view(), name = 'task-detail'),
    path('task-update/<int:pk>', TaskUpdate.as_view(), name = 'task-update'),
    path('task-delete/<int:pk>', TaskDelete.as_view(), name = 'task-delete')
]



