from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django import forms

from .models import ChatMessage, CoupleEvent, CoupleSpace, SharedFile, Task
from .security import encrypt_bytes, encrypt_text


User = get_user_model()
MAX_UPLOAD_SIZE = 50 * 1024 * 1024


class CaseInsensitiveAuthenticationForm(AuthenticationForm):
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            return username

        user = User.objects.filter(username__iexact=username).first()
        return user.username if user else username


class CaseInsensitiveUserCreationForm(UserCreationForm):
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username__iexact=username).exists():
            raise ValidationError('A user with that username already exists.')
        return username


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'category', 'complete']
        labels = {
            'title': 'Task',
            'description': 'Details',
            'category': 'Area',
            'complete': 'Done',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class SharedFileForm(forms.ModelForm):
    upload = forms.FileField(label='File')

    class Meta:
        model = SharedFile
        fields = ['title', 'category', 'favorite', 'note']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_upload(self):
        upload = self.cleaned_data['upload']
        if upload.size > MAX_UPLOAD_SIZE:
            raise ValidationError('File size must be 50 MB or less.')
        return upload

    def save(self, commit=True):
        instance = super().save(commit=False)
        upload = self.cleaned_data['upload']
        instance.file_name = upload.name
        instance.content_type = getattr(upload, 'content_type', '') or ''
        instance.size = upload.size
        instance.data = upload.read()
        if not instance.title:
            instance.title = upload.name

        if commit:
            instance.save()
        return instance


class SharedFileUpdateForm(forms.ModelForm):
    class Meta:
        model = SharedFile
        fields = ['title', 'category', 'favorite', 'note']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 4}),
        }


class CoupleEventForm(forms.ModelForm):
    class Meta:
        model = CoupleEvent
        fields = ['title', 'event_date', 'remind', 'notes']
        widgets = {
            'event_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }


class ChatMessageForm(forms.ModelForm):
    upload = forms.FileField(label='Attachment', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['attachment_type'].required = False

    class Meta:
        model = ChatMessage
        fields = ['message', 'attachment_type']
        labels = {
            'message': '',
            'attachment_type': 'Attachment type',
        }
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Write a note, meal report, plan, or tiny love letter...',
            }),
            'attachment_type': forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        message = (cleaned_data.get('message') or '').strip()
        upload = self.files.get('upload')
        attachment_type = cleaned_data.get('attachment_type') or ChatMessage.TEXT
        cleaned_data['attachment_type'] = attachment_type

        if attachment_type != ChatMessage.TEXT and not upload:
            raise ValidationError('Attach a file for this message type.')
        if attachment_type == ChatMessage.TEXT and not message:
            raise ValidationError('Write a message or choose an attachment type.')
        if upload and upload.size > MAX_UPLOAD_SIZE:
            raise ValidationError('Attachment size must be 50 MB or less.')

        if upload and attachment_type == ChatMessage.PHOTO and not upload.content_type.startswith('image/'):
            raise ValidationError('Photo messages must use an image file.')
        if upload and attachment_type == ChatMessage.VOICE and not upload.content_type.startswith('audio/'):
            raise ValidationError('Voice messages must use an audio file.')
        if upload and attachment_type == ChatMessage.VIDEO_CIRCLE and not upload.content_type.startswith('video/'):
            raise ValidationError('Video circles must use a video file.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.message = encrypt_text(instance.message)
        upload = self.files.get('upload')

        if upload:
            instance.file_name = upload.name
            instance.content_type = getattr(upload, 'content_type', '') or ''
            instance.size = upload.size
            instance.data = encrypt_bytes(upload.read())

        if commit:
            instance.save()
        return instance


class CoupleSpaceForm(forms.ModelForm):
    class Meta:
        model = CoupleSpace
        fields = ['name']
        labels = {
            'name': 'Space name',
        }


class AddSpaceMemberForm(forms.Form):
    username = forms.CharField(label='Username', max_length=150)

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if not User.objects.filter(username__iexact=username).exists():
            raise ValidationError('User with this username was not found.')
        return username
