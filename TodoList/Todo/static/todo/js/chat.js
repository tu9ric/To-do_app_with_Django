const messageInput = document.querySelector('textarea[name="message"]');
    const attachmentTypeInput = document.querySelector('input[name="attachment_type"]');
    const replyToInput = document.querySelector('input[name="reply_to"]');
    const replyPreview = document.querySelector('[data-reply-preview]');
    const replyAuthor = document.querySelector('[data-reply-author]');
    const replyText = document.querySelector('[data-reply-text]');
    const cancelReplyButton = document.querySelector('[data-cancel-reply]');
    const uploadWrap = document.querySelector('[data-chat-upload]');
    const uploadInput = document.querySelector('input[name="upload"]');
    const attachFileButton = document.querySelector('[data-attach-file]');
    const selectedFile = document.querySelector('[data-selected-file]');
    const chatForm = document.querySelector('.chat-compose');
    const chatSendButton = document.querySelector('.chat-send-button');
    const recordVoiceButton = document.querySelector('[data-record-voice]');
    const recordCircleButton = document.querySelector('[data-record-circle]');
    const recordStatus = document.querySelector('[data-record-status]');
    const circlePreview = document.querySelector('[data-circle-preview]');
    const circlePreviewVideo = circlePreview?.querySelector('video');
    const circleCancelHint = document.querySelector('[data-circle-cancel-hint]');
    const notificationsButton = document.querySelector('[data-enable-notifications]');
    const chatPanel = document.querySelector('[data-latest-message-id]');
    const chatFeed = document.querySelector('.full-chat-feed');
    const messageMenu = document.querySelector('[data-message-menu]');
    const menuEditLink = messageMenu?.querySelector('[data-menu-edit]');
    const menuDeleteLink = messageMenu?.querySelector('[data-menu-delete]');

    document.querySelectorAll('.chat-bubble > .message-actions').forEach((actions) => {
        actions.remove();
    });
    let latestMessageId = Number(chatPanel?.dataset.latestMessageId || 0);
    let mediaRecorder = null;
    let recordedChunks = [];
    let recordingStream = null;
    let recordingKind = null;
    let requestedRecordingKind = null;
    let recordingStartedAt = 0;
    let discardRecording = false;
    let cancelRecording = false;
    let activeRecordingPointerId = null;
    let recordingPointerStartX = 0;
    const cancelSwipeDeadZone = 24;
    let chatUpdateInProgress = false;

    const recordingFormats = {
        voice: [
            { mimeType: 'audio/mp4', extension: 'm4a' },
            { mimeType: 'audio/webm;codecs=opus', extension: 'webm' },
            { mimeType: 'audio/webm', extension: 'webm' },
            { mimeType: 'audio/ogg;codecs=opus', extension: 'ogg' },
        ],
        video_circle: [
            { mimeType: 'video/mp4', extension: 'mp4' },
            { mimeType: 'video/webm;codecs=vp8,opus', extension: 'webm' },
            { mimeType: 'video/webm', extension: 'webm' },
        ],
    };

    function getSupportedRecordingFormat(kind) {
        const formats = recordingFormats[kind] || [];
        return formats.find(({ mimeType }) => MediaRecorder.isTypeSupported(mimeType)) || null;
    }

    function getCancelSwipeDistance() {
        return Math.max(150, Math.min(window.innerWidth * 0.48, 260));
    }

    function updateChatViewport() {
        if (window.innerWidth > 820) return;
        const viewportHeight = window.visualViewport?.height || window.innerHeight;
        document.documentElement.style.setProperty('--chat-viewport-height', `${viewportHeight}px`);
    }

    function scrollChatToBottom() {
        if (chatFeed) chatFeed.scrollTop = chatFeed.scrollHeight;
    }

    function resizeMessageInput() {
        if (!messageInput) return;
        messageInput.style.height = '38px';
        messageInput.style.height = `${Math.min(messageInput.scrollHeight, 104)}px`;
    }

    updateChatViewport();
    scrollChatToBottom();
    resizeMessageInput();
    messageInput?.addEventListener('input', resizeMessageInput);
    chatSendButton?.addEventListener('pointerdown', (event) => {
        if (document.activeElement === messageInput) {
            event.preventDefault();
        }
    });
    messageInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !messageMenu?.hidden) {
            event.preventDefault();
            closeMessageMenu();
            return;
        }

        if (event.key === 'Escape' && replyToInput?.value) {
            event.preventDefault();
            clearReply();
            return;
        }

        if (event.key !== 'Enter') return;

        if (event.ctrlKey) {
            event.preventDefault();
            const selectionStart = messageInput.selectionStart;
            const selectionEnd = messageInput.selectionEnd;
            messageInput.setRangeText('\n', selectionStart, selectionEnd, 'end');
            resizeMessageInput();
            return;
        }

        event.preventDefault();
        chatForm?.requestSubmit();
    });
    window.visualViewport?.addEventListener('resize', updateChatViewport);
    window.addEventListener('orientationchange', () => {
        window.setTimeout(() => {
            updateChatViewport();
            scrollChatToBottom();
        }, 150);
    });

    function updateNotificationsButton() {
        if (!notificationsButton || !('Notification' in window)) return;
        if (Notification.permission === 'granted') {
            notificationsButton.textContent = chatPanel.dataset.notificationsEnabled;
            notificationsButton.disabled = true;
        }
    }

    async function requestNotifications() {
        if (!('Notification' in window)) return;
        const permission = await Notification.requestPermission();
        if (permission === 'granted') updateNotificationsButton();
    }

    async function pollChatUpdates() {
        if (!chatPanel || chatUpdateInProgress) return;
        chatUpdateInProgress = true;
        try {
            const url = `${chatPanel.dataset.updatesUrl}?after=${latestMessageId}`;
            const response = await fetch(url, {
                credentials: 'same-origin',
                cache: 'no-store',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (!response.ok) return;

            const data = await response.json();
            appendMessages(data.messages || []);
            latestMessageId = Number(data.latest_id || latestMessageId);
        } finally {
            chatUpdateInProgress = false;
        }
    }

    notificationsButton?.addEventListener('click', requestNotifications);
    updateNotificationsButton();
    window.setInterval(pollChatUpdates, 400);
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) pollChatUpdates();
    });

    if (attachmentTypeInput && !attachmentTypeInput.value) {
        attachmentTypeInput.value = 'text';
    }

    attachFileButton?.addEventListener('click', () => uploadInput?.click());

    uploadInput?.addEventListener('change', () => {
        const file = uploadInput.files?.[0];
        if (!file) return;

        let attachmentType = '';
        if (file.type.startsWith('image/')) attachmentType = 'photo';
        if (file.type.startsWith('audio/')) attachmentType = 'voice';
        if (file.type.startsWith('video/')) attachmentType = 'video_circle';

        if (!attachmentType) {
            uploadInput.value = '';
            if (recordStatus) recordStatus.textContent = 'Choose a photo, audio, or video file.';
            return;
        }

        if (attachmentTypeInput) attachmentTypeInput.value = attachmentType;
        if (uploadWrap) uploadWrap.hidden = false;
        if (selectedFile) selectedFile.textContent = file.name;
        if (recordStatus) recordStatus.textContent = '';
    });

    const floatingVideo = document.querySelector('.floating-video-circle');
    const floatingVideoTag = floatingVideo?.querySelector('video');
    const closeFloatingVideo = floatingVideo?.querySelector('button');

    chatFeed?.addEventListener('click', (event) => {
        const videoButton = event.target.closest('.video-circle-trigger');
        if (videoButton && floatingVideo && floatingVideoTag) {
            if (suppressMediaClick) {
                event.preventDefault();
                return;
            }
            floatingVideoTag.src = videoButton.dataset.videoSrc;
            floatingVideo.hidden = false;
            floatingVideoTag.play();
            return;
        }

        const quote = event.target.closest('[data-scroll-to-message]');
        if (quote) {
            const target = document.querySelector(`[data-message-id="${quote.dataset.scrollToMessage}"]`);
            target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            target?.classList.add('chat-bubble-highlight');
            window.setTimeout(() => target?.classList.remove('chat-bubble-highlight'), 1200);
        }
    });

    closeFloatingVideo?.addEventListener('click', () => {
        if (!floatingVideo || !floatingVideoTag) return;
        floatingVideoTag.pause();
        floatingVideoTag.removeAttribute('src');
        floatingVideo.hidden = true;
    });

    async function startRecording(kind) {
        if (!navigator.mediaDevices || !window.MediaRecorder || mediaRecorder?.state === 'recording') {
            if (recordStatus) recordStatus.textContent = 'Recording is not available in this browser.';
            return;
        }

        try {
            recordingKind = kind;
            const constraints = kind === 'voice'
                ? { audio: true }
                : { video: { facingMode: 'user' }, audio: true };
            recordingStream = await navigator.mediaDevices.getUserMedia(constraints);
            if (requestedRecordingKind !== kind) {
                recordingStream.getTracks().forEach((track) => track.stop());
                recordingStream = null;
                recordingKind = null;
                if (recordStatus) recordStatus.textContent = 'Permission granted. Hold the button again to record.';
                return;
            }
            recordedChunks = [];
            const recordingFormat = getSupportedRecordingFormat(kind);
            const options = recordingFormat
                ? { mimeType: recordingFormat.mimeType }
                : {};
            mediaRecorder = new MediaRecorder(recordingStream, options);
            mediaRecorder.addEventListener('dataavailable', (event) => {
                if (event.data.size > 0) recordedChunks.push(event.data);
            });
            mediaRecorder.addEventListener('stop', sendRecordedMedia);
            mediaRecorder.start();
            recordingStartedAt = Date.now();
            discardRecording = false;
            cancelRecording = false;

            const activeButton = kind === 'voice' ? recordVoiceButton : recordCircleButton;
            activeButton?.classList.add('recording');
            if (recordStatus) {
                recordStatus.textContent = kind === 'voice'
                    ? 'Recording voice... release to send'
                    : 'Recording circle... release to send';
            }

            if (kind === 'video_circle' && circlePreview && circlePreviewVideo) {
                circlePreviewVideo.srcObject = recordingStream;
                circlePreview.hidden = false;
                circlePreview.style.setProperty('--cancel-progress', '0');
                circlePreview.style.setProperty('--preview-shift', '0px');
            }
        } catch (error) {
            recordingKind = null;
            if (recordStatus) {
                recordStatus.textContent = kind === 'voice'
                    ? 'Microphone access was denied.'
                    : 'Camera or microphone access was denied.';
            }
        }
    }

    function stopRecording({ cancel = false } = {}) {
        requestedRecordingKind = null;
        if (!mediaRecorder || mediaRecorder.state !== 'recording') return;
        cancelRecording = cancel;
        discardRecording = cancel || Date.now() - recordingStartedAt < 600;
        mediaRecorder.stop();
        recordVoiceButton?.classList.remove('recording');
        recordCircleButton?.classList.remove('recording');
        if (recordingStream) {
            recordingStream.getTracks().forEach((track) => track.stop());
            recordingStream = null;
        }
        if (circlePreviewVideo) circlePreviewVideo.srcObject = null;
        if (circlePreview) {
            circlePreview.hidden = true;
            circlePreview.style.removeProperty('--cancel-progress');
            circlePreview.style.removeProperty('--preview-shift');
        }
    }

    async function sendRecordedMedia() {
        if (discardRecording) {
            recordedChunks = [];
            recordingKind = null;
            discardRecording = false;
            if (recordStatus) {
                recordStatus.textContent = cancelRecording
                    ? 'Recording canceled.'
                    : 'Hold the button to record.';
            }
            cancelRecording = false;
            return;
        }

        if (!chatForm || recordedChunks.length === 0) {
            if (recordStatus) recordStatus.textContent = '';
            recordingKind = null;
            return;
        }

        const kind = recordingKind;
        const recordingFormat = getSupportedRecordingFormat(kind);
        const mimeType = mediaRecorder?.mimeType
            || recordingFormat?.mimeType
            || (kind === 'voice' ? 'audio/mp4' : 'video/mp4');
        const extension = recordingFormat?.extension
            || (mimeType.includes('mp4') ? (kind === 'voice' ? 'm4a' : 'mp4') : 'webm');
        const blob = new Blob(recordedChunks, { type: mimeType });
        const formData = new FormData(chatForm);
        formData.set('attachment_type', kind);
        formData.set('message', messageInput?.value || '');
        formData.set('upload', blob, `${kind}-${Date.now()}.${extension}`);

        if (recordStatus) recordStatus.textContent = 'Sending...';

        try {
            const response = await fetch(chatForm.action, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });

            if (response.ok) {
                const data = await response.json();
                appendMessages([{
                    id: data.id,
                    html: data.html,
                    is_own: true,
                }]);
                resetComposer();
            } else if (recordStatus) {
                recordStatus.textContent = 'Could not send recording.';
            }
        } finally {
            recordingKind = null;
            cancelRecording = false;
        }
    }

    function bindHoldToRecord(button, kind) {
        button?.addEventListener('selectstart', (event) => event.preventDefault());
        button?.addEventListener('dragstart', (event) => event.preventDefault());
        button?.addEventListener('touchstart', (event) => {
            event.preventDefault();
        }, { passive: false });

        button?.addEventListener('pointerdown', (event) => {
            event.preventDefault();
            window.getSelection()?.removeAllRanges();
            if (activeRecordingPointerId !== null) return;
            activeRecordingPointerId = event.pointerId;
            recordingPointerStartX = event.clientX;
            requestedRecordingKind = kind;
            startRecording(kind);
        });

        button?.addEventListener('contextmenu', (event) => event.preventDefault());
    }

    function isSelectionAllowedNode(node) {
        const element = node?.nodeType === Node.ELEMENT_NODE
            ? node
            : node?.parentElement;
        return Boolean(element?.closest('.chat-message-text, .chat-message-field'));
    }

    document.addEventListener('selectstart', (event) => {
        if (!event.target.closest('.chat-message-text, .chat-message-field')) {
            event.preventDefault();
        }
    }, { capture: true });

    document.addEventListener('selectionchange', () => {
        const selection = window.getSelection();
        if (!selection || selection.isCollapsed) return;
        if (
            isSelectionAllowedNode(selection.anchorNode)
            && isSelectionAllowedNode(selection.focusNode)
        ) {
            return;
        }
        selection.removeAllRanges();
    });

    window.addEventListener('pointermove', (event) => {
        if (
            event.pointerId !== activeRecordingPointerId
            || recordingKind !== 'video_circle'
            || !mediaRecorder
            || mediaRecorder.state !== 'recording'
        ) {
            return;
        }

        const rawDistance = Math.max(0, recordingPointerStartX - event.clientX);
        const distance = Math.max(0, rawDistance - cancelSwipeDeadZone);
        const cancelSwipeDistance = getCancelSwipeDistance();
        const progress = Math.min(distance / cancelSwipeDistance, 1);
        if (circlePreview) {
            circlePreview.style.setProperty('--cancel-progress', String(progress));
            circlePreview.style.setProperty('--preview-shift', `${-Math.min(distance * 0.45, 100)}px`);
        }

        if (progress >= 1) {
            activeRecordingPointerId = null;
            stopRecording({ cancel: true });
        }
    }, { capture: true });

    window.addEventListener('pointerup', (event) => {
        if (event.pointerId !== activeRecordingPointerId) return;
        event.preventDefault();
        activeRecordingPointerId = null;
        stopRecording();
    }, { capture: true });

    window.addEventListener('pointercancel', (event) => {
        if (event.pointerId !== activeRecordingPointerId || event.pointerType === 'touch') return;
        activeRecordingPointerId = null;
        stopRecording();
    }, { capture: true });

    window.addEventListener('blur', () => {
        if (activeRecordingPointerId === null || !mediaRecorder || mediaRecorder.state !== 'recording') return;
        activeRecordingPointerId = null;
        stopRecording();
    });

    document.addEventListener('touchend', (event) => {
        if (activeRecordingPointerId === null) return;
        const stillActive = Array.from(event.touches).some((touch) => touch.identifier === activeRecordingPointerId);
        if (!stillActive) {
            event.preventDefault();
            activeRecordingPointerId = null;
            stopRecording();
        }
    }, { passive: false, capture: true });

    bindHoldToRecord(recordVoiceButton, 'voice');
    bindHoldToRecord(recordCircleButton, 'video_circle');

    function formatLocalTimes(root = document) {
        root.querySelectorAll('.chat-message-time:not([data-localized])').forEach((element) => {
            const date = new Date(element.dateTime);
            if (Number.isNaN(date.getTime())) return;
            element.textContent = new Intl.DateTimeFormat(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            }).format(date);
            element.dataset.localized = 'true';
        });
    }

    function appendMessages(messages) {
        if (!chatFeed || messages.length === 0) return;
        const nearBottom = chatFeed.scrollHeight - chatFeed.scrollTop - chatFeed.clientHeight < 120;
        chatFeed.querySelector('.empty-state')?.remove();

        messages.forEach((message) => {
            if (document.querySelector(`[data-message-id="${message.id}"]`)) return;
            chatFeed.insertAdjacentHTML('beforeend', message.html);
            const bubble = document.querySelector(`[data-message-id="${message.id}"]`);
            bubble?.querySelector(':scope > .message-actions')?.remove();

            if (bubble && !bubble.querySelector(':scope > .chat-message-author')) {
                const author = document.createElement('strong');
                author.className = 'chat-message-author';
                author.textContent = message.author || '';
                bubble.prepend(author);
            }
            if (bubble && !bubble.querySelector('.chat-message-time')) {
                const meta = document.createElement('small');
                meta.className = 'chat-message-meta';
                const time = document.createElement('time');
                time.className = 'chat-message-time';
                time.dateTime = message.created_at;
                meta.append(time);
                bubble.append(meta);
            }
            latestMessageId = Math.max(latestMessageId, Number(message.id));

            if (
                !message.is_own
                && document.hidden
                && 'Notification' in window
                && Notification.permission === 'granted'
            ) {
                new Notification(`OurHome: ${message.author}`, {
                    body: message.message || 'New message',
                    tag: `ourhome-chat-${message.id}`,
                });
            }
        });

        formatLocalTimes(chatFeed);
        observeVideoCirclePreviews(chatFeed);
        if (nearBottom) scrollChatToBottom();
    }

    const videoPreviewObserver = 'IntersectionObserver' in window
        ? new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                const video = entry.target;
                if (entry.isIntersecting) {
                    video.play().catch(() => {});
                } else {
                    video.pause();
                }
            });
        }, { root: chatFeed, threshold: 0.35 })
        : null;

    function observeVideoCirclePreviews(root = document) {
        root.querySelectorAll('.video-circle-trigger video:not([data-preview-ready])').forEach((video) => {
            video.dataset.previewReady = 'true';
            video.muted = true;
            video.playsInline = true;
            if (videoPreviewObserver) {
                videoPreviewObserver.observe(video);
            } else {
                video.play().catch(() => {});
            }
        });
    }

    function resetComposer({ keepFocus = false } = {}) {
        if (messageInput) messageInput.value = '';
        if (uploadInput) uploadInput.value = '';
        if (attachmentTypeInput) attachmentTypeInput.value = 'text';
        if (uploadWrap) uploadWrap.hidden = true;
        if (selectedFile) selectedFile.textContent = '';
        clearReply();
        resizeMessageInput();
        if (recordStatus) recordStatus.textContent = '';
        if (keepFocus) {
            messageInput?.focus({ preventScroll: true });
        }
    }

    function selectReply(message) {
        if (!replyToInput || !replyPreview) return;
        replyToInput.value = message.dataset.messageId;
        if (replyAuthor) replyAuthor.textContent = message.dataset.replyAuthor;
        if (replyText) replyText.textContent = message.dataset.replyText;
        replyPreview.hidden = false;
        messageInput?.focus({ preventScroll: true });
    }

    function clearReply() {
        if (replyToInput) replyToInput.value = '';
        if (replyPreview) replyPreview.hidden = true;
    }

    cancelReplyButton?.addEventListener('click', clearReply);

    let menuMessage = null;
    let longPressTimer = null;
    let longPressStartX = 0;
    let longPressStartY = 0;

    function isMessageTextTarget(target) {
        return Boolean(target.closest(
            '.chat-message-text, .chat-reply-quote, strong, small, a, button, audio, video, img'
        ));
    }

    function openMessageMenu(message, clientX, clientY) {
        if (!messageMenu || !message || message.dataset.ownMessage !== 'true') return;
        closeMessageMenu();
        menuMessage = message;

        if (menuEditLink) {
            menuEditLink.hidden = !message.dataset.editUrl;
            menuEditLink.href = message.dataset.editUrl || '#';
        }
        if (menuDeleteLink) {
            menuDeleteLink.hidden = !message.dataset.deleteUrl;
            menuDeleteLink.href = message.dataset.deleteUrl || '#';
        }

        messageMenu.hidden = false;
        messageMenu.style.left = '0px';
        messageMenu.style.top = '0px';
        const menuRect = messageMenu.getBoundingClientRect();
        const margin = 8;
        const left = Math.min(
            Math.max(clientX, margin),
            window.innerWidth - menuRect.width - margin
        );
        const top = Math.min(
            Math.max(clientY, margin),
            window.innerHeight - menuRect.height - margin
        );

        messageMenu.style.left = `${left}px`;
        messageMenu.style.top = `${top}px`;
        message.classList.add('chat-bubble-menu-open');
        const firstAction = messageMenu.querySelector('a:not([hidden])');
        firstAction?.focus({ preventScroll: true });
    }

    function closeMessageMenu() {
        menuMessage?.classList.remove('chat-bubble-menu-open');
        menuMessage = null;
        if (messageMenu) messageMenu.hidden = true;
    }

    function cancelLongPress() {
        window.clearTimeout(longPressTimer);
        longPressTimer = null;
    }

    chatFeed?.addEventListener('contextmenu', (event) => {
        const message = event.target.closest('[data-message-id]');
        if (!message || message.dataset.ownMessage !== 'true') return;
        event.preventDefault();
        openMessageMenu(message, event.clientX, event.clientY);
    });

    chatFeed?.addEventListener('pointerdown', (event) => {
        if (event.pointerType === 'mouse' || isMessageTextTarget(event.target)) return;
        const message = event.target.closest('[data-message-id]');
        if (!message || message.dataset.ownMessage !== 'true') return;

        longPressStartX = event.clientX;
        longPressStartY = event.clientY;
        longPressTimer = window.setTimeout(() => {
            openMessageMenu(message, event.clientX, event.clientY);
            longPressTimer = null;
        }, 550);
    });

    chatFeed?.addEventListener('pointermove', (event) => {
        if (!longPressTimer) return;
        const moved = Math.hypot(
            event.clientX - longPressStartX,
            event.clientY - longPressStartY
        );
        if (moved > 12) cancelLongPress();
    });

    chatFeed?.addEventListener('pointerup', cancelLongPress);
    chatFeed?.addEventListener('pointercancel', cancelLongPress);

    document.addEventListener('pointerdown', (event) => {
        if (
            !messageMenu?.hidden
            && !event.target.closest('[data-message-menu]')
        ) {
            closeMessageMenu();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !messageMenu?.hidden) {
            closeMessageMenu();
        }
    });

    window.addEventListener('resize', closeMessageMenu);
    chatFeed?.addEventListener('scroll', closeMessageMenu, { passive: true });

    let swipedMessage = null;
    let swipeStartX = 0;
    let swipeStartY = 0;
    let suppressMediaClick = false;

    chatFeed?.addEventListener('pointerdown', (event) => {
        const interactiveTarget = event.target.closest('a, button, audio, video');
        const videoCircle = event.target.closest('.video-circle-trigger');
        if (interactiveTarget && !videoCircle) return;
        swipedMessage = event.target.closest('[data-message-id]');
        if (!swipedMessage) return;
        swipeStartX = event.clientX;
        swipeStartY = event.clientY;
    });

    chatFeed?.addEventListener('pointermove', (event) => {
        if (!swipedMessage) return;
        const isOwnMessage = swipedMessage.classList.contains('chat-bubble-own');
        const deltaX = event.clientX - swipeStartX;
        const horizontal = isOwnMessage
            ? Math.max(0, -deltaX)
            : Math.max(0, deltaX);
        const vertical = Math.abs(event.clientY - swipeStartY);
        if (vertical > horizontal) {
            swipedMessage.style.removeProperty('transform');
            swipedMessage = null;
            return;
        }
        const direction = isOwnMessage ? -1 : 1;
        const offset = Math.min(horizontal * 0.55, 72) * direction;
        swipedMessage.style.transform = `translateX(${offset}px)`;
    });

    function finishReplySwipe(event) {
        if (!swipedMessage) return;
        const message = swipedMessage;
        const deltaX = event.clientX - swipeStartX;
        const distance = message.classList.contains('chat-bubble-own')
            ? -deltaX
            : deltaX;
        message.style.removeProperty('transform');
        swipedMessage = null;
        if (distance >= 70) {
            suppressMediaClick = true;
            selectReply(message);
            window.setTimeout(() => {
                suppressMediaClick = false;
            }, 350);
        }
    }

    chatFeed?.addEventListener('pointerup', finishReplySwipe);
    chatFeed?.addEventListener('pointercancel', () => {
        swipedMessage?.style.removeProperty('transform');
        swipedMessage = null;
    });

    chatForm?.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (mediaRecorder?.state === 'recording') return;
        const formData = new FormData(chatForm);
        if (!formData.get('message')?.trim() && !formData.get('upload')?.size) return;

        const response = await fetch(chatForm.action, {
            method: 'POST',
            body: formData,
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
        if (!response.ok) {
            if (recordStatus) recordStatus.textContent = 'Could not send message.';
            return;
        }
        const data = await response.json();
        appendMessages([{ id: data.id, html: data.html, is_own: true }]);
        resetComposer({ keepFocus: true });
    });

    formatLocalTimes();
    observeVideoCirclePreviews();
    pollChatUpdates();
