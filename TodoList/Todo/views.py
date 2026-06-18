from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView
from django.views.generic.edit import FormView
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from .forms import (
    CaseInsensitiveAuthenticationForm,
    CaseInsensitiveUserCreationForm,
    ChatMessageEditForm,
    ChatMessageForm,
    AccountDeleteForm,
    AccountPasswordChangeForm,
    AccountProfileForm,
    AccountRecoveryForm,
    AddSpaceMemberForm,
    CoupleEventForm,
    CoupleSpaceForm,
    SharedFileForm,
    SharedFileUpdateForm,
    TaskForm,
)
from .models import ChatMessage, CoupleEvent, CoupleSpace, SharedFile, Task
from .security import decrypt_bytes


User = get_user_model()


QUESTION_PROMPTS = [
    'What made us smile today?',
    'What should we cook together this week?',
    'Which shared plan needs a tiny next step?',
    'What is one thing we can make easier for each other?',
    'Which memory should we save in OurHome?',
]


def get_user_spaces(user):
    return CoupleSpace.objects.filter(members=user)


def get_active_space(request):
    spaces = get_user_spaces(request.user)
    space_id = request.session.get('active_space_id')
    space = spaces.filter(id=space_id).first()

    if space:
        return space

    space = spaces.first()
    if not space:
        space = CoupleSpace.objects.create(name=f"{request.user.username}'s home", owner=request.user)
        space.members.add(request.user)

    request.session['active_space_id'] = space.id
    return space


def add_space_context(request, context, active_nav):
    active_space = get_active_space(request)
    context['active_nav'] = active_nav
    context['active_space'] = active_space
    context['spaces'] = get_user_spaces(request.user)
    return active_space


class TaskList(LoginRequiredMixin, ListView):
    model = Task
    context_object_name = 'task'
    template_name = 'todo/task_list.html'

    def get_queryset(self):
        queryset = Task.objects.filter(space=get_active_space(self.request))
        search_input = self.request.GET.get('search-area', '').strip()
        status_filter = self.request.GET.get('status', '').strip()
        category_filter = self.request.GET.get('category', '').strip()

        if search_input:
            queryset = queryset.filter(title__icontains=search_input)

        if status_filter == 'active':
            queryset = queryset.filter(complete=False)
        elif status_filter == 'completed':
            queryset = queryset.filter(complete=True)

        if category_filter:
            queryset = queryset.filter(category=category_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_space = add_space_context(self.request, context, 'todo')
        user_tasks = Task.objects.filter(space=active_space)
        status_filter = self.request.GET.get('status', '').strip()

        if status_filter not in ['active', 'completed']:
            status_filter = ''

        context['count'] = user_tasks.filter(complete=False).count()
        context['completed_count'] = user_tasks.filter(complete=True).count()
        context['total_count'] = user_tasks.count()
        context['visible_count'] = context['task'].count()
        context['search_input'] = self.request.GET.get('search-area', '').strip()
        context['status_filter'] = status_filter
        context['category_filter'] = self.request.GET.get('category', '').strip()
        context['categories'] = user_tasks.exclude(
            category__isnull=True
        ).exclude(
            category=''
        ).values_list('category', flat=True).distinct().order_by('category')
        user_files = SharedFile.objects.filter(space=active_space)
        upcoming_events = CoupleEvent.objects.filter(
            space=active_space,
            event_date__gte=timezone.localdate(),
        )
        context['file_count'] = user_files.count()
        context['recent_files'] = user_files[:4]
        context['favorite_files'] = user_files.filter(favorite=True)[:4]
        context['event_count'] = upcoming_events.count()
        context['events'] = upcoming_events[:4]
        context['chat_messages'] = ChatMessage.objects.filter(space=active_space)[:5]
        context['chat_form'] = ChatMessageForm()
        context['question_prompt'] = QUESTION_PROMPTS[timezone.localdate().toordinal() % len(QUESTION_PROMPTS)]
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'todo/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_space = add_space_context(self.request, context, 'dashboard')
        user_tasks = Task.objects.filter(space=active_space)
        user_files = SharedFile.objects.filter(space=active_space)
        upcoming_events = CoupleEvent.objects.filter(
            space=active_space,
            event_date__gte=timezone.localdate(),
        )
        context['count'] = user_tasks.filter(complete=False).count()
        context['completed_count'] = user_tasks.filter(complete=True).count()
        context['total_count'] = user_tasks.count()
        context['file_count'] = user_files.count()
        context['favorite_files'] = user_files.filter(favorite=True)[:4]
        context['recent_files'] = user_files[:4]
        context['event_count'] = upcoming_events.count()
        context['events'] = upcoming_events[:4]
        context['chat_messages'] = ChatMessage.objects.filter(space=active_space)[:4]
        context['question_prompt'] = QUESTION_PROMPTS[timezone.localdate().toordinal() % len(QUESTION_PROMPTS)]
        return context


class SharedFileList(LoginRequiredMixin, ListView):
    model = SharedFile
    context_object_name = 'files'
    template_name = 'todo/shared_file_list.html'

    def get_queryset(self):
        queryset = SharedFile.objects.filter(space=get_active_space(self.request))
        category = self.request.GET.get('category', '').strip()
        favorite = self.request.GET.get('favorite', '').strip()

        if category:
            queryset = queryset.filter(category=category)
        if favorite == '1':
            queryset = queryset.filter(favorite=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_space = add_space_context(self.request, context, 'files')
        context['category_filter'] = self.request.GET.get('category', '').strip()
        context['favorite_filter'] = self.request.GET.get('favorite', '').strip()
        context['file_count'] = SharedFile.objects.filter(space=active_space).count()
        context['favorite_count'] = SharedFile.objects.filter(space=active_space, favorite=True).count()
        context['file_categories'] = SharedFile.CATEGORY_CHOICES
        return context


class CoupleEventList(LoginRequiredMixin, ListView):
    model = CoupleEvent
    context_object_name = 'events'
    template_name = 'todo/event_list.html'

    def get_queryset(self):
        return CoupleEvent.objects.filter(space=get_active_space(self.request))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_space = add_space_context(self.request, context, 'events')
        context['upcoming_count'] = CoupleEvent.objects.filter(
            space=active_space,
            event_date__gte=timezone.localdate(),
        ).count()
        return context


class ChatPage(LoginRequiredMixin, TemplateView):
    template_name = 'todo/chat.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_space = add_space_context(self.request, context, 'chat')
        latest_messages = ChatMessage.objects.filter(space=active_space).order_by('-id')[:50]
        context['chat_messages'] = list(reversed(latest_messages))
        latest_message = ChatMessage.objects.filter(space=active_space).order_by('-id').first()
        context['latest_chat_message_id'] = latest_message.id if latest_message else 0
        context['chat_form'] = ChatMessageForm()
        return context


class SettingsPage(LoginRequiredMixin, TemplateView):
    template_name = 'todo/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_space = add_space_context(self.request, context, 'settings')
        context['theme'] = self.request.session.get('theme', 'light')
        context['language'] = self.request.session.get('language', 'en')
        context['space_form'] = CoupleSpaceForm()
        context['member_form'] = AddSpaceMemberForm()
        context['profile_form'] = AccountProfileForm(instance=self.request.user)
        context['password_form'] = AccountPasswordChangeForm(self.request.user)
        context['delete_account_form'] = AccountDeleteForm(self.request.user)
        context['members'] = active_space.members.order_by('username')
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('settings_action', 'preferences')
        active_space = get_active_space(request)

        if action == 'create_space':
            form = CoupleSpaceForm(request.POST)
            if form.is_valid():
                space = form.save(commit=False)
                space.owner = request.user
                space.save()
                space.members.add(request.user)
                request.session['active_space_id'] = space.id
            return redirect('settings')

        if action == 'switch_space':
            space = get_user_spaces(request.user).filter(id=request.POST.get('space_id')).first()
            if space:
                request.session['active_space_id'] = space.id
            return redirect('settings')

        if action == 'add_member':
            form = AddSpaceMemberForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                user = User.objects.get(username__iexact=username)
                active_space.members.add(user)
            return redirect('settings')

        if action == 'remove_member':
            if active_space.owner_id == request.user.id:
                member = active_space.members.filter(id=request.POST.get('member_id')).first()
                if member and member.id != active_space.owner_id:
                    active_space.members.remove(member)
            return redirect('settings')

        if action == 'profile':
            form = AccountProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
            return redirect('settings')

        if action == 'password':
            form = AccountPasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
            return redirect('settings')

        if action == 'deactivate_account':
            form = AccountDeleteForm(request.user, request.POST)
            if form.is_valid():
                user = request.user
                user.is_active = False
                user.save(update_fields=['is_active'])
                logout(request)
                return redirect('login')
            return redirect('settings')

        theme = request.POST.get('theme', 'light')
        language = request.POST.get('language', 'en')

        if theme not in ['light', 'dark']:
            theme = 'light'
        if language not in ['en', 'ru']:
            language = 'en'

        request.session['theme'] = theme
        request.session['language'] = language
        return redirect('settings')


class TaskDetail(LoginRequiredMixin, DetailView):
    model = Task
    context_object_name = 'task'
    template_name = 'todo/task.html'

    def get_queryset(self):
        return Task.objects.filter(space=get_active_space(self.request))


class TaskCreate(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    success_url = reverse_lazy('task')

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.space = get_active_space(self.request)
        return super(TaskCreate, self).form_valid(form)


class TaskUpdate(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    success_url = reverse_lazy('task')

    def get_queryset(self):
        return Task.objects.filter(space=get_active_space(self.request))


class TaskDelete(LoginRequiredMixin, DeleteView):
    model = Task
    context_object_name = 'task'
    success_url = reverse_lazy('task')

    def get_queryset(self):
        return Task.objects.filter(space=get_active_space(self.request))


class CustomLoginView(LoginView):
    template_name = 'todo/login.html'
    authentication_form = CaseInsensitiveAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard')


class RegisterPage(FormView):
    template_name = 'todo/register.html'
    form_class = CaseInsensitiveUserCreationForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        user = form.save()
        if user is not None:
            login(self.request, user)
        return super(RegisterPage, self).form_valid(form)

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('dashboard')
        return super(RegisterPage, self).get(*args, **kwargs)


class AccountRecoveryPage(FormView):
    template_name = 'todo/account_recovery.html'
    form_class = AccountRecoveryForm
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class SharedFileCreate(LoginRequiredMixin, CreateView):
    model = SharedFile
    form_class = SharedFileForm
    template_name = 'todo/shared_file_form.html'
    success_url = reverse_lazy('files')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.instance.space = get_active_space(self.request)
        return super().form_valid(form)


class SharedFileDelete(LoginRequiredMixin, DeleteView):
    model = SharedFile
    context_object_name = 'file'
    template_name = 'todo/shared_file_confirm_delete.html'
    success_url = reverse_lazy('files')

    def get_queryset(self):
        return SharedFile.objects.filter(space=get_active_space(self.request))


class SharedFileUpdate(LoginRequiredMixin, UpdateView):
    model = SharedFile
    form_class = SharedFileUpdateForm
    template_name = 'todo/shared_file_edit_form.html'
    success_url = reverse_lazy('files')

    def get_queryset(self):
        return SharedFile.objects.filter(space=get_active_space(self.request))


class CoupleEventCreate(LoginRequiredMixin, CreateView):
    model = CoupleEvent
    form_class = CoupleEventForm
    template_name = 'todo/event_form.html'
    success_url = reverse_lazy('events')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.instance.space = get_active_space(self.request)
        return super().form_valid(form)


class ChatMessageCreate(LoginRequiredMixin, CreateView):
    model = ChatMessage
    form_class = ChatMessageForm
    success_url = reverse_lazy('chat')

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.space = get_active_space(self.request)
        return super().form_valid(form)


class ChatMessageUpdate(LoginRequiredMixin, UpdateView):
    model = ChatMessage
    form_class = ChatMessageEditForm
    template_name = 'todo/chat_message_form.html'
    success_url = reverse_lazy('chat')

    def get_queryset(self):
        return ChatMessage.objects.filter(space=get_active_space(self.request), user=self.request.user)


class ChatMessageDelete(LoginRequiredMixin, DeleteView):
    model = ChatMessage
    context_object_name = 'message'
    template_name = 'todo/chat_message_confirm_delete.html'
    success_url = reverse_lazy('chat')

    def get_queryset(self):
        return ChatMessage.objects.filter(space=get_active_space(self.request), user=self.request.user)


@login_required
def download_chat_attachment(request, pk):
    message = get_object_or_404(ChatMessage, pk=pk, space=get_active_space(request))
    if not message.data:
        return HttpResponse(status=404)

    response = HttpResponse(decrypt_bytes(message.data), content_type=message.content_type or 'application/octet-stream')
    response['Content-Disposition'] = f'inline; filename="{message.file_name}"'
    return response


@login_required
def chat_notifications(request):
    after_id = request.GET.get('after', '0')
    try:
        after_id = int(after_id)
    except ValueError:
        after_id = 0

    messages = ChatMessage.objects.filter(
        space=get_active_space(request),
        id__gt=after_id,
    ).exclude(user=request.user).order_by('id')[:10]

    payload = []
    for message in messages:
        text = message.display_message
        if not text and message.attachment_type != ChatMessage.TEXT:
            text = dict(ChatMessage.ATTACHMENT_CHOICES).get(message.attachment_type, 'Attachment')

        payload.append({
            'id': message.id,
            'author': message.user.username,
            'message': text,
            'attachment_type': message.attachment_type,
        })

    latest_message = ChatMessage.objects.filter(space=get_active_space(request)).order_by('-id').first()
    return JsonResponse({
        'latest_id': latest_message.id if latest_message else after_id,
        'messages': payload,
    })


@login_required
def download_shared_file(request, pk):
    shared_file = get_object_or_404(SharedFile, pk=pk, space=get_active_space(request))
    response = HttpResponse(bytes(shared_file.data), content_type=shared_file.content_type or 'application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{shared_file.file_name}"'
    return response
