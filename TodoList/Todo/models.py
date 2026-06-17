from django.db import models
from django.contrib.auth.models import User
from .security import decrypt_text


class CoupleSpace(models.Model):
    name = models.CharField(max_length=120)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_spaces')
    members = models.ManyToManyField(User, related_name='couple_spaces', blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    space = models.ForeignKey(CoupleSpace, on_delete=models.CASCADE, null=True, blank=True, related_name='tasks')
    title = models.CharField(max_length=200, null=True)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    complete = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or ''

    class Meta:
        ordering = ['complete']


class SharedFile(models.Model):
    DOCUMENT = 'document'
    PHOTO = 'photo'
    GENERAL = 'general'

    CATEGORY_CHOICES = [
        (DOCUMENT, 'Document'),
        (PHOTO, 'Photo'),
        (GENERAL, 'General'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    space = models.ForeignKey(CoupleSpace, on_delete=models.CASCADE, null=True, blank=True, related_name='files')
    title = models.CharField(max_length=200)
    file_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveIntegerField(default=0)
    data = models.BinaryField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default=GENERAL)
    favorite = models.BooleanField(default=False)
    note = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-favorite', '-created']

    def __str__(self):
        return self.title


class CoupleEvent(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    space = models.ForeignKey(CoupleSpace, on_delete=models.CASCADE, null=True, blank=True, related_name='events')
    title = models.CharField(max_length=200)
    event_date = models.DateField()
    remind = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['event_date', 'title']

    def __str__(self):
        return self.title


class ChatMessage(models.Model):
    TEXT = 'text'
    PHOTO = 'photo'
    VOICE = 'voice'
    VIDEO_CIRCLE = 'video_circle'

    ATTACHMENT_CHOICES = [
        (TEXT, 'Text'),
        (PHOTO, 'Photo'),
        (VOICE, 'Voice'),
        (VIDEO_CIRCLE, 'Video circle'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    space = models.ForeignKey(CoupleSpace, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    message = models.TextField(blank=True)
    attachment_type = models.CharField(max_length=30, choices=ATTACHMENT_CHOICES, default=TEXT)
    file_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveIntegerField(default=0)
    data = models.BinaryField(null=True, blank=True)
    attachment = models.ForeignKey(
        SharedFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_messages',
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.display_message[:60]

    @property
    def display_message(self):
        return decrypt_text(self.message)
