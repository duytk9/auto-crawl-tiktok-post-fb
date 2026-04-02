import {
  CONVERSATION_STATUS_META,
  PAGE_TOKEN_META,
  SOURCE_KIND_LABELS,
  SOURCE_PLATFORM_META,
  STATUS_LABELS,
} from './constants';

export function buildReplyAutomationDraft(pageItem) {
  return {
    comment_auto_reply_enabled: pageItem?.comment_auto_reply_enabled ?? true,
    comment_ai_prompt: pageItem?.comment_ai_prompt || '',
    message_auto_reply_enabled: pageItem?.message_auto_reply_enabled ?? false,
    message_ai_prompt: pageItem?.message_ai_prompt || '',
    message_reply_schedule_enabled: pageItem?.message_reply_schedule_enabled ?? false,
    message_reply_start_time: pageItem?.message_reply_start_time || '08:00',
    message_reply_end_time: pageItem?.message_reply_end_time || '22:00',
    message_reply_cooldown_minutes: pageItem?.message_reply_cooldown_minutes ?? 0,
  };
}

export function extractRuntimeForm(payload) {
  return {
    BASE_URL: payload?.settings?.BASE_URL?.value || '',
    FB_VERIFY_TOKEN: payload?.settings?.FB_VERIFY_TOKEN?.value || '',
    FB_APP_SECRET: payload?.settings?.FB_APP_SECRET?.value || '',
    GEMINI_API_KEY: payload?.settings?.GEMINI_API_KEY?.value || '',
    TUNNEL_TOKEN: payload?.settings?.TUNNEL_TOKEN?.value || '',
  };
}

export function cx(...values) {
  return values.filter(Boolean).join(' ');
}

export function parseMessage(payload, fallback) {
  return payload?.detail || payload?.message || fallback;
}

export function summarizeText(value, fallback = 'Chưa có nội dung.', maxLength = 110) {
  const normalized = (value || '').replace(/\s+/g, ' ').trim();
  if (!normalized) return fallback;
  if (normalized.length <= maxLength) return normalized;
  return `${normalized.slice(0, maxLength).trim()}...`;
}

export function formatDateTime(isoString, options = {}) {
  if (!isoString) return 'Chưa có';
  const date = new Date(`${isoString}${isoString.endsWith('Z') ? '' : 'Z'}`);
  return date.toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    ...options,
  });
}

export function formatRelTime(isoString) {
  if (!isoString) return 'Chưa có';
  const date = new Date(`${isoString}${isoString.endsWith('Z') ? '' : 'Z'}`);
  const diffMinutes = Math.round((date.getTime() - Date.now()) / 60000);
  if (diffMinutes <= 0) return 'Đến lượt ngay';
  if (diffMinutes < 60) return `${diffMinutes} phút nữa`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours} giờ nữa`;
  return `${Math.floor(diffHours / 24)} ngày nữa`;
}

export function formatTrendLabel(dateString) {
  if (!dateString) return '--';
  const [, month, day] = dateString.split('-');
  return `${day}/${month}`;
}

export function getStatusClasses(status) {
  const map = {
    active: 'border-emerald-400/25 bg-emerald-400/10 text-emerald-100',
    paused: 'border-amber-400/25 bg-amber-400/10 text-amber-100',
    pending: 'border-cyan-400/25 bg-cyan-400/10 text-cyan-100',
    downloading: 'border-cyan-400/25 bg-cyan-400/10 text-cyan-100',
    queued: 'border-cyan-400/25 bg-cyan-400/10 text-cyan-100',
    processing: 'border-amber-400/25 bg-amber-400/10 text-amber-100',
    completed: 'border-emerald-400/25 bg-emerald-400/10 text-emerald-100',
    ready: 'border-amber-400/25 bg-amber-400/10 text-amber-100',
    posted: 'border-emerald-400/25 bg-emerald-400/10 text-emerald-100',
    failed: 'border-rose-400/25 bg-rose-400/10 text-rose-100',
    replied: 'border-emerald-400/25 bg-emerald-400/10 text-emerald-100',
    ignored: 'border-white/10 bg-white/5 text-slate-200',
    page_access_token: 'border-emerald-400/25 bg-emerald-400/10 text-emerald-100',
    user_access_token: 'border-rose-400/25 bg-rose-400/10 text-rose-100',
    invalid_token: 'border-rose-400/25 bg-rose-400/10 text-rose-100',
    network_error: 'border-amber-400/25 bg-amber-400/10 text-amber-100',
    legacy_webhook: 'border-amber-400/25 bg-amber-400/10 text-amber-100',
    invalid_encryption: 'border-rose-400/25 bg-rose-400/10 text-rose-100',
    missing: 'border-white/10 bg-white/5 text-slate-200',
  };
  return map[status] || 'border-white/10 bg-white/5 text-slate-200';
}

export function getSyncStateMeta(status) {
  if (status === 'queued') return { tone: 'pending', label: 'Đang xếp hàng' };
  if (status === 'syncing') return { tone: 'pending', label: 'Đang đồng bộ' };
  if (status === 'completed') return { tone: 'posted', label: 'Đã đồng bộ' };
  if (status === 'failed') return { tone: 'failed', label: 'Đồng bộ lỗi' };
  return { tone: 'paused', label: 'Chưa đồng bộ' };
}

export function getStatusLabel(status) {
  return STATUS_LABELS[status] || status || 'Chưa có';
}

export function getPageTokenMeta(tokenKind) {
  return PAGE_TOKEN_META[tokenKind] || PAGE_TOKEN_META.missing;
}

export function getSourcePlatformMeta(sourcePlatform) {
  return SOURCE_PLATFORM_META[sourcePlatform] || SOURCE_PLATFORM_META.unknown;
}

export function getSourceKindLabel(sourceKind) {
  return SOURCE_KIND_LABELS[sourceKind] || sourceKind || 'Chưa rõ kiểu nguồn';
}

export function summarizeSourceCounts(items, selector) {
  return items.reduce(
    (summary, item) => {
      const rawValue = selector(item);
      const key = rawValue === 'tiktok' || rawValue === 'youtube' ? rawValue : 'unknown';
      summary[key] += 1;
      return summary;
    },
    { tiktok: 0, youtube: 0, unknown: 0 },
  );
}

export function formatIntentLabel(intent) {
  const normalized = (intent || '').trim();
  if (!normalized) return 'Chưa xác định';
  return normalized.replace(/_/g, ' ');
}

export function getConversationFactEntries(conversation) {
  if (!conversation?.customer_facts || typeof conversation.customer_facts !== 'object') return [];
  return Object.entries(conversation.customer_facts).filter(([key, value]) => key && value);
}

export function getConversationStatusMeta(status) {
  return CONVERSATION_STATUS_META[status] || { label: 'Chưa rõ trạng thái', tone: 'slate' };
}

export function buildConversationTimeline(logs) {
  const events = [];
  logs.forEach((log) => {
    const customerText = (log.user_message || '').trim();
    if (customerText) {
      events.push({
        id: `${log.id}-customer`,
        type: 'customer',
        text: customerText,
        time: log.created_at,
        sourceLabel: 'Khách hàng',
        status: log.status,
      });
    }

    const replyText = (log.ai_reply || '').trim();
    const shouldShowReply = replyText && (log.status === 'replied' || log.facebook_reply_message_id || log.reply_source);
    if (shouldShowReply) {
      const isOperator = log.reply_source === 'operator';
      events.push({
        id: `${log.id}-reply`,
        type: isOperator ? 'operator' : 'ai',
        text: replyText,
        time: log.updated_at || log.created_at,
        sourceLabel: isOperator ? (log.reply_author?.display_name || 'Operator') : 'AI fanpage',
        status: log.status,
      });
    }
  });

  return events.sort((left, right) => new Date(left.time || 0).getTime() - new Date(right.time || 0).getTime());
}

export function detectSourcePreview(rawUrl) {
  const candidate = (rawUrl || '').trim();
  if (!candidate) {
    return {
      status: 'idle',
      tone: 'slate',
      title: 'Chưa nhập nguồn',
      detail: 'Hỗ trợ TikTok và YouTube Shorts.',
    };
  }

  let normalized = candidate;
  if (!normalized.includes('://') && !normalized.startsWith('//')) {
    normalized = `https://${normalized}`;
  }

  try {
    const parsed = new URL(normalized);
    const host = parsed.hostname.toLowerCase();
    const path = parsed.pathname.replace(/\/+$/, '') || '/';

    if (host.endsWith('tiktok.com')) {
      if (host === 'vm.tiktok.com' || host === 'vt.tiktok.com' || path.toLowerCase().startsWith('/t/')) {
        return { status: 'ok', tone: 'sky', title: 'TikTok shortlink', detail: 'Hệ thống sẽ mở shortlink và đồng bộ video từ đó.' };
      }
      if (/^\/@[^/]+\/(video|photo)\/[^/]+$/i.test(path)) {
        return { status: 'ok', tone: 'sky', title: 'Video TikTok đơn lẻ', detail: 'Phù hợp khi bạn muốn lấy đúng một video cụ thể.' };
      }
      if (/^\/@[^/]+$/i.test(path)) {
        return { status: 'ok', tone: 'sky', title: 'Hồ sơ TikTok', detail: 'Worker sẽ lấy danh sách video từ hồ sơ này.' };
      }
      return { status: 'warning', tone: 'amber', title: 'TikTok chưa đúng mẫu hỗ trợ', detail: 'Hãy dùng link video, hồ sơ hoặc shortlink TikTok hợp lệ.' };
    }

    if (['youtube.com', 'www.youtube.com', 'm.youtube.com'].includes(host)) {
      if (/^\/shorts\/[^/]+$/i.test(path)) {
        return { status: 'ok', tone: 'rose', title: 'YouTube Short đơn lẻ', detail: 'Phù hợp khi bạn muốn lấy đúng một short cụ thể.' };
      }
      if (/^\/(?:@[^/]+|channel\/[^/]+|c\/[^/]+|user\/[^/]+)\/shorts$/i.test(path)) {
        return { status: 'ok', tone: 'rose', title: 'Nguồn YouTube Shorts', detail: 'Worker sẽ chỉ lấy các Shorts hợp lệ từ nguồn này.' };
      }
      return { status: 'warning', tone: 'amber', title: 'Link YouTube chưa đúng scope', detail: 'Chỉ hỗ trợ /shorts/... hoặc nguồn /@handle/shorts.' };
    }

    if (['youtu.be', 'www.youtu.be'].includes(host)) {
      return { status: 'warning', tone: 'amber', title: 'Link rút gọn YouTube chưa hỗ trợ', detail: 'Hãy dùng URL đầy đủ dạng youtube.com/shorts/...' };
    }

    return { status: 'warning', tone: 'amber', title: 'Nguồn chưa được hỗ trợ', detail: 'Hiện chỉ hỗ trợ TikTok và YouTube Shorts.' };
  } catch {
    return { status: 'warning', tone: 'amber', title: 'Link nguồn chưa hợp lệ', detail: 'Kiểm tra lại URL trước khi tạo chiến dịch.' };
  }
}

export function getResolvedPageTokenKind(pageItem, validation) {
  return validation?.token_kind || pageItem?.token_kind || 'missing';
}

export function getMessengerConnectionMeta(validation) {
  const connection = validation?.messenger_connection;
  if (!validation) {
    return {
      label: 'Webhook chưa kiểm tra',
      tone: 'slate',
      detail: 'Bấm xác minh để xem trạng thái webhook feed và messages.',
    };
  }
  if (validation.ok === false) {
    return {
      label: 'Token chưa đạt',
      tone: 'rose',
      detail: validation.message || 'Không thể kiểm tra kết nối webhook fanpage.',
    };
  }
  if (connection?.connected) {
    const appName = connection.connected_app?.name || 'app hiện tại';
    return {
      label: 'Webhook đã kết nối',
      tone: 'emerald',
      detail: `Đang nhận feed và messages qua ${appName}.`,
    };
  }
  return {
    label: 'Webhook chưa kết nối',
    tone: connection?.ok === false ? 'rose' : 'amber',
    detail: connection?.message || 'Fanpage chưa đăng ký nhận feed và messages.',
  };
}

export function buildPageCheckSnapshot(payload) {
  return {
    ...payload?.validation,
    messenger_connection: payload?.messenger_connection || payload?.validation?.messenger_connection || null,
    checked_at: new Date().toISOString(),
  };
}
