from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from datetime import date

from .models import ChatMessage, CoupleEvent, CoupleSpace, SharedFile, Task


class TaskViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.other_user = User.objects.create_user(username='bob', password='pass12345')
        self.space = CoupleSpace.objects.create(name='Alice and Bob', owner=self.user)
        self.space.members.add(self.user)
        self.other_space = CoupleSpace.objects.create(name='Bob private', owner=self.other_user)
        self.other_space.members.add(self.other_user)
        self.task = Task.objects.create(user=self.user, space=self.space, title='Buy milk')
        self.done_task = Task.objects.create(user=self.user, space=self.space, title='Done task', complete=True)
        self.other_task = Task.objects.create(user=self.other_user, space=self.other_space, title='Private task')

    def test_task_list_requires_login(self):
        response = self.client.get(reverse('task'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_task_list_only_shows_current_user_tasks(self):
        self.client.login(username='alice', password='pass12345')

        response = self.client.get(reverse('task'))

        self.assertContains(response, self.task.title)
        self.assertContains(response, self.done_task.title)
        self.assertNotContains(response, self.other_task.title)
        self.assertEqual(response.context['count'], 1)

    def test_search_filters_current_user_tasks(self):
        self.client.login(username='alice', password='pass12345')

        response = self.client.get(reverse('task'), {'search-area': 'milk'})

        self.assertContains(response, self.task.title)
        self.assertNotContains(response, self.done_task.title)
        self.assertEqual(response.context['search_input'], 'milk')
        self.assertEqual(response.context['count'], 1)

    def test_status_filter_shows_only_completed_tasks(self):
        self.client.login(username='alice', password='pass12345')

        response = self.client.get(reverse('task'), {'status': 'completed'})

        self.assertContains(response, self.done_task.title)
        self.assertNotContains(response, self.task.title)
        self.assertEqual(response.context['status_filter'], 'completed')

    def test_category_filter_shows_only_matching_tasks(self):
        self.task.category = 'Home'
        self.task.save()
        self.done_task.category = 'Work'
        self.done_task.save()
        self.client.login(username='alice', password='pass12345')

        response = self.client.get(reverse('task'), {'category': 'Home'})

        self.assertContains(response, self.task.title)
        self.assertNotContains(response, self.done_task.title)
        self.assertEqual(response.context['category_filter'], 'Home')

    def test_user_cannot_update_another_users_task(self):
        self.client.login(username='alice', password='pass12345')

        response = self.client.get(reverse('task-update', args=[self.other_task.id]))

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_delete_another_users_task(self):
        self.client.login(username='alice', password='pass12345')

        response = self.client.get(reverse('task-delete', args=[self.other_task.id]))

        self.assertEqual(response.status_code, 404)


class RegisterPageTests(TestCase):
    def test_authenticated_user_is_redirected_from_register_page(self):
        User.objects.create_user(username='alice', password='pass12345')
        self.client.login(username='alice', password='pass12345')

        response = self.client.get(reverse('register'))

        self.assertRedirects(response, reverse('dashboard'))

    def test_register_rejects_case_insensitive_duplicate_username(self):
        User.objects.create_user(username='Artem', password='pass12345')

        response = self.client.post(reverse('register'), {
            'username': 'artem',
            'password1': 'StrongPass123',
            'password2': 'StrongPass123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A user with that username already exists.')

    def test_register_shows_password_validation_errors(self):
        response = self.client.post(reverse('register'), {
            'username': 'hello',
            'password1': 'helloworld',
            'password2': 'helloworld',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This password is too common.')
        self.assertFalse(User.objects.filter(username='hello').exists())


class LoginPageTests(TestCase):
    def test_login_is_case_insensitive_for_username(self):
        User.objects.create_user(username='Artem', password='pass12345')

        response = self.client.post(reverse('login'), {
            'username': 'artem',
            'password': 'pass12345',
        })

        self.assertRedirects(response, reverse('dashboard'))


class CoupleHomeFeatureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='kate', password='pass12345')
        self.client.login(username='kate', password='pass12345')

    def test_sidebar_modes_render(self):
        urls = [
            reverse('dashboard'),
            reverse('task'),
            reverse('files'),
            reverse('chat'),
            reverse('events'),
            reverse('settings'),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'OurHome')

    def test_settings_save_theme_and_language(self):
        response = self.client.post(reverse('settings'), {
            'theme': 'dark',
            'language': 'ru',
        })

        self.assertRedirects(response, reverse('settings'))
        self.assertEqual(self.client.session['theme'], 'dark')
        self.assertEqual(self.client.session['language'], 'ru')

        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'theme-dark')
        self.assertContains(response, 'Главная')
        self.assertContains(response, 'Настройки')

        response = self.client.get(reverse('task'))
        self.assertContains(response, 'Общий список задач')
        self.assertContains(response, 'Применить')

        response = self.client.get(reverse('settings'))
        self.assertContains(response, 'Групповой режим')
        self.assertContains(response, 'Общее пространство')
        self.assertContains(response, 'Добавить пользователя')

    def test_account_profile_can_be_updated(self):
        response = self.client.post(reverse('settings'), {
            'settings_action': 'profile',
            'username': 'katya',
            'email': 'katya@example.com',
            'first_name': 'Katya',
        })

        self.assertRedirects(response, reverse('settings'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'katya')
        self.assertEqual(self.user.email, 'katya@example.com')
        self.assertEqual(self.user.first_name, 'Katya')

    def test_account_password_can_be_changed(self):
        response = self.client.post(reverse('settings'), {
            'settings_action': 'password',
            'old_password': 'pass12345',
            'new_password1': 'NewStrongPass123',
            'new_password2': 'NewStrongPass123',
        })

        self.assertRedirects(response, reverse('settings'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStrongPass123'))

        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 200)

    def test_settings_password_field_does_not_autofocus(self):
        response = self.client.get(reverse('settings'))
        password_field = response.context['password_form'].fields['old_password']

        self.assertNotIn('autofocus', password_field.widget.attrs)
        self.assertEqual(password_field.widget.attrs['autocomplete'], 'current-password')

    def test_account_can_be_deactivated_and_recovered(self):
        response = self.client.post(reverse('settings'), {
            'settings_action': 'deactivate_account',
            'password': 'pass12345',
        })

        self.assertRedirects(response, reverse('login'))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.client.login(username='kate', password='pass12345'))

        response = self.client.post(reverse('recover-account'), {
            'username': 'kate',
            'password1': 'RecoveredPass123',
            'password2': 'RecoveredPass123',
        })

        self.assertRedirects(response, reverse('login'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(self.user.check_password('RecoveredPass123'))
        self.assertTrue(self.client.login(username='kate', password='RecoveredPass123'))

    def test_group_member_can_see_shared_space_tasks(self):
        User.objects.create_user(username='temka', password='pass12345')

        self.client.post(reverse('settings'), {
            'settings_action': 'add_member',
            'username': 'temka',
        })

        space = CoupleSpace.objects.get(members=self.user)
        Task.objects.create(user=self.user, space=space, title='Shared groceries')
        self.client.logout()
        self.client.login(username='temka', password='pass12345')

        response = self.client.get(reverse('task'))

        self.assertContains(response, 'Shared groceries')
        self.assertContains(response, 'Space')

    def test_space_owner_can_remove_member(self):
        member = User.objects.create_user(username='member', password='pass12345')
        self.client.get(reverse('settings'))
        space = CoupleSpace.objects.get(owner=self.user)
        space.members.add(member)

        response = self.client.post(reverse('settings'), {
            'settings_action': 'remove_member',
            'member_id': member.id,
        })

        self.assertRedirects(response, reverse('settings'))
        self.assertFalse(space.members.filter(id=member.id).exists())
        self.assertTrue(space.members.filter(id=self.user.id).exists())

    def test_space_member_cannot_remove_another_member(self):
        member = User.objects.create_user(username='member', password='pass12345')
        other_member = User.objects.create_user(username='other-member', password='pass12345')
        self.client.get(reverse('settings'))
        space = CoupleSpace.objects.get(owner=self.user)
        space.members.add(member, other_member)
        self.client.logout()
        self.client.login(username='member', password='pass12345')

        response = self.client.post(reverse('settings'), {
            'settings_action': 'remove_member',
            'member_id': other_member.id,
        })

        self.assertRedirects(response, reverse('settings'))
        self.assertTrue(space.members.filter(id=other_member.id).exists())

    def test_space_owner_cannot_remove_themselves(self):
        self.client.get(reverse('settings'))
        space = CoupleSpace.objects.get(owner=self.user)

        response = self.client.post(reverse('settings'), {
            'settings_action': 'remove_member',
            'member_id': self.user.id,
        })

        self.assertRedirects(response, reverse('settings'))
        self.assertTrue(space.members.filter(id=self.user.id).exists())

    def test_shared_file_can_be_uploaded_and_downloaded(self):
        upload = SimpleUploadedFile(
            'ticket.txt',
            b'flight details',
            content_type='text/plain',
        )

        response = self.client.post(reverse('file-upload'), {
            'title': 'Trip ticket',
            'category': SharedFile.DOCUMENT,
            'favorite': 'on',
            'note': 'For the airport',
            'upload': upload,
        })

        self.assertRedirects(response, reverse('files'))
        shared_file = SharedFile.objects.get(title='Trip ticket')
        self.assertEqual(shared_file.owner, self.user)
        self.assertEqual(bytes(shared_file.data), b'flight details')

        download = self.client.get(reverse('file-download', args=[shared_file.id]))
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.content, b'flight details')

    def test_shared_file_can_be_deleted_from_active_space(self):
        response = self.client.post(reverse('file-upload'), {
            'title': 'Old ticket',
            'category': SharedFile.DOCUMENT,
            'note': '',
            'upload': SimpleUploadedFile('old.txt', b'old data', content_type='text/plain'),
        })
        self.assertRedirects(response, reverse('files'))
        shared_file = SharedFile.objects.get(title='Old ticket')

        response = self.client.post(reverse('file-delete', args=[shared_file.id]))

        self.assertRedirects(response, reverse('files'))
        self.assertFalse(SharedFile.objects.filter(id=shared_file.id).exists())

    def test_user_cannot_delete_file_from_another_space(self):
        other_user = User.objects.create_user(username='other', password='pass12345')
        other_space = CoupleSpace.objects.create(name='Other home', owner=other_user)
        other_space.members.add(other_user)
        shared_file = SharedFile.objects.create(
            owner=other_user,
            space=other_space,
            title='Private file',
            file_name='private.txt',
            content_type='text/plain',
            size=7,
            data=b'private',
        )

        response = self.client.post(reverse('file-delete', args=[shared_file.id]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(SharedFile.objects.filter(id=shared_file.id).exists())

    def test_shared_file_category_can_be_updated(self):
        self.client.post(reverse('file-upload'), {
            'title': 'Kitchen photo',
            'category': SharedFile.GENERAL,
            'note': '',
            'upload': SimpleUploadedFile('kitchen.jpg', b'image data', content_type='image/jpeg'),
        })
        shared_file = SharedFile.objects.get(title='Kitchen photo')

        response = self.client.post(reverse('file-edit', args=[shared_file.id]), {
            'title': 'Kitchen photo',
            'category': SharedFile.PHOTO,
            'favorite': 'on',
            'note': 'For renovation ideas',
        })

        self.assertRedirects(response, reverse('files'))
        shared_file.refresh_from_db()
        self.assertEqual(shared_file.category, SharedFile.PHOTO)
        self.assertTrue(shared_file.favorite)

        response = self.client.get(reverse('files'), {'category': SharedFile.PHOTO})
        self.assertContains(response, 'Kitchen photo')

    def test_event_can_be_created(self):
        response = self.client.post(reverse('event-create'), {
            'title': 'Anniversary',
            'event_date': '2026-08-10',
            'remind': 'on',
            'notes': 'Book a table',
        })

        self.assertRedirects(response, reverse('events'))
        self.assertTrue(CoupleEvent.objects.filter(
            owner=self.user,
            title='Anniversary',
            event_date=date(2026, 8, 10),
        ).exists())

    def test_chat_message_can_be_sent(self):
        response = self.client.post(reverse('chat-send'), {
            'message': 'Dinner report: soup and tea',
        })

        self.assertRedirects(response, reverse('chat'))
        message = ChatMessage.objects.get(user=self.user)
        self.assertNotEqual(message.message, 'Dinner report: soup and tea')
        self.assertEqual(message.display_message, 'Dinner report: soup and tea')

    def test_chat_aligns_own_and_partner_messages(self):
        partner = User.objects.create_user(username='partner', password='pass12345')
        space = CoupleSpace.objects.create(name='Shared chat', owner=self.user)
        space.members.add(self.user)
        space.members.add(partner)
        ChatMessage.objects.create(user=self.user, space=space, message='My note')
        ChatMessage.objects.create(user=partner, space=space, message='Partner note')

        response = self.client.get(reverse('chat'))

        self.assertContains(response, 'chat-bubble-own')
        self.assertContains(response, 'chat-bubble-partner')

    def test_chat_renders_old_messages_before_new_messages(self):
        space = CoupleSpace.objects.create(name='Chronological chat', owner=self.user)
        space.members.add(self.user)
        ChatMessage.objects.create(user=self.user, space=space, message='Older message')
        ChatMessage.objects.create(user=self.user, space=space, message='Newer message')

        response = self.client.get(reverse('chat'))
        html = response.content.decode(response.charset)

        self.assertLess(html.index('Older message'), html.index('Newer message'))

    def test_chat_notifications_return_only_partner_messages(self):
        partner = User.objects.create_user(username='partner', password='pass12345')
        space = CoupleSpace.objects.create(name='Notification chat', owner=self.user)
        space.members.add(self.user)
        space.members.add(partner)
        own_message = ChatMessage.objects.create(user=self.user, space=space, message='My own note')
        partner_message = ChatMessage.objects.create(user=partner, space=space, message='Incoming note')

        response = self.client.get(reverse('chat-notifications'), {'after': own_message.id})
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['latest_id'], partner_message.id)
        self.assertEqual(len(payload['messages']), 1)
        self.assertEqual(payload['messages'][0]['author'], 'partner')
        self.assertEqual(payload['messages'][0]['message'], 'Incoming note')

    def test_photo_message_can_be_sent_and_rendered(self):
        response = self.client.post(reverse('chat-send'), {
            'message': 'Look at this',
            'attachment_type': ChatMessage.PHOTO,
            'upload': SimpleUploadedFile('photo.jpg', b'jpeg bytes', content_type='image/jpeg'),
        })

        self.assertRedirects(response, reverse('chat'))
        message = ChatMessage.objects.get(user=self.user, attachment_type=ChatMessage.PHOTO)
        self.assertEqual(message.attachment_type, ChatMessage.PHOTO)
        self.assertNotEqual(bytes(message.data), b'jpeg bytes')
        self.assertEqual(message.display_message, 'Look at this')

        response = self.client.get(reverse('chat'))
        self.assertContains(response, reverse('chat-attachment', args=[message.id]))

        response = self.client.get(reverse('chat-attachment', args=[message.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'jpeg bytes')

    def test_user_cannot_download_chat_attachment_from_another_space(self):
        other_user = User.objects.create_user(username='chat-other', password='pass12345')
        other_space = CoupleSpace.objects.create(name='Other chat', owner=other_user)
        other_space.members.add(other_user)
        message = ChatMessage.objects.create(
            user=other_user,
            space=other_space,
            message='private',
            attachment_type=ChatMessage.PHOTO,
            file_name='private.jpg',
            content_type='image/jpeg',
            size=7,
            data=b'private',
        )

        response = self.client.get(reverse('chat-attachment', args=[message.id]))

        self.assertEqual(response.status_code, 404)

    def test_chat_message_can_be_edited_by_author(self):
        self.client.post(reverse('chat-send'), {
            'message': 'Original message',
        })
        message = ChatMessage.objects.get(user=self.user)

        response = self.client.post(reverse('chat-message-edit', args=[message.id]), {
            'message': 'Edited message',
        })

        self.assertRedirects(response, reverse('chat'))
        message.refresh_from_db()
        self.assertNotEqual(message.message, 'Edited message')
        self.assertEqual(message.display_message, 'Edited message')

        response = self.client.get(reverse('chat'))
        self.assertContains(response, 'Edited message')

    def test_chat_message_can_be_deleted_by_author(self):
        self.client.post(reverse('chat-send'), {
            'message': 'Delete me',
        })
        message = ChatMessage.objects.get(user=self.user)

        response = self.client.post(reverse('chat-message-delete', args=[message.id]))

        self.assertRedirects(response, reverse('chat'))
        self.assertFalse(ChatMessage.objects.filter(id=message.id).exists())

    def test_chat_message_cannot_be_edited_by_another_member(self):
        User.objects.create_user(username='other-member', password='pass12345')
        self.client.post(reverse('settings'), {
            'settings_action': 'add_member',
            'username': 'other-member',
        })
        self.client.post(reverse('chat-send'), {
            'message': 'Private author edit',
        })
        message = ChatMessage.objects.get(user=self.user)
        self.client.logout()
        self.client.login(username='other-member', password='pass12345')

        response = self.client.post(reverse('chat-message-edit', args=[message.id]), {
            'message': 'Hijacked',
        })

        self.assertEqual(response.status_code, 404)
        message.refresh_from_db()
        self.assertEqual(message.display_message, 'Private author edit')
