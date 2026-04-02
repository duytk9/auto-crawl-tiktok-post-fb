import { useEffect, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Bot,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  CircleCheck,
  CircleX,
  Clock,
  CloudDownload,
  Copy,
  ExternalLink,
  Filter,
  Globe2,
  KeyRound,
  LogOut,
  Menu,
  MessagesSquare,
  Pause,
  Play,
  PlusCircle,
  Radio,
  RefreshCw,
  Server,
  Share2,
  ShieldCheck,
  Terminal,
  Trash2,
  UserPlus,
  X,
  Zap,
} from 'lucide-react';

const API_URL = '/api';
const AUTO_REFRESH_MS = 5000;
const TASK_PAGE_SIZE = 3;
const TASK_FETCH_LIMIT = 24;
const SYSTEM_EVENT_PAGE_SIZE = 3;
const SYSTEM_EVENT_FETCH_LIMIT = 24;
const FIELD_CLASS = 'field-input w-full rounded-2xl px-4 py-3 text-sm text-white';
const BUTTON_DISABLED = 'disabled:cursor-not-allowed disabled:opacity-50';
const BUTTON_PRIMARY = `btn-primary inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold ${BUTTON_DISABLED}`;
const BUTTON_SECONDARY = `btn-secondary inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-medium ${BUTTON_DISABLED}`;
const BUTTON_GHOST = `btn-ghost inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-medium ${BUTTON_DISABLED}`;

const DEFAULT_STATS = {
  total: 0,
  pending: 0,
  ready: 0,
  posted: 0,
  failed: 0,
  active_campaigns: 0,
  paused_campaigns: 0,
  connected_pages: 0,
  next_publish: null,
  queue_end: null,
  last_posted: null,
  by_source: {
    tiktok: { campaigns: 0, videos: 0, ready: 0 },
    youtube: { campaigns: 0, videos: 0, ready: 0 },
    unknown: { campaigns: 0, videos: 0, ready: 0 },
  },
  source_trends: {
    labels: [],
    series: {
      tiktok: { ready: [], posted: [], failed: [] },
      youtube: { ready: [], posted: [], failed: [] },
      unknown: { ready: [], posted: [], failed: [] },
    },
  },
};

const DEFAULT_TASK_SUMMARY = { queued: 0, processing: 0, completed: 0, failed: 0 };
const DEFAULT_RUNTIME_FORM = {
  BASE_URL: '',
  FB_VERIFY_TOKEN: '',
  FB_APP_SECRET: '',
  GEMINI_API_KEY: '',
  TUNNEL_TOKEN: '',
};

function buildReplyAutomationDraft(pageItem) {
  return {
    comment_auto_reply_enabled: pageItem?.comment_auto_reply_enabled ?? true,
    comment_ai_prompt: pageItem?.comment_ai_prompt || '',
    message_auto_reply_enabled: pageItem?.message_auto_reply_enabled ?? false,
    message_ai_prompt: pageItem?.message_ai_prompt || '',
    message_reply_schedule_enabled: pageItem?.message_reply_schedule_enabled ?? false,
    message_reply_start_time: pageItem?.message_reply_start_time || '08:00',
    message_reply_end_time: pageItem?.message_reply_end_time || '22:00',
    message_reply_cooldown_minutes: pageItem?.message_reply_cooldown_minutes ?? 0,
    affiliate_comment_enabled: pageItem?.affiliate_comment_enabled ?? false,
    affiliate_comment_text: pageItem?.affiliate_comment_text || '',
    affiliate_link_url: pageItem?.affiliate_link_url || '',
    affiliate_comment_delay_seconds: pageItem?.affiliate_comment_delay_seconds ?? 60,
  };
}

function extractRuntimeForm(payload) {
  return {
    BASE_URL: payload?.settings?.BASE_URL?.value || '',
    FB_VERIFY_TOKEN: payload?.settings?.FB_VERIFY_TOKEN?.value || '',
    FB_APP_SECRET: payload?.settings?.FB_APP_SECRET?.value || '',
    GEMINI_API_KEY: payload?.settings?.GEMINI_API_KEY?.value || '',
    TUNNEL_TOKEN: payload?.settings?.TUNNEL_TOKEN?.value || '',
  };
}

const STATUS_FILTERS = [
  { value: 'all', label: 'Tất cả trạng thái' },
  { value: 'pending', label: 'Đang xử lý' },
  { value: 'ready', label: 'Sẵn sàng đăng' },
  { value: 'posted', label: 'Đã đăng' },
  { value: 'failed', label: 'Thất bại' },
];

const SOURCE_PLATFORM_FILTERS = [
  { value: 'all', label: 'Tất cả nguồn' },
  { value: 'tiktok', label: 'TikTok' },
  { value: 'youtube', label: 'YouTube Shorts' },
];

const NAV_ITEMS = [
  { id: 'overview', label: 'Tổng quan', description: 'Chỉ số và cảnh báo.', icon: Globe2 },
  { id: 'campaigns', label: 'Chiến dịch', description: 'Nguồn, trang và chiến dịch.', icon: Share2 },
  { id: 'queue', label: 'Lịch đăng', description: 'Video, lịch và caption.', icon: Clock },
  { id: 'engagement', label: 'Tương tác', description: 'Bình luận và phản hồi AI.', icon: Bot },
  { id: 'messages', label: 'Tin nhắn AI', description: 'Prompt và inbox tự động.', icon: MessagesSquare },
  { id: 'operations', label: 'Vận hành', description: 'Worker, queue và log.', icon: Server },
  { id: 'security', label: 'Bảo mật', description: 'Phiên, mật khẩu, người dùng.', icon: ShieldCheck },
];

const STATUS_LABELS = {
  active: 'Đang chạy',
  paused: 'Tạm dừng',
  pending: 'Đang xử lý',
  downloading: 'Đang tải',
  queued: 'Đang chờ',
  processing: 'Đang chạy',
  completed: 'Hoàn tất',
  ready: 'Sẵn sàng',
  posted: 'Đã đăng',
  failed: 'Thất bại',
  replied: 'Đã trả lời',
  ignored: 'Bỏ qua',
  disabled: 'Tắt',
  operator_required: 'Cần operator',
  page_access_token: 'Token trang',
  user_access_token: 'Token người dùng',
  invalid_token: 'Token không hợp lệ',
  network_error: 'Lỗi kết nối',
  legacy_webhook: 'Webhook cũ',
  invalid_encryption: 'Lỗi giải mã',
  missing: 'Chưa có',
};

const TONE_CLASSES = {
  slate: 'border-white/10 bg-white/5 text-slate-200',
  sky: 'border-cyan-400/20 bg-cyan-400/10 text-cyan-100',
  emerald: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100',
  amber: 'border-amber-400/20 bg-amber-400/10 text-amber-100',
  rose: 'border-rose-400/20 bg-rose-400/10 text-rose-100',
};

const PAGE_TOKEN_META = {
  page_access_token: { label: 'Token trang hợp lệ', tone: 'emerald' },
  user_access_token: { label: 'Đang dùng user token', tone: 'rose' },
  invalid_token: { label: 'Token không hợp lệ', tone: 'rose' },
  network_error: { label: 'Chưa kiểm tra được token', tone: 'amber' },
  legacy_webhook: { label: 'Dữ liệu webhook cũ', tone: 'amber' },
  invalid_encryption: { label: 'Lỗi giải mã token', tone: 'rose' },
  missing: { label: 'Chưa có token', tone: 'slate' },
};

const CONVERSATION_STATUS_META = {
  ai_active: { label: 'AI đang xử lý', tone: 'sky' },
  operator_active: { label: 'Cần operator', tone: 'rose' },
  resolved: { label: 'Đã xử lý', tone: 'emerald' },
};

const SOURCE_PLATFORM_META = {
  tiktok: { label: 'TikTok', tone: 'sky' },
  youtube: { label: 'YouTube Shorts', tone: 'rose' },
  unknown: { label: 'Chưa rõ nguồn', tone: 'slate' },
};

const SOURCE_KIND_LABELS = {
  tiktok_video: 'Video TikTok',
  tiktok_profile: 'Hồ sơ TikTok',
  tiktok_shortlink: 'Link TikTok rút gọn',
  tiktok_legacy: 'Nguồn TikTok cũ',
  youtube_short: 'YouTube Short',
  youtube_shorts_feed: 'Nguồn Shorts YouTube',
};

const TREND_STATUS_META = {
  ready: { label: 'Sẵn sàng', color: '#67e8f9', textClass: 'text-cyan-100' },
  posted: { label: 'Đã đăng', color: '#34d399', textClass: 'text-emerald-100' },
  failed: { label: 'Thất bại', color: '#fb7185', textClass: 'text-rose-100' },
};

function cx(...values) {
  return values.filter(Boolean).join(' ');
}

function parseMessage(payload, fallback) {
  return payload?.detail || payload?.message || fallback;
}

function summarizeText(value, fallback = 'Chưa có nội dung.', maxLength = 110) {
  const normalized = (value || '').replace(/\s+/g, ' ').trim();
  if (!normalized) return fallback;
  if (normalized.length <= maxLength) return normalized;
  return `${normalized.slice(0, maxLength).trim()}...`;
}

function formatDateTime(isoString, options = {}) {
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

function formatRelTime(isoString) {
  if (!isoString) return 'Chưa có';
  const date = new Date(`${isoString}${isoString.endsWith('Z') ? '' : 'Z'}`);
  const diffMinutes = Math.round((date.getTime() - Date.now()) / 60000);
  if (diffMinutes <= 0) return 'Đến lượt ngay';
  if (diffMinutes < 60) return `${diffMinutes} phút nữa`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours} giờ nữa`;
  return `${Math.floor(diffHours / 24)} ngày nữa`;
}

function formatTrendLabel(dateString) {
  if (!dateString) return '--';
  const [, month, day] = dateString.split('-');
  return `${day}/${month}`;
}

function getStatusClasses(status) {
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
    disabled: 'border-white/10 bg-white/5 text-slate-200',
    operator_required: 'border-rose-400/25 bg-rose-400/10 text-rose-100',
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

function getSyncStateMeta(status) {
  if (status === 'queued') return { tone: 'pending', label: 'Đang xếp hàng' };
  if (status === 'syncing') return { tone: 'pending', label: 'Đang đồng bộ' };
  if (status === 'completed') return { tone: 'posted', label: 'Đã đồng bộ' };
  if (status === 'failed') return { tone: 'failed', label: 'Đồng bộ lỗi' };
  return { tone: 'paused', label: 'Chưa đồng bộ' };
}

function getStatusLabel(status) {
  return STATUS_LABELS[status] || status || 'Chưa có';
}

function getPageTokenMeta(tokenKind) {
  return PAGE_TOKEN_META[tokenKind] || PAGE_TOKEN_META.missing;
}

function getSourcePlatformMeta(sourcePlatform) {
  return SOURCE_PLATFORM_META[sourcePlatform] || SOURCE_PLATFORM_META.unknown;
}

function getSourceKindLabel(sourceKind) {
  return SOURCE_KIND_LABELS[sourceKind] || sourceKind || 'Chưa rõ kiểu nguồn';
}

function summarizeSourceCounts(items, selector) {
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

function formatIntentLabel(intent) {
  const normalized = (intent || '').trim();
  if (!normalized) return 'Chưa xác định';
  return normalized.replace(/_/g, ' ');
}

function getConversationFactEntries(conversation) {
  if (!conversation?.customer_facts || typeof conversation.customer_facts !== 'object') return [];
  return Object.entries(conversation.customer_facts).filter(([key, value]) => key && value);
}

function getConversationStatusMeta(status) {
  return CONVERSATION_STATUS_META[status] || { label: 'Chưa rõ trạng thái', tone: 'slate' };
}

function buildConversationTimeline(logs) {
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

function detectSourcePreview(rawUrl) {
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
        return {
          status: 'ok',
          tone: 'sky',
          title: 'TikTok shortlink',
          detail: 'Hệ thống sẽ mở shortlink và đồng bộ video từ đó.',
        };
      }
      if (/^\/@[^/]+\/(video|photo)\/[^/]+$/i.test(path)) {
        return {
          status: 'ok',
          tone: 'sky',
          title: 'Video TikTok đơn lẻ',
          detail: 'Phù hợp khi bạn muốn lấy đúng một video cụ thể.',
        };
      }
      if (/^\/@[^/]+$/i.test(path)) {
        return {
          status: 'ok',
          tone: 'sky',
          title: 'Hồ sơ TikTok',
          detail: 'Worker sẽ lấy danh sách video từ hồ sơ này.',
        };
      }
      return {
        status: 'warning',
        tone: 'amber',
        title: 'TikTok chưa đúng mẫu hỗ trợ',
        detail: 'Hãy dùng link video, hồ sơ hoặc shortlink TikTok hợp lệ.',
      };
    }

    if (['youtube.com', 'www.youtube.com', 'm.youtube.com'].includes(host)) {
      if (/^\/shorts\/[^/]+$/i.test(path)) {
        return {
          status: 'ok',
          tone: 'rose',
          title: 'YouTube Short đơn lẻ',
          detail: 'Phù hợp khi bạn muốn lấy đúng một short cụ thể.',
        };
      }
      if (/^\/(?:@[^/]+|channel\/[^/]+|c\/[^/]+|user\/[^/]+)\/shorts$/i.test(path)) {
        return {
          status: 'ok',
          tone: 'rose',
          title: 'Nguồn YouTube Shorts',
          detail: 'Worker sẽ chỉ lấy các Shorts hợp lệ từ nguồn này.',
        };
      }
      return {
        status: 'warning',
        tone: 'amber',
        title: 'Link YouTube chưa đúng scope',
        detail: 'Chỉ hỗ trợ /shorts/... hoặc nguồn /@handle/shorts.',
      };
    }

    if (['youtu.be', 'www.youtu.be'].includes(host)) {
      return {
        status: 'warning',
        tone: 'amber',
        title: 'Link rút gọn YouTube chưa hỗ trợ',
        detail: 'Hãy dùng URL đầy đủ dạng youtube.com/shorts/...',
      };
    }

    return {
      status: 'warning',
      tone: 'amber',
      title: 'Nguồn chưa được hỗ trợ',
      detail: 'Hiện chỉ hỗ trợ TikTok và YouTube Shorts.',
    };
  } catch {
    return {
      status: 'warning',
      tone: 'amber',
      title: 'Link nguồn chưa hợp lệ',
      detail: 'Kiểm tra lại URL trước khi tạo chiến dịch.',
    };
  }
}

function getResolvedPageTokenKind(pageItem, validation) {
  return validation?.token_kind || pageItem?.token_kind || 'missing';
}

function getMessengerConnectionMeta(validation) {
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

function buildPageCheckSnapshot(payload) {
  return {
    ...payload?.validation,
    messenger_connection: payload?.messenger_connection || payload?.validation?.messenger_connection || null,
    checked_at: new Date().toISOString(),
  };
}

function StatusIcon({ status, className = '' }) {
  if (['posted', 'completed', 'active', 'replied', 'page_access_token'].includes(status)) {
    return <CircleCheck className={cx('h-3.5 w-3.5', className)} />;
  }
  if (['failed', 'invalid_encryption'].includes(status)) {
    return <CircleX className={cx('h-3.5 w-3.5', className)} />;
  }
  if (['user_access_token', 'invalid_token'].includes(status)) {
    return <CircleX className={cx('h-3.5 w-3.5', className)} />;
  }
  if (['pending', 'queued', 'processing', 'downloading'].includes(status)) {
    return <RefreshCw className={cx('h-3.5 w-3.5 animate-spin', className)} />;
  }
  if (['paused', 'ready', 'legacy_webhook', 'ignored', 'network_error'].includes(status)) {
    return <Radio className={cx('h-3.5 w-3.5', className)} />;
  }
  return <ChevronRight className={cx('h-3.5 w-3.5', className)} />;
}

function StatusPill({ tone = 'slate', icon: Icon, children, className = '' }) {
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium',
        TONE_CLASSES[tone] || TONE_CLASSES.slate,
        className
      )}
    >
      {Icon ? <Icon className="h-3.5 w-3.5" /> : null}
      <span>{children}</span>
    </span>
  );
}

function MetricCard({ icon, label, value, detail, tone = 'slate' }) {
  const IconComponent = icon;
  return (
    <div className="metric-card overflow-hidden rounded-[22px] p-3.5 sm:rounded-[24px] lg:p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">{label}</div>
          <div className="mt-2.5 font-display text-[1.45rem] font-semibold text-white sm:text-[1.8rem]">{value}</div>
        </div>
        <div className={cx('rounded-2xl border p-3', TONE_CLASSES[tone] || TONE_CLASSES.slate)}>
          <IconComponent className="h-5 w-5" />
        </div>
      </div>
      <p className="mt-3 text-xs leading-5 text-[var(--text-soft)]">{detail}</p>
    </div>
  );
}

function Panel({ eyebrow, title, subtitle, action, children, className = '' }) {
  return (
    <section className={cx('panel-surface rounded-[22px] p-3.5 sm:rounded-[24px] sm:p-4 lg:p-5', className)}>
      {(eyebrow || title || subtitle || action) && (
        <div className="mb-4 flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            {eyebrow ? <div className="text-[10px] uppercase tracking-[0.34em] text-[var(--text-muted)]">{eyebrow}</div> : null}
            {title ? <h2 className="mt-1.5 font-display text-[1.05rem] font-semibold text-white sm:text-[1.25rem]">{title}</h2> : null}
            {subtitle ? <p className="mt-1 max-w-2xl text-sm leading-6 text-[var(--text-soft)]">{subtitle}</p> : null}
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>
      )}
      {children}
    </section>
  );
}

function InfoRow({ label, value, emphasis = false }) {
  return (
    <div className="flex flex-col gap-1.5 rounded-2xl border border-white/6 bg-black/10 px-3 py-2.5 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <span className="text-[13px] text-[var(--text-muted)]">{label}</span>
      <span className={cx('text-left text-[13px] sm:text-right', emphasis ? 'font-semibold text-white' : 'text-[var(--text-soft)]')}>{value}</span>
    </div>
  );
}

function SourceBreakdownBar({ label, value, max = 1, tone = 'slate', detail }) {
  const width = `${Math.max(8, Math.round((value / Math.max(1, max)) * 100))}%`;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="text-[12px] text-[var(--text-muted)]">{label}</span>
        <span className="text-sm font-medium text-white">{value}</span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-white/8">
        <div className={cx('h-full rounded-full', tone === 'rose' ? 'bg-rose-300/80' : tone === 'sky' ? 'bg-cyan-300/80' : 'bg-white/60')} style={{ width }} />
      </div>
      {detail ? <div className="text-[11px] text-[var(--text-muted)]">{detail}</div> : null}
    </div>
  );
}

function TrendLegend() {
  return (
    <div className="flex flex-wrap gap-2">
      {Object.entries(TREND_STATUS_META).map(([key, meta]) => (
        <span key={key} className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] text-[var(--text-soft)]">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: meta.color }} />
          {meta.label}
        </span>
      ))}
    </div>
  );
}

function TrendTimelineChart({ labels, series }) {
  const width = 100;
  const height = 56;
  const entries = Object.entries(TREND_STATUS_META);
  const values = entries.flatMap(([key]) => series?.[key] || []);
  const maxValue = Math.max(1, ...values, 0);

  const buildPoints = (points) => {
    if (!points?.length) return '';
    return points
      .map((value, index) => {
        const x = points.length === 1 ? width / 2 : (index / (points.length - 1)) * width;
        const y = height - (value / maxValue) * (height - 6) - 3;
        return `${x},${Number.isFinite(y) ? y : height - 3}`;
      })
      .join(' ');
  };

  return (
    <div className="rounded-[22px] border border-white/8 bg-black/10 p-4">
      <TrendLegend />
      <div className="mt-4">
        <svg viewBox={`0 0 ${width} ${height}`} className="h-32 w-full overflow-visible">
          {[0.25, 0.5, 0.75].map((ratio) => {
            const y = height - ratio * (height - 6) - 3;
            return <line key={ratio} x1="0" y1={y} x2={width} y2={y} stroke="rgba(255,255,255,0.08)" strokeWidth="0.6" strokeDasharray="2 2" />;
          })}
          <line x1="0" y1={height - 3} x2={width} y2={height - 3} stroke="rgba(255,255,255,0.1)" strokeWidth="0.8" />
          {entries.map(([key, meta]) => {
            const points = series?.[key] || [];
            const pointString = buildPoints(points);
            return pointString ? (
              <polyline
                key={key}
                fill="none"
                stroke={meta.color}
                strokeWidth="2.2"
                strokeLinejoin="round"
                strokeLinecap="round"
                points={pointString}
              />
            ) : null;
          })}
          {entries.map(([key, meta]) => {
            const points = series?.[key] || [];
            return points.map((value, index) => {
              const x = points.length === 1 ? width / 2 : (index / (points.length - 1)) * width;
              const y = height - (value / maxValue) * (height - 6) - 3;
              return <circle key={`${key}-${labels?.[index] || index}`} cx={x} cy={y} r="1.75" fill={meta.color} />;
            });
          })}
        </svg>
      </div>
      <div className="mt-3 flex items-center justify-between gap-3 text-[11px] text-[var(--text-muted)]">
        <span>{formatTrendLabel(labels?.[0])}</span>
        <span>7 ngày gần nhất</span>
        <span>{formatTrendLabel(labels?.[labels.length - 1])}</span>
      </div>
    </div>
  );
}

function EmptyState({ title, description }) {
  return (
    <div className="rounded-[20px] border border-dashed border-white/10 bg-black/10 px-4 py-6 text-center sm:rounded-[22px] sm:px-5 sm:py-7">
      <div className="font-display text-base font-semibold text-white sm:text-lg">{title}</div>
      <p className="mx-auto mt-2 max-w-md text-[13px] leading-5 text-[var(--text-soft)]">{description}</p>
    </div>
  );
}

function DetailToggle({ expanded, onClick, className = '' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        'inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] text-[var(--text-soft)] transition hover:border-white/18 hover:bg-white/8 hover:text-white',
        className
      )}
    >
      {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      {expanded ? 'Thu gọn' : 'Xem thêm'}
    </button>
  );
}

function LoginFeature({ icon, title, description }) {
  const IconComponent = icon;
  return (
    <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 text-cyan-100">
        <IconComponent className="h-5 w-5" />
      </div>
      <div className="font-display text-lg font-semibold text-white">{title}</div>
      <p className="mt-2 text-sm leading-6 text-[var(--text-soft)]">{description}</p>
    </div>
  );
}

function LoginScreen({ loginUser, setLoginUser, loginPass, setLoginPass, loginError, handleLogin }) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[var(--shell-bg)] text-white">
      <div className="pointer-events-none absolute inset-0 opacity-80">
        <div className="absolute inset-y-0 left-0 w-1/2 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.16),transparent_58%)]" />
        <div className="absolute inset-y-0 right-0 w-1/2 bg-[radial-gradient(circle_at_bottom_right,rgba(245,158,11,0.12),transparent_54%)]" />
      </div>
      <div className="relative mx-auto flex min-h-screen max-w-[1560px] items-center px-4 py-8 lg:px-8">
        <div className="grid w-full gap-6 lg:grid-cols-[minmax(0,1.15fr)_440px] xl:gap-8">
          <section className="panel-strong hidden rounded-[34px] p-8 lg:flex lg:flex-col lg:justify-between xl:p-10">
            <div>
              <StatusPill tone="sky" icon={Zap}>Trạm điều phối nội dung</StatusPill>
              <h1 className="mt-6 max-w-3xl font-display text-[1.9rem] font-semibold leading-tight text-white xl:text-[2.5rem]">
                Quản lý chiến dịch, lịch đăng và phản hồi Facebook trong một nơi.
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-8 text-[var(--text-soft)]">
                Theo dõi queue, worker, webhook và cấu hình hệ thống từ cùng một dashboard.
              </p>
            </div>
            <div className="mt-10 grid gap-4 xl:grid-cols-3">
              <LoginFeature icon={Share2} title="Điều phối theo khu vực" description="Tách khu vực rõ ràng." />
              <LoginFeature icon={Terminal} title="Theo dõi sát worker" description="Theo dõi queue và worker." />
              <LoginFeature icon={ShieldCheck} title="Quản trị có kiểm soát" description="Quản lý phiên và quyền." />
            </div>
          </section>
          <section className="panel-surface mx-auto w-full max-w-[440px] rounded-[34px] p-6 sm:p-8">
            <div className="flex h-14 w-14 items-center justify-center rounded-[22px] border border-cyan-400/20 bg-cyan-400/10 text-cyan-100">
              <KeyRound className="h-7 w-7" />
            </div>
            <div className="mt-6">
              <div className="text-[11px] uppercase tracking-[0.32em] text-[var(--text-muted)]">Đăng nhập vận hành</div>
              <h2 className="mt-3 font-display text-[1.55rem] font-semibold text-white sm:text-[1.7rem]">Vào trạm điều phối</h2>
              <p className="mt-3 text-sm leading-7 text-[var(--text-soft)]">Dùng tài khoản quản trị hoặc vận hành để bắt đầu.</p>
            </div>
            <form onSubmit={handleLogin} className="mt-8 space-y-4">
              <label className="block space-y-2">
                <span className="text-xs uppercase tracking-[0.28em] text-[var(--text-muted)]">Tên đăng nhập</span>
                <input type="text" required className={FIELD_CLASS} placeholder="Nhập tên đăng nhập" value={loginUser} onChange={(event) => setLoginUser(event.target.value)} />
              </label>
              <label className="block space-y-2">
                <span className="text-xs uppercase tracking-[0.28em] text-[var(--text-muted)]">Mật khẩu</span>
                <input type="password" required className={FIELD_CLASS} placeholder="••••••••" value={loginPass} onChange={(event) => setLoginPass(event.target.value)} />
              </label>
              {loginError ? <div className="rounded-2xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">{loginError}</div> : null}
              <button type="submit" className={cx(BUTTON_PRIMARY, 'w-full')}>
                <KeyRound className="h-4 w-4" />
                Đăng nhập vào hệ thống
              </button>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
}

function App() {
  const [campaigns, setCampaigns] = useState([]);
  const [videos, setVideos] = useState([]);
  const [affiliateOperatorItems, setAffiliateOperatorItems] = useState([]);
  const [interactions, setInteractions] = useState([]);
  const [conversationList, setConversationList] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [selectedConversationLogs, setSelectedConversationLogs] = useState([]);
  const [systemInfo, setSystemInfo] = useState(null);
  const [formData, setFormData] = useState({ name: '', source_url: '', auto_post: false, target_page_id: '', schedule_interval: 30 });
  const [fbPages, setFbPages] = useState([]);
  const [fbForm, setFbForm] = useState({ page_id: '', page_name: '', long_lived_access_token: '' });
  const [fbImportToken, setFbImportToken] = useState('');
  const [discoveredFbPages, setDiscoveredFbPages] = useState([]);
  const [selectedDiscoveredPageIds, setSelectedDiscoveredPageIds] = useState([]);
  const [discoverySubject, setDiscoverySubject] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [stats, setStats] = useState(DEFAULT_STATS);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filteredVideoTotal, setFilteredVideoTotal] = useState(0);
  const [filters, setFilters] = useState({ status: 'all', campaignId: 'all', sourcePlatform: 'all' });
  const [campaignSourceFilter, setCampaignSourceFilter] = useState('all');
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [sessionExpiresAt, setSessionExpiresAt] = useState(localStorage.getItem('token_expires_at'));
  const [loginUser, setLoginUser] = useState('');
  const [loginPass, setLoginPass] = useState('');
  const [loginError, setLoginError] = useState('');
  const [notice, setNotice] = useState(null);
  const [actionState, setActionState] = useState({});
  const [captionDrafts, setCaptionDrafts] = useState({});
  const [pageChecks, setPageChecks] = useState({});
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [healthInfo, setHealthInfo] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [taskSummary, setTaskSummary] = useState(DEFAULT_TASK_SUMMARY);
  const [events, setEvents] = useState([]);
  const [workers, setWorkers] = useState([]);
  const [users, setUsers] = useState([]);
  const [runtimeConfig, setRuntimeConfig] = useState(null);
  const [runtimeForm, setRuntimeForm] = useState(DEFAULT_RUNTIME_FORM);
  const [replyAutomationDrafts, setReplyAutomationDrafts] = useState({});
  const [userForm, setUserForm] = useState({ username: '', display_name: '', password: '', role: 'operator' });
  const [passwordForm, setPasswordForm] = useState({ current_password: '', new_password: '' });
  const [activeSection, setActiveSection] = useState(localStorage.getItem('dashboard-active-section') || 'overview');
  const [taskPage, setTaskPage] = useState(1);
  const [eventPage, setEventPage] = useState(1);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [expandedItems, setExpandedItems] = useState({});
  const [showAllMetrics, setShowAllMetrics] = useState(false);
  const [overviewSourceFilter, setOverviewSourceFilter] = useState('all');
  const [conversationStatusFilter, setConversationStatusFilter] = useState('all');
  const [manualReplyDraft, setManualReplyDraft] = useState('');
  const [affiliateManualDrafts, setAffiliateManualDrafts] = useState({});
  const [conversationNoteDraft, setConversationNoteDraft] = useState('');
  const [conversationAssigneeDraft, setConversationAssigneeDraft] = useState('');
  const [pendingOperatorComposerId, setPendingOperatorComposerId] = useState(null);
  const manualReplyPanelRef = useRef(null);
  const manualReplyInputRef = useRef(null);

  const isAdmin = currentUser?.role === 'admin';
  const staleWorkers = workers.filter((worker) => !worker.is_online);
  const onlineWorkers = workers.filter((worker) => worker.is_online).length;
  const currentSection = NAV_ITEMS.find((item) => item.id === activeSection) || NAV_ITEMS[0];
  const warningCount = systemInfo?.warnings?.length || 0;
  const invalidPages = fbPages.filter((pageItem) => getResolvedPageTokenKind(pageItem, pageChecks[pageItem.page_id]) !== 'page_access_token');
  const connectedMessagePages = fbPages.filter((pageItem) => pageChecks[pageItem.page_id]?.messenger_connection?.connected).length;
  const focusCampaignCandidates = campaigns.filter((campaign) => campaign.last_sync_status === 'failed' || campaign.video_counts?.failed > 0);
  const focusCampaigns = focusCampaignCandidates.slice(0, 3);
  const campaignSourceSummary = summarizeSourceCounts(campaigns, (campaign) => campaign.source_platform);
  const filteredCampaigns = campaigns.filter((campaign) => campaignSourceFilter === 'all' || campaign.source_platform === campaignSourceFilter);
  const overviewSourceBreakdown = [
    {
      platform: 'tiktok',
      ...getSourcePlatformMeta('tiktok'),
      campaigns: stats.by_source?.tiktok?.campaigns ?? 0,
      videos: stats.by_source?.tiktok?.videos ?? 0,
      ready: stats.by_source?.tiktok?.ready ?? 0,
      trend: stats.source_trends?.series?.tiktok || { ready: [], posted: [], failed: [] },
    },
    {
      platform: 'youtube',
      ...getSourcePlatformMeta('youtube'),
      campaigns: stats.by_source?.youtube?.campaigns ?? 0,
      videos: stats.by_source?.youtube?.videos ?? 0,
      ready: stats.by_source?.youtube?.ready ?? 0,
      trend: stats.source_trends?.series?.youtube || { ready: [], posted: [], failed: [] },
    },
  ];
  const visibleOverviewSources = overviewSourceFilter === 'all'
    ? overviewSourceBreakdown
    : overviewSourceBreakdown.filter((item) => item.platform === overviewSourceFilter);
  const overviewSourceMax = Math.max(
    1,
    ...visibleOverviewSources.flatMap((item) => [item.campaigns, item.videos, item.ready]),
  );
  const overviewFocusCampaigns = focusCampaignCandidates
    .filter((campaign) => overviewSourceFilter === 'all' || campaign.source_platform === overviewSourceFilter)
    .slice(0, 3);
  const runtimeSettings = runtimeConfig?.settings || {};
  const runtimeDerived = runtimeConfig?.derived || {};
  const totalTaskPages = Math.max(1, Math.ceil(tasks.length / TASK_PAGE_SIZE));
  const pagedTasks = tasks.slice((taskPage - 1) * TASK_PAGE_SIZE, taskPage * TASK_PAGE_SIZE);
  const totalEventPages = Math.max(1, Math.ceil(events.length / SYSTEM_EVENT_PAGE_SIZE));
  const pagedEvents = events.slice((eventPage - 1) * SYSTEM_EVENT_PAGE_SIZE, eventPage * SYSTEM_EVENT_PAGE_SIZE);
  const toggleExpandedItem = (key) => setExpandedItems((current) => ({ ...current, [key]: !current[key] }));
  const handoffConversations = conversationList.filter((conversation) => conversation.status === 'operator_active');
  const resolvedConversations = conversationList.filter((conversation) => conversation.status === 'resolved');
  const affiliateEnabledPages = fbPages.filter((pageItem) => pageItem.affiliate_comment_enabled).length;
  const visibleConversations = conversationStatusFilter === 'all'
    ? conversationList
    : conversationList.filter((conversation) => conversation.status === conversationStatusFilter);
  const selectedConversationStatusMeta = getConversationStatusMeta(selectedConversation?.status);
  const selectedConversationTimeline = buildConversationTimeline(selectedConversationLogs);
  const assignableUsers = isAdmin ? users.filter((user) => user.is_active) : (currentUser ? [currentUser] : []);
  const allDiscoveredSelected = discoveredFbPages.length > 0
    && selectedDiscoveredPageIds.length === discoveredFbPages.length;

  const authFetch = async (url, options = {}) => {
    if (sessionExpiresAt && new Date(sessionExpiresAt).getTime() <= Date.now()) {
      setToken(null);
      setSessionExpiresAt(null);
      localStorage.removeItem('token');
      localStorage.removeItem('token_expires_at');
      throw new Error('Phiên đăng nhập đã hết hạn.');
    }
    const headers = { ...options.headers };
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) {
      setToken(null);
      setSessionExpiresAt(null);
      localStorage.removeItem('token');
      localStorage.removeItem('token_expires_at');
      throw new Error('Phiên đăng nhập đã hết hạn.');
    }
    return response;
  };

  const requestJson = async (url, options = {}) => {
    const response = await authFetch(url, options);
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    if (!response.ok) throw new Error(parseMessage(payload, 'Yêu cầu không thành công.'));
    return payload;
  };

  const setBusy = (key, value) => setActionState((current) => ({ ...current, [key]: value }));
  const showNotice = (type, message) => setNotice({ type, message });

  const fetchDashboard = async () => {
    if (!token) return;
    setIsRefreshing(true);
    try {
      const meData = await requestJson(`${API_URL}/auth/me`);
      const params = new URLSearchParams({ page: String(page), limit: '10' });
      if (filters.status !== 'all') params.set('status', filters.status);
      if (filters.campaignId !== 'all') params.set('campaign_id', filters.campaignId);
      if (filters.sourcePlatform !== 'all') params.set('source_platform', filters.sourcePlatform);

      const [campaignsData, statsData, videosData, affiliateData, fbData, logsData, conversationsData, systemData, healthData, taskData, eventData, workerData, userData] = await Promise.all([
        requestJson(`${API_URL}/campaigns/`),
        requestJson(`${API_URL}/campaigns/stats`),
        requestJson(`${API_URL}/campaigns/videos?${params.toString()}`),
        requestJson(`${API_URL}/campaigns/affiliate-comments?status=operator_required&limit=30`),
        requestJson(`${API_URL}/facebook/config`),
        requestJson(`${API_URL}/webhooks/logs`),
        requestJson(`${API_URL}/webhooks/conversations?limit=80`),
        requestJson(`${API_URL}/system/overview`),
        requestJson(`${API_URL}/system/health`),
        requestJson(`${API_URL}/system/tasks?limit=${TASK_FETCH_LIMIT}`),
        requestJson(`${API_URL}/system/events?limit=${SYSTEM_EVENT_FETCH_LIMIT}`),
        requestJson(`${API_URL}/system/workers`),
        meData?.role === 'admin' ? requestJson(`${API_URL}/users/`) : Promise.resolve({ users: [] }),
      ]);

      setCurrentUser(meData);
      setCampaigns(campaignsData);
      setStats(statsData);
      setVideos(videosData.videos);
      setAffiliateOperatorItems(affiliateData.items || []);
      setFilteredVideoTotal(videosData.total ?? 0);
      setTotalPages(videosData.pages);
      setFbPages(fbData);
      setInteractions(logsData);
      setConversationList(conversationsData.conversations || []);
      setSystemInfo(systemData);
      setHealthInfo(healthData);
      setTasks(taskData.tasks || []);
      setTaskSummary(taskData.summary || DEFAULT_TASK_SUMMARY);
      setEvents(eventData.events || []);
      setWorkers(workerData.workers || []);
      setUsers(userData.users || []);
      setLastUpdatedAt(new Date().toISOString());
    } catch (error) {
      showNotice('error', error.message);
    } finally {
      setTimeout(() => setIsRefreshing(false), 250);
    }
  };

  const loadRuntimeConfig = async () => {
    if (!token || currentUser?.role !== 'admin') return;
    const payload = await requestJson(`${API_URL}/system/runtime-config`);
    setRuntimeConfig(payload);
    setRuntimeForm(extractRuntimeForm(payload));
  };

  useEffect(() => {
    setAffiliateManualDrafts((current) => {
      const next = { ...current };
      affiliateOperatorItems.forEach((item) => {
        if (!next[item.id]) {
          next[item.id] = item.affiliate_comment_text || '';
        }
      });
      return next;
    });
  }, [affiliateOperatorItems]);

  const loadConversationDetail = async (conversationId, { silent = false } = {}) => {
    if (!token || !conversationId) {
      setSelectedConversation(null);
      setSelectedConversationLogs([]);
      return null;
    }

    try {
      const payload = await requestJson(`${API_URL}/webhooks/conversations/${conversationId}`);
      setSelectedConversation(payload.conversation || null);
      setSelectedConversationLogs(payload.logs || []);
      return payload;
    } catch (error) {
      if (!silent) showNotice('error', error.message);
      return null;
    }
  };

  const runAction = async (key, action) => {
    setBusy(key, true);
    try {
      const payload = await action();
      if (payload?.message) showNotice('success', payload.message);
      await fetchDashboard();
      return payload;
    } catch (error) {
      showNotice('error', error.message);
      return null;
    } finally {
      setBusy(key, false);
    }
  };

  useEffect(() => {
    if (!notice) return undefined;
    const timeout = setTimeout(() => setNotice(null), 4200);
    return () => clearTimeout(timeout);
  }, [notice]);

  useEffect(() => {
    localStorage.setItem('dashboard-active-section', activeSection);
  }, [activeSection]);

  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, AUTO_REFRESH_MS);
    return () => clearInterval(interval);
  }, [token, page, filters.status, filters.campaignId, filters.sourcePlatform]);
  /* eslint-enable react-hooks/exhaustive-deps */

  useEffect(() => {
    if (fbPages.length === 0) return;
    const selectedPageExists = fbPages.some((entry) => entry.page_id === formData.target_page_id);
    if (!selectedPageExists) setFormData((current) => ({ ...current, target_page_id: fbPages[0].page_id }));
  }, [fbPages, formData.target_page_id]);

  useEffect(() => {
    setReplyAutomationDrafts((current) => {
      const next = {};
      fbPages.forEach((pageItem) => {
        next[pageItem.page_id] = current[pageItem.page_id] || buildReplyAutomationDraft(pageItem);
      });
      return next;
    });
  }, [fbPages]);

  useEffect(() => {
    if (filters.campaignId === 'all') return;
    const exists = campaigns.some((campaign) => campaign.id === filters.campaignId);
    if (!exists) setFilters((current) => ({ ...current, campaignId: 'all' }));
  }, [campaigns, filters.campaignId]);

  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    if (!token || currentUser?.role !== 'admin') {
      setRuntimeConfig(null);
      setRuntimeForm(DEFAULT_RUNTIME_FORM);
      return;
    }

    let cancelled = false;
    const load = async () => {
      try {
        const payload = await requestJson(`${API_URL}/system/runtime-config`);
        if (cancelled) return;
        setRuntimeConfig(payload);
        setRuntimeForm(extractRuntimeForm(payload));
      } catch (error) {
        if (!cancelled) showNotice('error', error.message);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [token, currentUser?.role]);
  /* eslint-enable react-hooks/exhaustive-deps */

  useEffect(() => {
    if (taskPage > totalTaskPages) {
      setTaskPage(totalTaskPages);
    }
  }, [taskPage, totalTaskPages]);

  useEffect(() => {
    if (eventPage > totalEventPages) {
      setEventPage(totalEventPages);
    }
  }, [eventPage, totalEventPages]);

  useEffect(() => {
    setCaptionDrafts((current) => {
      const nextDrafts = { ...current };
      videos.forEach((video) => {
        if (!(video.id in nextDrafts) || (!nextDrafts[video.id] && video.ai_caption)) nextDrafts[video.id] = video.ai_caption || '';
      });
      return nextDrafts;
    });
  }, [videos]);

  useEffect(() => {
    if (conversationList.length === 0) {
      setSelectedConversationId(null);
      setSelectedConversation(null);
      setSelectedConversationLogs([]);
      return;
    }

    const exists = conversationList.some((conversation) => conversation.id === selectedConversationId);
    if (!exists) setSelectedConversationId(conversationList[0].id);
  }, [conversationList, selectedConversationId]);

  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    if (!token || !selectedConversationId) return;
    loadConversationDetail(selectedConversationId, { silent: true });
  }, [token, selectedConversationId, lastUpdatedAt]);
  /* eslint-enable react-hooks/exhaustive-deps */

  useEffect(() => {
    if (!selectedConversation) {
      setConversationNoteDraft('');
      setConversationAssigneeDraft('');
      setManualReplyDraft('');
      return;
    }

    setConversationNoteDraft(selectedConversation.internal_note || '');
    setConversationAssigneeDraft(
      selectedConversation.assigned_to_user_id
        || (!isAdmin && currentUser?.id ? currentUser.id : ''),
    );
  }, [selectedConversation, isAdmin, currentUser?.id]);

  useEffect(() => {
    if (
      !pendingOperatorComposerId
      || !selectedConversation
      || selectedConversation.id !== pendingOperatorComposerId
      || selectedConversation.status !== 'operator_active'
    ) {
      return;
    }

    setConversationStatusFilter('operator_active');
    const timeout = setTimeout(() => {
      manualReplyPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      manualReplyInputRef.current?.focus();
      setPendingOperatorComposerId(null);
    }, 120);

    return () => clearTimeout(timeout);
  }, [pendingOperatorComposerId, selectedConversation]);

  const handleSectionChange = (sectionId) => {
    setActiveSection(sectionId);
    setIsMobileNavOpen(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleCampaignSubmit = async (event) => {
    event.preventDefault();
    if (!formData.target_page_id) {
      showNotice('error', 'Vui lòng chọn trang đích.');
      return;
    }
    await runAction('create-campaign', async () => {
      const payload = await requestJson(`${API_URL}/campaigns/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      setFormData((current) => ({ ...current, name: '', source_url: '', auto_post: false }));
      return payload;
    });
  };

  const handleFbSubmit = async (event) => {
    event.preventDefault();
    const payload = await runAction('save-page', async () => {
      const response = await requestJson(`${API_URL}/facebook/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fbForm),
      });
      setFbForm({ page_id: '', page_name: '', long_lived_access_token: '' });
      return response;
    });
    if (payload?.page?.page_id && payload?.validation) {
      setPageChecks((current) => ({
        ...current,
        [payload.page.page_id]: buildPageCheckSnapshot(payload),
      }));
    }
  };

  const handleDiscoverFacebookPages = async (event) => {
    event.preventDefault();
    const userAccessToken = fbImportToken.trim();
    if (!userAccessToken) {
      showNotice('error', 'Bạn cần dán User Access Token trước khi tải danh sách fanpage.');
      return;
    }

    const payload = await runAction('discover-pages', () => requestJson(`${API_URL}/facebook/config/discover-pages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_access_token: userAccessToken }),
    }));

    if (payload) {
      const pages = payload.pages || [];
      setDiscoveredFbPages(pages);
      setDiscoverySubject({
        token_subject_id: payload.token_subject_id,
        token_subject_name: payload.token_subject_name,
      });
      const preferredSelection = pages
        .filter((pageItem) => !pageItem.already_configured)
        .map((pageItem) => pageItem.page_id);
      setSelectedDiscoveredPageIds(
        preferredSelection.length > 0
          ? preferredSelection
          : pages.map((pageItem) => pageItem.page_id),
      );
    }
  };

  const handleToggleDiscoveredPage = (pageId) => {
    setSelectedDiscoveredPageIds((current) => (
      current.includes(pageId)
        ? current.filter((item) => item !== pageId)
        : [...current, pageId]
    ));
  };

  const handleToggleAllDiscoveredPages = () => {
    setSelectedDiscoveredPageIds(
      allDiscoveredSelected
        ? []
        : discoveredFbPages.map((pageItem) => pageItem.page_id),
    );
  };

  const handleImportFacebookPages = async () => {
    const userAccessToken = fbImportToken.trim();
    if (!userAccessToken) {
      showNotice('error', 'Bạn cần dán User Access Token để import fanpage.');
      return;
    }
    if (selectedDiscoveredPageIds.length === 0) {
      showNotice('error', 'Hãy chọn ít nhất một fanpage để import.');
      return;
    }

    const payload = await runAction('import-pages', () => requestJson(`${API_URL}/facebook/config/import-pages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_access_token: userAccessToken,
        page_ids: selectedDiscoveredPageIds,
      }),
    }));

    if (payload?.imported_pages) {
      setPageChecks((current) => {
        const next = { ...current };
        payload.imported_pages.forEach((item) => {
          if (item?.page?.page_id && item?.validation) {
            next[item.page.page_id] = buildPageCheckSnapshot(item);
          }
        });
        return next;
      });
      setDiscoveredFbPages([]);
      setSelectedDiscoveredPageIds([]);
      setDiscoverySubject(null);
      setFbImportToken('');
    }
  };

  const handleRefreshFacebookPages = async () => {
    const userAccessToken = fbImportToken.trim();
    if (!userAccessToken) {
      showNotice('error', 'Bạn cần dán User Access Token để làm mới token fanpage.');
      return;
    }
    if (fbPages.length === 0) {
      showNotice('error', 'Chưa có fanpage nào trong hệ thống để làm mới token.');
      return;
    }

    const payload = await runAction('refresh-pages', () => requestJson(`${API_URL}/facebook/config/refresh-pages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_access_token: userAccessToken,
        page_ids: fbPages.map((pageItem) => pageItem.page_id),
      }),
    }));

    if (payload?.refreshed_pages) {
      setPageChecks((current) => {
        const next = { ...current };
        payload.refreshed_pages.forEach((item) => {
          if (item?.page?.page_id && item?.validation) {
            next[item.page.page_id] = buildPageCheckSnapshot(item);
          }
        });
        return next;
      });
    }
  };

  const handleDeleteFacebookPage = async (pageId, pageName) => {
    const confirmed = window.confirm(`Bạn có chắc muốn xóa fanpage "${pageName}" khỏi hệ thống không?`);
    if (!confirmed) return;

    const payload = await runAction(`delete-page-${pageId}`, () => requestJson(`${API_URL}/facebook/config/${pageId}`, {
      method: 'DELETE',
    }));

    if (payload?.page_id) {
      setPageChecks((current) => {
        const next = { ...current };
        delete next[payload.page_id];
        return next;
      });
      setReplyAutomationDrafts((current) => {
        const next = { ...current };
        delete next[payload.page_id];
        return next;
      });
      if (formData.target_page_id === payload.page_id) {
        setFormData((current) => ({ ...current, target_page_id: '' }));
      }
    }
  };

  const handleValidatePage = async (pageId) => {
    setBusy(`page-validate-${pageId}`, true);
    try {
      const payload = await requestJson(`${API_URL}/facebook/config/${pageId}/validate`);
      setPageChecks((current) => ({ ...current, [pageId]: buildPageCheckSnapshot({ validation: payload, messenger_connection: payload.messenger_connection }) }));
      showNotice('success', payload.message);
    } catch (error) {
      setPageChecks((current) => ({ ...current, [pageId]: { ok: false, message: error.message, checked_at: new Date().toISOString() } }));
      showNotice('error', error.message);
    } finally {
      setBusy(`page-validate-${pageId}`, false);
    }
  };

  const handleSubscribeMessages = async (pageId) => {
    setBusy(`page-subscribe-${pageId}`, true);
    try {
      const payload = await requestJson(`${API_URL}/facebook/config/${pageId}/subscribe-messages`, {
        method: 'POST',
      });
      setPageChecks((current) => ({
        ...current,
        [pageId]: buildPageCheckSnapshot(payload),
      }));
      showNotice('success', payload.message);
      await fetchDashboard();
    } catch (error) {
      showNotice('error', error.message);
    } finally {
      setBusy(`page-subscribe-${pageId}`, false);
    }
  };

  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    if (!token || fbPages.length === 0) return;

    const missingPageIds = fbPages
      .map((pageItem) => pageItem.page_id)
      .filter((pageId) => !pageChecks[pageId] && !actionState[`page-validate-${pageId}`]);

    if (missingPageIds.length === 0) return;

    let cancelled = false;
    const hydrateChecks = async () => {
      const results = await Promise.allSettled(
        missingPageIds.map((pageId) => requestJson(`${API_URL}/facebook/config/${pageId}/validate`)),
      );

      if (cancelled) return;

      setPageChecks((current) => {
        const next = { ...current };
        results.forEach((result, index) => {
          const pageId = missingPageIds[index];
          if (result.status === 'fulfilled') {
            next[pageId] = buildPageCheckSnapshot({
              validation: result.value,
              messenger_connection: result.value.messenger_connection,
            });
          } else {
            next[pageId] = {
              ok: false,
              message: result.reason?.message || 'Không thể kiểm tra fanpage.',
              checked_at: new Date().toISOString(),
            };
          }
        });
        return next;
      });
    };

    hydrateChecks();
    return () => {
      cancelled = true;
    };
  }, [fbPages, pageChecks, token, actionState]);
  /* eslint-enable react-hooks/exhaustive-deps */

  const handleReplyAutomationDraftChange = (pageId, key, value) => {
    setReplyAutomationDrafts((current) => ({
      ...current,
      [pageId]: {
        ...(current[pageId] || {}),
        [key]: value,
      },
    }));
  };

  const handleReplyAutomationReset = (pageItem) => {
    setReplyAutomationDrafts((current) => ({
      ...current,
      [pageItem.page_id]: buildReplyAutomationDraft(pageItem),
    }));
  };

  const handleReplyAutomationSave = async (pageId) => {
    const draft = replyAutomationDrafts[pageId];
    if (!draft) {
      showNotice('error', 'Không tìm thấy cấu hình fanpage để lưu.');
      return;
    }

    const payload = await runAction(`reply-automation-${pageId}`, () => requestJson(`${API_URL}/facebook/config/${pageId}/automation`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(draft),
    }));

    if (payload?.page) {
      setReplyAutomationDrafts((current) => ({
        ...current,
        [pageId]: buildReplyAutomationDraft(payload.page),
      }));
    }
  };

  const handleConversationUpdate = async (conversationId, payload, keySuffix = 'update') => {
    if (!conversationId) {
      showNotice('error', 'Không tìm thấy cuộc trò chuyện để cập nhật.');
      return null;
    }

    const result = await runAction(`conversation-${keySuffix}-${conversationId}`, () => requestJson(`${API_URL}/webhooks/conversations/${conversationId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }));
    if (result?.conversation) {
      setConversationList((current) => current.map((conversation) => (
        conversation.id === conversationId
          ? { ...conversation, ...result.conversation }
          : conversation
      )));
      if (selectedConversationId === conversationId) {
        setSelectedConversation((current) => ({ ...(current || {}), ...result.conversation }));
      }
      if (result.conversation.status === 'operator_active') {
        setConversationStatusFilter('operator_active');
        setPendingOperatorComposerId(conversationId);
      }
      await loadConversationDetail(conversationId, { silent: true });
    }
    return result;
  };

  const handleConversationStatusChange = async (conversationId, status, handoffReason = '') => {
    await handleConversationUpdate(conversationId, { status, handoff_reason: handoffReason }, `status-${status}`);
  };

  const handleConversationMetaSave = async () => {
    if (!selectedConversationId) {
      showNotice('error', 'Bạn chưa chọn cuộc trò chuyện nào.');
      return;
    }

    const payload = {
      assigned_to_user_id: conversationAssigneeDraft || '',
      internal_note: conversationNoteDraft,
    };
    await handleConversationUpdate(selectedConversationId, payload, 'meta');
  };

  const handleManualReply = async (markResolved = false) => {
    if (!selectedConversationId) {
      showNotice('error', 'Bạn chưa chọn cuộc trò chuyện nào.');
      return;
    }

    const message = manualReplyDraft.trim();
    if (message.length < 2) {
      showNotice('error', 'Nội dung phản hồi cần ít nhất 2 ký tự.');
      return;
    }

    const payload = await runAction(`conversation-reply-${selectedConversationId}`, () => requestJson(`${API_URL}/webhooks/conversations/${selectedConversationId}/reply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, mark_resolved: markResolved }),
    }));
    if (payload?.conversation) {
      setManualReplyDraft('');
      await loadConversationDetail(selectedConversationId, { silent: true });
    }
  };

  const handlePrioritize = async (videoId) => {
    await runAction(`video-${videoId}`, () => requestJson(`${API_URL}/campaigns/videos/${videoId}/priority`, { method: 'POST' }));
  };

  const handleRetryVideo = async (videoId) => {
    await runAction(`video-retry-${videoId}`, () => requestJson(`${API_URL}/campaigns/videos/${videoId}/retry`, { method: 'POST' }));
  };

  const handleRegenerateCaption = async (videoId) => {
    const payload = await runAction(`video-generate-${videoId}`, () => requestJson(`${API_URL}/campaigns/videos/${videoId}/generate-caption`, { method: 'POST' }));
    if (payload?.video) setCaptionDrafts((current) => ({ ...current, [videoId]: payload.video.ai_caption || '' }));
  };

  const handleCaptionChange = (videoId, value) => setCaptionDrafts((current) => ({ ...current, [videoId]: value }));
  const handleAffiliateDraftChange = (videoId, value) => setAffiliateManualDrafts((current) => ({ ...current, [videoId]: value }));

  const handleSaveCaption = async (videoId) => {
    const ai_caption = (captionDrafts[videoId] || '').trim();
    if (ai_caption.length < 3) {
      showNotice('error', 'Chú thích cần ít nhất 3 ký tự.');
      return;
    }
    const payload = await runAction(`video-caption-${videoId}`, () => requestJson(`${API_URL}/campaigns/videos/${videoId}/caption`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ai_caption }),
    }));
    if (payload?.video) setCaptionDrafts((current) => ({ ...current, [videoId]: payload.video.ai_caption || '' }));
  };

  const handleRetryAffiliateComment = async (videoId) => {
    await runAction(`affiliate-retry-${videoId}`, () => requestJson(`${API_URL}/campaigns/videos/${videoId}/affiliate-comment/retry`, {
      method: 'POST',
    }));
  };

  const handleManualAffiliateComment = async (videoId) => {
    const message = (affiliateManualDrafts[videoId] || '').trim();
    if (message.length < 3) {
      showNotice('error', 'Nội dung comment affiliate cần ít nhất 3 ký tự.');
      return;
    }

    const payload = await runAction(`affiliate-manual-${videoId}`, () => requestJson(`${API_URL}/campaigns/videos/${videoId}/affiliate-comment/manual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    }));

    if (payload?.video) {
      setAffiliateManualDrafts((current) => ({
        ...current,
        [videoId]: payload.video.affiliate_comment_text || message,
      }));
    }
  };

  const handleCampaignAction = async (campaign, action) => {
    if (action === 'delete') {
      const confirmed = window.confirm(`Xóa chiến dịch "${campaign.name}" và toàn bộ video liên quan?`);
      if (!confirmed) return;
    }
    const config = {
      sync: { method: 'POST', path: `${API_URL}/campaigns/${campaign.id}/sync` },
      pause: { method: 'POST', path: `${API_URL}/campaigns/${campaign.id}/pause` },
      resume: { method: 'POST', path: `${API_URL}/campaigns/${campaign.id}/resume` },
      delete: { method: 'DELETE', path: `${API_URL}/campaigns/${campaign.id}` },
    }[action];
    await runAction(`campaign-${campaign.id}-${action}`, () => requestJson(config.path, { method: config.method }));
  };

  const handleCopy = async (text, label) => {
    if (!text) {
      showNotice('error', `${label} hiện chưa có dữ liệu để sao chép.`);
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      showNotice('success', `Đã sao chép ${label}.`);
    } catch {
      showNotice('error', `Không thể sao chép ${label}.`);
    }
  };

  const handleRuntimeFieldChange = (key, value) => {
    setRuntimeForm((current) => ({ ...current, [key]: value }));
  };

  const handleRuntimeConfigSave = async (event) => {
    event.preventDefault();
    const payload = await runAction('save-runtime-config', () => requestJson(`${API_URL}/system/runtime-config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(runtimeForm),
    }));
    if (payload) {
      setRuntimeConfig(payload);
      setRuntimeForm(extractRuntimeForm(payload));
      await loadRuntimeConfig();
    }
  };

  const handleLogin = async (event) => {
    event.preventDefault();
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loginUser, password: loginPass }),
      });
      const payload = await response.json();
      if (response.ok) {
        const expiresAt = payload.expires_in ? new Date(Date.now() + payload.expires_in * 1000).toISOString() : null;
        setToken(payload.access_token);
        setSessionExpiresAt(expiresAt);
        setCurrentUser(payload.user || null);
        localStorage.setItem('token', payload.access_token);
        if (expiresAt) localStorage.setItem('token_expires_at', expiresAt);
        else localStorage.removeItem('token_expires_at');
        setLoginError('');
      } else {
        setLoginError(parseMessage(payload, 'Mật khẩu không chính xác!'));
      }
    } catch {
      setLoginError('Lỗi kết nối server.');
    }
  };

  const handleLogout = () => {
    setToken(null);
    setSessionExpiresAt(null);
    setLoginPass('');
    setCurrentUser(null);
    setUsers([]);
    localStorage.removeItem('token');
    localStorage.removeItem('token_expires_at');
  };

  const handleChangePassword = async (event) => {
    event.preventDefault();
    const payload = await runAction('change-password', () => requestJson(`${API_URL}/auth/change-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(passwordForm),
    }));
    if (payload) {
      setPasswordForm({ current_password: '', new_password: '' });
      setCurrentUser((current) => (current ? { ...current, must_change_password: false } : current));
    }
  };

  const handleCreateUser = async (event) => {
    event.preventDefault();
    const payload = await runAction('create-user', () => requestJson(`${API_URL}/users/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userForm),
    }));
    if (payload) setUserForm({ username: '', display_name: '', password: '', role: 'operator' });
  };

  const handleUserUpdate = async (userId, changes) => {
    await runAction(`user-update-${userId}`, () => requestJson(`${API_URL}/users/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(changes),
    }));
  };

  const handleResetUserPassword = async (userId) => {
    const payload = await runAction(`user-reset-${userId}`, () => requestJson(`${API_URL}/users/${userId}/reset-password`, { method: 'POST' }));
    if (payload?.temporary_password) showNotice('success', `${payload.message} Mật khẩu tạm: ${payload.temporary_password}`);
  };

  const handleDeleteUser = async (userId, username) => {
    const confirmed = window.confirm(`Xóa vĩnh viễn tài khoản @${username}? Thao tác này không thể hoàn tác.`);
    if (!confirmed) return;
    await runAction(`user-delete-${userId}`, () => requestJson(`${API_URL}/users/${userId}`, { method: 'DELETE' }));
  };

  const handleCleanupWorkers = async () => {
    if (staleWorkers.length === 0) {
      showNotice('success', 'Không có worker mất kết nối nào để dọn.');
      return;
    }
    const confirmed = window.confirm(`Dọn ${staleWorkers.length} worker mất kết nối khỏi danh sách theo dõi?`);
    if (!confirmed) return;
    await runAction('cleanup-workers', () => requestJson(`${API_URL}/system/workers/cleanup`, { method: 'POST' }));
  };

  const renderOverviewSection = () => (
    <div className="grid gap-6 2xl:grid-cols-12">
      <Panel
        className="2xl:col-span-8"
        eyebrow="Kết nối công khai"
        title="Webhook và cổng hệ thống"
      >
        <div className="grid gap-4 xl:grid-cols-3">
          {[
            { label: 'BASE_URL', value: systemInfo?.base_url || 'Chưa cấu hình', copyLabel: 'BASE_URL' },
            { label: 'Đường dẫn webhook', value: systemInfo?.webhook_url || 'Chưa tạo được đường dẫn webhook', copyLabel: 'đường dẫn webhook' },
            { label: 'Mã xác minh', value: systemInfo?.verify_token || 'Chưa có', copyLabel: 'mã xác minh' },
          ].map((item) => (
            <div key={item.label} className="rounded-[24px] border border-white/8 bg-black/10 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">{item.label}</div>
                <button type="button" className={BUTTON_GHOST} onClick={() => handleCopy(item.value, item.copyLabel)}>
                  <Copy className="h-4 w-4" />
                  Sao chép
                </button>
              </div>
              <div className="mt-4 break-all font-medium text-white">{item.value}</div>
            </div>
          ))}
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-2">
          <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
            <div className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Tình trạng sẵn sàng</div>
            <div className="mt-4 flex flex-wrap gap-2">
              <StatusPill tone={systemInfo?.public_webhook_ready ? 'emerald' : 'rose'} icon={Globe2}>
                {systemInfo?.public_webhook_ready ? 'Webhook có thể công khai' : 'Webhook chưa sẵn sàng'}
              </StatusPill>
              <StatusPill tone={systemInfo?.webhook_signature_enabled ? 'emerald' : 'amber'} icon={ShieldCheck}>
                {systemInfo?.webhook_signature_enabled ? 'Đang xác minh chữ ký' : 'Chưa cấu hình FB_APP_SECRET'}
              </StatusPill>
              <StatusPill tone={healthInfo?.database?.ok ? 'emerald' : 'rose'} icon={Server}>
                {healthInfo?.database?.ok ? 'Database ổn định' : 'Database có lỗi'}
              </StatusPill>
            </div>
          </div>
          <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
            <div className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Nút thao tác nhanh</div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <button type="button" className={BUTTON_SECONDARY} onClick={() => fetchDashboard()}>
                <RefreshCw className={cx('h-4 w-4', isRefreshing ? 'animate-spin' : '')} />
                Làm mới số liệu
              </button>
              <button type="button" className={BUTTON_SECONDARY} onClick={() => handleCopy(systemInfo?.webhook_url, 'đường dẫn webhook')}>
                <Copy className="h-4 w-4" />
                Copy webhook
              </button>
              <button type="button" className={BUTTON_SECONDARY} onClick={() => handleCopy(systemInfo?.verify_token, 'mã xác minh')}>
                <KeyRound className="h-4 w-4" />
                Copy verify token
              </button>
              <a className={BUTTON_SECONDARY} href={systemInfo?.webhook_url || '#'} target="_blank" rel="noreferrer">
                <ExternalLink className="h-4 w-4" />
                Mở webhook
              </a>
            </div>
          </div>
        </div>
      </Panel>

      <Panel className="2xl:col-span-4" eyebrow="Điểm nóng" title="Cảnh báo cần xử lý">
        <div className="space-y-3">
          {(systemInfo?.warnings || []).length === 0 ? (
            <div className="rounded-[24px] border border-emerald-400/20 bg-emerald-400/10 px-4 py-5 text-sm text-emerald-100">
              Chưa có cảnh báo.
            </div>
          ) : (
            systemInfo.warnings.map((warning) => (
              <div key={warning} className="rounded-[24px] border border-amber-400/20 bg-amber-400/10 px-4 py-4 text-sm leading-7 text-amber-50">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="mt-1 h-4 w-4 shrink-0" />
                  <span>{warning}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </Panel>

      <Panel
        className="2xl:col-span-7"
        eyebrow="Nguồn nội dung"
        title="Hiệu quả TikTok vs YouTube Shorts"
        action={(
          <select className={cx(FIELD_CLASS, 'min-w-[180px]')} value={overviewSourceFilter} onChange={(event) => setOverviewSourceFilter(event.target.value)}>
            {SOURCE_PLATFORM_FILTERS.map((option) => <option key={option.value} value={option.value} style={{ color: '#06101a' }}>{option.label}</option>)}
          </select>
        )}
      >
        <div className="grid gap-4 xl:grid-cols-2">
          {visibleOverviewSources.map((sourceItem) => (
            <div key={sourceItem.platform} className="rounded-[24px] border border-white/8 bg-black/10 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Nguồn đang theo dõi</div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <StatusPill tone={sourceItem.tone}>{sourceItem.label}</StatusPill>
                  </div>
                </div>
                <div className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-3 text-right">
                  <div className="text-[10px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Campaign</div>
                  <div className="mt-2 font-display text-[1.35rem] font-semibold text-white">{sourceItem.campaigns}</div>
                </div>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <InfoRow label="Tổng video" value={sourceItem.videos} emphasis />
                <InfoRow label="Video sẵn sàng" value={sourceItem.ready} />
              </div>
              <div className="mt-4 space-y-3">
                <SourceBreakdownBar label="Campaign" value={sourceItem.campaigns} max={overviewSourceMax} tone={sourceItem.tone} detail="Số chiến dịch đã gắn nguồn này." />
                <SourceBreakdownBar label="Tổng video" value={sourceItem.videos} max={overviewSourceMax} tone={sourceItem.tone} detail="Tổng video đã vào hàng chờ hoặc lịch sử đăng." />
                <SourceBreakdownBar label="Sẵn sàng đăng" value={sourceItem.ready} max={overviewSourceMax} tone={sourceItem.tone} detail="Video đang ở trạng thái ready." />
              </div>
              <div className="mt-4">
                <div className="mb-3 text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Xu hướng 7 ngày</div>
                <TrendTimelineChart labels={stats.source_trends?.labels || []} series={sourceItem.trend} />
              </div>
            </div>
          ))}
        </div>
        <div className="mt-5 rounded-[24px] border border-white/8 bg-black/10 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Chiến dịch cần xem theo nguồn</div>
              <div className="mt-1 text-sm text-[var(--text-soft)]">
                {overviewSourceFilter === 'all' ? 'Đang hiển thị campaign nóng của toàn bộ nguồn.' : `Đang lọc theo ${getSourcePlatformMeta(overviewSourceFilter).label.toLowerCase()}.`}
              </div>
            </div>
            <StatusPill tone={overviewFocusCampaigns.length ? 'amber' : 'emerald'}>{overviewFocusCampaigns.length} mục</StatusPill>
          </div>
          <div className="mt-4 space-y-3">
            {overviewFocusCampaigns.length === 0 ? (
              <div className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-4 text-sm text-[var(--text-soft)]">
                Không có chiến dịch nổi bật khớp bộ lọc nguồn.
              </div>
            ) : overviewFocusCampaigns.map((campaign) => {
              const sourceMeta = getSourcePlatformMeta(campaign.source_platform);
              return (
                <button key={campaign.id} type="button" onClick={() => handleSectionChange('campaigns')} className="w-full rounded-[22px] border border-white/8 bg-black/10 px-4 py-4 text-left transition hover:border-cyan-400/20 hover:bg-cyan-400/6">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-medium text-white">{campaign.name}</div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <StatusPill tone={sourceMeta.tone}>{sourceMeta.label}</StatusPill>
                        <StatusPill tone="slate">{getSyncStateMeta(campaign.last_sync_status).label}</StatusPill>
                      </div>
                    </div>
                    <div className="text-sm text-[var(--text-soft)]">{campaign.video_counts?.failed ?? 0} video lỗi</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </Panel>

      <Panel className="2xl:col-span-5" eyebrow="Nhịp vận hành" title="Mốc thời gian quan trọng">
        <div className="grid gap-4 xl:grid-cols-2">
          <InfoRow label="Lượt đăng kế tiếp" value={formatRelTime(stats.next_publish)} emphasis />
          <InfoRow label="Mốc cuối hàng chờ" value={formatDateTime(stats.queue_end)} />
          <InfoRow label="Bài đăng gần nhất" value={formatDateTime(stats.last_posted)} />
          <InfoRow label="Lần đồng bộ dashboard" value={formatDateTime(lastUpdatedAt)} />
          <InfoRow label="Chế độ tác vụ nền" value={systemInfo?.background_jobs_mode || 'Chưa có'} />
          <InfoRow label="Bộ lập lịch" value={healthInfo?.config?.scheduler_enabled ? `Bật, quét ${systemInfo?.scheduler_interval_minutes || 0} phút/lần` : 'Đang tắt'} />
        </div>
      </Panel>

      <Panel className="2xl:col-span-5" eyebrow="Fanpage" title="Tình trạng kết nối trang">
        <div className="space-y-3">
          {fbPages.length === 0 ? (
            <EmptyState title="Chưa có fanpage nào" description="Thêm fanpage để bắt đầu." />
          ) : (
            fbPages.map((pageItem) => {
              const validation = pageChecks[pageItem.page_id];
              const tokenMeta = getPageTokenMeta(getResolvedPageTokenKind(pageItem, validation));
              const messengerMeta = getMessengerConnectionMeta(validation);
              return (
                <div key={pageItem.page_id} className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-medium text-white">{pageItem.page_name}</div>
                      <div className="mt-1 text-xs text-[var(--text-muted)]">{pageItem.page_id}</div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusPill tone={tokenMeta.tone}>{tokenMeta.label}</StatusPill>
                      <StatusPill tone={messengerMeta.tone}>{messengerMeta.label}</StatusPill>
                    </div>
                  </div>
                  <div className="mt-3 text-sm text-[var(--text-soft)]">{pageItem.token_preview || 'Chưa có token để hiển thị.'}</div>
                  <div className="mt-2 text-xs text-[var(--text-muted)]">{messengerMeta.detail}</div>
                  <div className="mt-4 mobile-action-stack sm:justify-end">
                    <button type="button" className={BUTTON_SECONDARY} onClick={() => handleValidatePage(pageItem.page_id)} disabled={actionState[`page-validate-${pageItem.page_id}`]}>
                      <ShieldCheck className="h-4 w-4" />
                      {actionState[`page-validate-${pageItem.page_id}`] ? 'Đang kiểm tra...' : 'Xác minh & kiểm tra'}
                    </button>
                    <button
                      type="button"
                      className={cx(BUTTON_GHOST, 'border-rose-400/20 bg-rose-400/10 text-rose-100 hover:border-rose-400/30 hover:bg-rose-400/15')}
                      onClick={() => handleDeleteFacebookPage(pageItem.page_id, pageItem.page_name)}
                      disabled={!isAdmin || actionState[`delete-page-${pageItem.page_id}`]}
                    >
                      <Trash2 className="h-4 w-4" />
                      {actionState[`delete-page-${pageItem.page_id}`] ? 'Đang xóa...' : 'Xóa fanpage'}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </Panel>

      {isAdmin ? (
        <Panel className="2xl:col-span-12" eyebrow="Runtime config" title="Cấu hình hệ thống trên trang">
          <form onSubmit={handleRuntimeConfigSave} className="space-y-5">
            <div className="grid gap-4 xl:grid-cols-2">
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">BASE_URL</span>
                <input type="url" className={FIELD_CLASS} value={runtimeForm.BASE_URL} onChange={(event) => handleRuntimeFieldChange('BASE_URL', event.target.value)} placeholder="https://your-domain.example.com" />
                <div className="text-xs text-[var(--text-muted)]">Nguồn: {runtimeSettings.BASE_URL?.source === 'override' ? 'Dashboard' : 'Môi trường'}</div>
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Đường dẫn webhook</span>
                <input type="text" className={FIELD_CLASS} value={runtimeDerived.webhook_url || ''} readOnly />
                <div className="text-xs text-[var(--text-muted)]">Tự sinh từ `BASE_URL`.</div>
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">FB_VERIFY_TOKEN / Mã xác minh</span>
                <input type="text" className={FIELD_CLASS} value={runtimeForm.FB_VERIFY_TOKEN} onChange={(event) => handleRuntimeFieldChange('FB_VERIFY_TOKEN', event.target.value)} />
                <div className="text-xs text-[var(--text-muted)]">Nguồn: {runtimeSettings.FB_VERIFY_TOKEN?.source === 'override' ? 'Dashboard' : 'Môi trường'}</div>
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">FB_APP_SECRET</span>
                <input type="password" className={FIELD_CLASS} value={runtimeForm.FB_APP_SECRET} onChange={(event) => handleRuntimeFieldChange('FB_APP_SECRET', event.target.value)} placeholder="Để trống rồi lưu để quay về môi trường" />
                <div className="text-xs text-[var(--text-muted)]">Áp dụng ngay cho chữ ký webhook.</div>
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">GEMINI_API_KEY</span>
                <input type="password" className={FIELD_CLASS} value={runtimeForm.GEMINI_API_KEY} onChange={(event) => handleRuntimeFieldChange('GEMINI_API_KEY', event.target.value)} placeholder="Dùng cho caption và reply AI" />
                <div className="text-xs text-[var(--text-muted)]">Worker sẽ dùng khóa mới mà không cần sửa repo.</div>
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">TUNNEL_TOKEN</span>
                <input type="password" className={FIELD_CLASS} value={runtimeForm.TUNNEL_TOKEN} onChange={(event) => handleRuntimeFieldChange('TUNNEL_TOKEN', event.target.value)} placeholder="Cloudflare Tunnel token" />
                <div className="text-xs text-[var(--text-muted)]">Cần khởi động lại service `tunnel` để áp dụng.</div>
              </label>
            </div>
            <div className="grid gap-3 xl:grid-cols-3">
              <div className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-4 text-sm text-[var(--text-soft)]">Để trống một ô rồi lưu nếu muốn quay về giá trị môi trường.</div>
              <div className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-4 text-sm text-[var(--text-soft)]">Các giá trị được lưu ngoài repo và xuất ra file runtime riêng.</div>
              <div className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-4 text-sm text-[var(--text-soft)]">File runtime: {runtimeDerived.runtime_env_file || 'backend/runtime.env'}</div>
            </div>
            <div className="flex flex-wrap justify-end gap-2">
              <button type="button" className={BUTTON_GHOST} onClick={() => setRuntimeForm(extractRuntimeForm(runtimeConfig))}>
                Khôi phục giá trị đã lưu
              </button>
              <button type="submit" disabled={actionState['save-runtime-config']} className={BUTTON_PRIMARY}>
                <ShieldCheck className="h-4 w-4" />
                {actionState['save-runtime-config'] ? 'Đang lưu...' : 'Lưu cấu hình'}
              </button>
            </div>
          </form>
        </Panel>
      ) : null}
    </div>
  );

  const renderCampaignSection = () => (
    <div className="grid gap-6 2xl:grid-cols-12">
      <Panel className="2xl:col-span-7" eyebrow="Nguồn mới" title="Tạo chiến dịch đăng tự động">
        {(() => {
          const sourcePreview = detectSourcePreview(formData.source_url);
          return (
        <form onSubmit={handleCampaignSubmit} className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2 md:col-span-2">
            <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Trang đích</span>
            <select required className={FIELD_CLASS} value={formData.target_page_id} onChange={(event) => setFormData({ ...formData, target_page_id: event.target.value })} disabled={fbPages.length === 0}>
              {fbPages.length === 0 ? <option value="">Chưa có trang nào</option> : fbPages.map((pageItem) => <option key={pageItem.page_id} value={pageItem.page_id} style={{ color: '#06101a' }}>{pageItem.page_name}</option>)}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Tên chiến dịch</span>
            <input required type="text" className={FIELD_CLASS} placeholder="Ví dụ: Giải trí mỗi ngày" value={formData.name} onChange={(event) => setFormData({ ...formData, name: event.target.value })} />
          </label>
          <label className="space-y-2">
            <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Khoảng cách đăng (phút)</span>
            <input required type="number" min="0" className={FIELD_CLASS} value={formData.schedule_interval} onChange={(event) => setFormData({ ...formData, schedule_interval: parseInt(event.target.value, 10) || 0 })} />
          </label>
          <label className="space-y-2 md:col-span-2">
            <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Nguồn nội dung</span>
            <input required type="url" className={FIELD_CLASS} placeholder="https://www.tiktok.com/@... hoặc https://www.youtube.com/shorts/..." value={formData.source_url} onChange={(event) => setFormData({ ...formData, source_url: event.target.value })} />
          </label>
          <div className="md:col-span-2 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <div className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-4">
              <div className="flex flex-wrap items-center gap-2">
                <div className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Nhận diện nguồn</div>
                <StatusPill tone={sourcePreview.tone}>{sourcePreview.title}</StatusPill>
              </div>
              <div className="mt-3 text-sm leading-7 text-[var(--text-soft)]">{sourcePreview.detail}</div>
            </div>
            <div className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-4 text-sm leading-7 text-[var(--text-soft)]">
              <div className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Ví dụ hợp lệ</div>
              <div className="mt-3 break-all">TikTok: `https://www.tiktok.com/@creator/video/...`</div>
              <div className="mt-1 break-all">YouTube Shorts: `https://www.youtube.com/shorts/...`</div>
              <div className="mt-1 break-all">Nguồn Shorts: `https://www.youtube.com/@creator/shorts`</div>
            </div>
          </div>
          <label className="md:col-span-2 flex items-center gap-3 rounded-[24px] border border-white/8 bg-black/10 px-4 py-4">
            <input type="checkbox" checked={formData.auto_post} onChange={(event) => setFormData({ ...formData, auto_post: event.target.checked })} />
            <div>
              <div className="font-medium text-white">Cho phép tự đăng ngay khi hàng chờ đến lượt</div>
              <div className="text-sm text-[var(--text-soft)]">Worker sẽ tự đăng theo lịch.</div>
            </div>
          </label>
          <div className="md:col-span-2 flex justify-end">
            <button type="submit" disabled={fbPages.length === 0 || actionState['create-campaign']} className={BUTTON_PRIMARY}>
              <PlusCircle className="h-4 w-4" />
              {actionState['create-campaign'] ? 'Đang tạo chiến dịch...' : 'Tạo và đưa vào hàng đợi'}
            </button>
          </div>
        </form>
          );
        })()}
      </Panel>

      <Panel className="2xl:col-span-5" eyebrow="Fanpage" title="Kết nối nhiều trang từ một app Meta">
        <div className="space-y-5">
          <form onSubmit={handleDiscoverFacebookPages} className="rounded-[24px] border border-white/8 bg-black/10 p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="font-medium text-white">Import fanpage bằng User Access Token</div>
                <div className="mt-2 text-sm leading-7 text-[var(--text-soft)]">
                  Dùng một app Meta chung để tải danh sách fanpage bạn đang quản lý, rồi chọn nhiều trang để lưu vào hệ thống.
                </div>
              </div>
              <StatusPill tone="sky">Khuyến nghị</StatusPill>
            </div>
            <label className="mt-4 block space-y-2">
              <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">User Access Token</span>
              <input
                required
                type="password"
                className={FIELD_CLASS}
                placeholder="Dán User Access Token có quyền pages_show_list"
                value={fbImportToken}
                onChange={(event) => setFbImportToken(event.target.value)}
              />
            </label>
            <div className="mt-4 mobile-action-stack">
              <button type="submit" disabled={actionState['discover-pages']} className={BUTTON_PRIMARY}>
                <Globe2 className="h-4 w-4" />
                {actionState['discover-pages'] ? 'Đang tải danh sách...' : 'Tải danh sách fanpage'}
              </button>
              <button
                type="button"
                className={BUTTON_SECONDARY}
                onClick={handleRefreshFacebookPages}
                disabled={fbPages.length === 0 || actionState['refresh-pages']}
              >
                <RefreshCw className="h-4 w-4" />
                {actionState['refresh-pages'] ? 'Đang làm mới...' : 'Làm mới token fanpage đã có'}
              </button>
              {discoveredFbPages.length > 0 ? (
                <button type="button" className={BUTTON_GHOST} onClick={handleToggleAllDiscoveredPages}>
                  {allDiscoveredSelected ? 'Bỏ chọn tất cả' : 'Chọn tất cả'}
                </button>
              ) : null}
            </div>
            {discoverySubject ? (
              <div className="mt-4 rounded-[20px] border border-white/8 bg-black/10 px-4 py-3 text-sm text-[var(--text-soft)]">
                Đang xem fanpage của <span className="font-medium text-white">{discoverySubject.token_subject_name || discoverySubject.token_subject_id}</span>
              </div>
            ) : null}
          </form>

          {discoveredFbPages.length > 0 ? (
            <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="font-medium text-white">Chọn fanpage cần import</div>
                  <div className="mt-2 text-sm text-[var(--text-soft)]">
                    Hệ thống sẽ lấy luôn Page Access Token của từng fanpage được chọn từ User Access Token hiện tại.
                  </div>
                </div>
                <StatusPill tone="amber">{selectedDiscoveredPageIds.length}/{discoveredFbPages.length} đã chọn</StatusPill>
              </div>
              <div className="mt-4 space-y-3">
                {discoveredFbPages.map((pageItem) => {
                  const isSelected = selectedDiscoveredPageIds.includes(pageItem.page_id);
                  return (
                    <label
                      key={pageItem.page_id}
                      className={cx(
                        'flex cursor-pointer items-start gap-3 rounded-[20px] border px-4 py-4 transition',
                        isSelected
                          ? 'border-cyan-400/25 bg-cyan-400/10'
                          : 'border-white/8 bg-black/10 hover:border-white/15 hover:bg-black/15',
                      )}
                    >
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={isSelected}
                        onChange={() => handleToggleDiscoveredPage(pageItem.page_id)}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <div className="font-medium text-white">{pageItem.page_name}</div>
                          {pageItem.already_configured ? <StatusPill tone="amber">Đã có trong hệ thống</StatusPill> : null}
                          {pageItem.has_page_access_token ? <StatusPill tone="emerald">Có Page Token</StatusPill> : <StatusPill tone="rose">Thiếu Page Token</StatusPill>}
                        </div>
                        <div className="mt-1 text-xs text-[var(--text-muted)]">{pageItem.page_id}</div>
                        <div className="mt-3 grid gap-3 sm:grid-cols-2">
                          <InfoRow label="Danh mục" value={pageItem.category || 'Chưa rõ'} compact />
                          <InfoRow label="Quyền" value={(pageItem.tasks || []).join(', ') || 'Chưa có'} compact />
                        </div>
                      </div>
                    </label>
                  );
                })}
              </div>
              <div className="mt-4 mobile-action-stack">
                <button
                  type="button"
                  className={BUTTON_PRIMARY}
                  onClick={handleImportFacebookPages}
                  disabled={selectedDiscoveredPageIds.length === 0 || actionState['import-pages']}
                >
                  <PlusCircle className="h-4 w-4" />
                  {actionState['import-pages'] ? 'Đang import...' : 'Import fanpage đã chọn'}
                </button>
                <button
                  type="button"
                  className={BUTTON_GHOST}
                  onClick={() => {
                    setDiscoveredFbPages([]);
                    setSelectedDiscoveredPageIds([]);
                    setDiscoverySubject(null);
                  }}
                >
                  Xóa danh sách
                </button>
              </div>
            </div>
          ) : null}

          <form onSubmit={handleFbSubmit} className="rounded-[24px] border border-white/8 bg-black/10 p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="font-medium text-white">Nhập tay fanpage</div>
                <div className="mt-2 text-sm text-[var(--text-soft)]">
                  Giữ làm chế độ dự phòng khi bạn chỉ muốn thêm một trang riêng lẻ bằng Page Access Token.
                </div>
              </div>
              <StatusPill tone="slate">Fallback</StatusPill>
            </div>
            <div className="mt-4 space-y-4">
              <label className="block space-y-2">
                <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Mã trang</span>
                <input required type="text" className={FIELD_CLASS} placeholder="Page ID" value={fbForm.page_id} onChange={(event) => setFbForm({ ...fbForm, page_id: event.target.value })} />
              </label>
              <label className="block space-y-2">
                <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Tên trang</span>
                <input required type="text" className={FIELD_CLASS} placeholder="Tên fanpage" value={fbForm.page_name} onChange={(event) => setFbForm({ ...fbForm, page_name: event.target.value })} />
              </label>
              <label className="block space-y-2">
                <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Page Access Token</span>
                <input required type="password" className={FIELD_CLASS} placeholder="Dán token trang Facebook thật" value={fbForm.long_lived_access_token} onChange={(event) => setFbForm({ ...fbForm, long_lived_access_token: event.target.value })} />
              </label>
              <button type="submit" disabled={actionState['save-page']} className={cx(BUTTON_PRIMARY, 'w-full')}>
                <Globe2 className="h-4 w-4" />
                {actionState['save-page'] ? 'Đang lưu token...' : 'Lưu cấu hình fanpage'}
              </button>
            </div>
          </form>
        </div>
      </Panel>

      <Panel className="2xl:col-span-4" eyebrow="Danh sách trang" title="Fanpage đang sẵn sàng">
        <div className="space-y-4">
          {fbPages.length === 0 ? (
            <EmptyState title="Chưa có fanpage" description="Thêm fanpage để dùng." />
          ) : (
            fbPages.map((pageItem) => {
              const validation = pageChecks[pageItem.page_id];
              const tokenMeta = getPageTokenMeta(getResolvedPageTokenKind(pageItem, validation));
              const messengerMeta = getMessengerConnectionMeta(validation);
              return (
                <div key={pageItem.page_id} className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium text-white">{pageItem.page_name}</div>
                      <div className="mt-1 text-xs text-[var(--text-muted)]">{pageItem.page_id}</div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <StatusPill tone={tokenMeta.tone}>{tokenMeta.label}</StatusPill>
                        <StatusPill tone={messengerMeta.tone}>{messengerMeta.label}</StatusPill>
                      </div>
                    </div>
                  </div>
                  <div className="mt-3 text-sm text-[var(--text-soft)]">{pageItem.token_preview || 'Chưa có token để hiển thị.'}</div>
                  <div className="mt-3 rounded-2xl border border-white/8 bg-black/10 px-3 py-3 text-sm text-[var(--text-soft)]">{messengerMeta.detail}</div>
                  {validation ? (
                    <div className={cx('mt-3 rounded-2xl border px-3 py-3 text-sm', validation.ok ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100' : 'border-rose-400/20 bg-rose-400/10 text-rose-100')}>
                      <div>{validation.message}</div>
                      <div className="mt-1 text-xs opacity-80">Kiểm tra lúc {formatDateTime(validation.checked_at)}</div>
                    </div>
                  ) : null}
                  <div className="mobile-action-stack mt-4 sm:justify-end">
                    <button
                      type="button"
                      className={BUTTON_GHOST}
                      onClick={() => handleSubscribeMessages(pageItem.page_id)}
                      disabled={actionState[`page-subscribe-${pageItem.page_id}`]}
                    >
                      <MessagesSquare className="h-4 w-4" />
                          {actionState[`page-subscribe-${pageItem.page_id}`] ? 'Đang đăng ký...' : 'Đăng ký webhook'}
                    </button>
                    <button type="button" className={BUTTON_SECONDARY} onClick={() => handleValidatePage(pageItem.page_id)} disabled={actionState[`page-validate-${pageItem.page_id}`]}>
                      <ShieldCheck className="h-4 w-4" />
                      {actionState[`page-validate-${pageItem.page_id}`] ? 'Đang kiểm tra...' : 'Xác minh & kiểm tra'}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </Panel>

      <Panel className="2xl:col-span-8" eyebrow="Danh mục chiến dịch" title="Toàn bộ chiến dịch đang quản lý">
        <div className="mb-5 grid gap-4 xl:grid-cols-[220px_minmax(0,1fr)]">
          <label className="space-y-2">
            <span className="flex items-center gap-2 text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">
              <Filter className="h-3.5 w-3.5" />
              Nguồn chiến dịch
            </span>
            <select className={FIELD_CLASS} value={campaignSourceFilter} onChange={(event) => setCampaignSourceFilter(event.target.value)}>
              {SOURCE_PLATFORM_FILTERS.map((option) => <option key={option.value} value={option.value} style={{ color: '#06101a' }}>{option.label}</option>)}
            </select>
          </label>
          <div className="grid gap-3 sm:grid-cols-3">
            <InfoRow label="Campaign TikTok" value={campaignSourceSummary.tiktok} emphasis={campaignSourceFilter === 'tiktok'} />
            <InfoRow label="Campaign Shorts" value={campaignSourceSummary.youtube} emphasis={campaignSourceFilter === 'youtube'} />
            <InfoRow label="Khớp bộ lọc" value={filteredCampaigns.length} />
          </div>
        </div>
        {filteredCampaigns.length === 0 ? (
          <EmptyState
            title={campaigns.length === 0 ? 'Chưa có chiến dịch nào' : 'Không có chiến dịch khớp bộ lọc'}
            description={campaigns.length === 0 ? 'Tạo chiến dịch để bắt đầu.' : 'Đổi bộ lọc nguồn để xem thêm.'}
          />
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            {filteredCampaigns.map((campaign) => {
              const syncMeta = getSyncStateMeta(campaign.last_sync_status);
              const isExpanded = !!expandedItems[`campaign:${campaign.id}`];
              const sourcePlatformMeta = getSourcePlatformMeta(campaign.source_platform);
              return (
                <article key={campaign.id} className="rounded-[22px] border border-white/8 bg-black/10 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="font-display text-lg font-semibold text-white sm:text-[1.15rem]">{campaign.name}</div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <span className={cx('inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium', getStatusClasses(campaign.status))}>
                          <StatusIcon status={campaign.status} />
                          {getStatusLabel(campaign.status)}
                        </span>
                        <span className={cx('inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium', getStatusClasses(syncMeta.tone))}>
                          <StatusIcon status={syncMeta.tone} />
                          {syncMeta.label}
                        </span>
                        <StatusPill tone={sourcePlatformMeta.tone}>{sourcePlatformMeta.label}</StatusPill>
                        <StatusPill tone="slate">{getSourceKindLabel(campaign.source_kind)}</StatusPill>
                      </div>
                    </div>
                    <div className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-3 text-right">
                      <div className="text-[10px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Trang đích</div>
                      <div className="mt-2 text-sm font-medium text-white">{campaign.target_page_name || campaign.target_page_id || 'Chưa gắn'}</div>
                    </div>
                  </div>
                  <div className="mt-3 text-sm text-[var(--text-soft)]">
                    {(campaign.video_counts?.total ?? 0)} video • {(campaign.video_counts?.ready ?? 0)} sẵn sàng • {campaign.schedule_interval || 0} phút/lần
                  </div>
                  <div className="mt-3 flex justify-start">
                    <DetailToggle expanded={isExpanded} onClick={() => toggleExpandedItem(`campaign:${campaign.id}`)} />
                  </div>
                  {isExpanded ? (
                    <>
                      <div className="mt-4 rounded-[22px] border border-white/8 bg-black/10 px-4 py-3">
                        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">
                          <CloudDownload className="h-3.5 w-3.5" />
                          Nguồn crawl
                        </div>
                        <a href={campaign.source_url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-2 break-all text-sm text-cyan-100 hover:text-white">
                          {campaign.source_url}
                          <ExternalLink className="h-4 w-4 shrink-0" />
                        </a>
                      </div>
                      <div className="mt-4 grid gap-3 sm:grid-cols-3">
                        <InfoRow label="Nền tảng nguồn" value={sourcePlatformMeta.label} />
                        <InfoRow label="Kiểu nguồn" value={getSourceKindLabel(campaign.source_kind)} />
                        <InfoRow label="Tổng video" value={campaign.video_counts?.total ?? 0} emphasis />
                        <InfoRow label="Sẵn sàng" value={campaign.video_counts?.ready ?? 0} />
                        <InfoRow label="Thất bại" value={campaign.video_counts?.failed ?? 0} />
                        <InfoRow label="Khoảng cách" value={`${campaign.schedule_interval || 0} phút`} />
                        <InfoRow label="Tự đăng" value={campaign.auto_post ? 'Đang bật' : 'Đang tắt'} />
                        <InfoRow label="Lần sync gần nhất" value={formatDateTime(campaign.last_synced_at)} />
                      </div>
                      {campaign.last_sync_error ? <div className="mt-4 rounded-[22px] border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm leading-7 text-rose-100">{campaign.last_sync_error}</div> : null}
                      <div className="mobile-action-stack mt-5">
                        <button type="button" className={BUTTON_SECONDARY} onClick={() => handleCampaignAction(campaign, 'sync')} disabled={actionState[`campaign-${campaign.id}-sync`]}>
                          <RefreshCw className={cx('h-4 w-4', actionState[`campaign-${campaign.id}-sync`] ? 'animate-spin' : '')} />
                          Đồng bộ lại
                        </button>
                        {campaign.status === 'active' ? (
                          <button type="button" className={BUTTON_GHOST} onClick={() => handleCampaignAction(campaign, 'pause')} disabled={actionState[`campaign-${campaign.id}-pause`]}>
                            <Pause className="h-4 w-4" />
                            Tạm dừng
                          </button>
                        ) : (
                          <button type="button" className={BUTTON_GHOST} onClick={() => handleCampaignAction(campaign, 'resume')} disabled={actionState[`campaign-${campaign.id}-resume`]}>
                            <Play className="h-4 w-4" />
                            Kích hoạt lại
                          </button>
                        )}
                        <button type="button" className={cx(BUTTON_GHOST, 'text-rose-100')} onClick={() => handleCampaignAction(campaign, 'delete')} disabled={actionState[`campaign-${campaign.id}-delete`]}>
                          <Trash2 className="h-4 w-4" />
                          Xóa chiến dịch
                        </button>
                      </div>
                    </>
                  ) : null}
                </article>
              );
            })}
          </div>
        )}
      </Panel>
    </div>
  );
  const renderQueueSection = () => (
    <div className="space-y-6">
      <Panel eyebrow="Affiliate" title="Comment aff cần operator xử lý">
        {affiliateOperatorItems.length === 0 ? (
          <EmptyState title="Chưa có video nào cần comment tay" description="Nếu comment aff tự động lỗi sau retry, mục đó sẽ hiện ở đây để operator xử lý." />
        ) : (
          <div className="space-y-4">
            {affiliateOperatorItems.map((item) => {
              const sourcePlatformMeta = getSourcePlatformMeta(item.source_platform);
              return (
                <article key={item.id} className="rounded-[22px] border border-rose-400/15 bg-rose-400/5 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="font-display text-base font-semibold text-white sm:text-[1.05rem]">
                        {item.campaign_name || 'Chưa rõ chiến dịch'}
                      </div>
                      <div className="mt-1 text-sm text-[var(--text-soft)]">
                        {item.target_page_name || item.target_page_id || 'Chưa rõ fanpage'} • {item.original_id}
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <span className={cx('inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium', getStatusClasses(item.affiliate_comment_status))}>
                          <AlertTriangle className="h-3.5 w-3.5" />
                          {getStatusLabel(item.affiliate_comment_status)}
                        </span>
                        <StatusPill tone={sourcePlatformMeta.tone}>{sourcePlatformMeta.label}</StatusPill>
                        <StatusPill tone="slate">{getSourceKindLabel(item.source_kind)}</StatusPill>
                        <StatusPill tone="amber">Attempt {item.affiliate_comment_attempts ?? 0}</StatusPill>
                      </div>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <InfoRow label="Đăng lúc" value={formatDateTime(item.updated_at)} emphasis />
                      <InfoRow label="Link bài đăng" value={item.fb_permalink_url ? 'Có' : 'Chưa có'} />
                    </div>
                  </div>
                  {item.affiliate_comment_error ? (
                    <div className="mt-4 rounded-[20px] border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">
                      {item.affiliate_comment_error}
                    </div>
                  ) : null}
                  <textarea
                    className={cx(FIELD_CLASS, 'mt-4 min-h-[140px] resize-y')}
                    value={affiliateManualDrafts[item.id] ?? item.affiliate_comment_text ?? ''}
                    onChange={(event) => handleAffiliateDraftChange(item.id, event.target.value)}
                    placeholder="Nhập nội dung comment affiliate để operator gửi tay..."
                  />
                  <div className="mobile-action-stack mt-4">
                    {item.fb_permalink_url ? (
                      <a href={item.fb_permalink_url} target="_blank" rel="noreferrer" className={BUTTON_GHOST}>
                        <ExternalLink className="h-4 w-4" />
                        Mở bài đăng
                      </a>
                    ) : null}
                    <button
                      type="button"
                      className={BUTTON_SECONDARY}
                      onClick={() => handleRetryAffiliateComment(item.id)}
                      disabled={actionState[`affiliate-retry-${item.id}`]}
                    >
                      <RefreshCw className="h-4 w-4" />
                      {actionState[`affiliate-retry-${item.id}`] ? 'Đang xếp lại...' : 'Retry tự động'}
                    </button>
                    <button
                      type="button"
                      className={BUTTON_PRIMARY}
                      onClick={() => handleManualAffiliateComment(item.id)}
                      disabled={actionState[`affiliate-manual-${item.id}`]}
                    >
                      <MessagesSquare className="h-4 w-4" />
                      {actionState[`affiliate-manual-${item.id}`] ? 'Đang gửi...' : 'Comment tay ngay'}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </Panel>

      <Panel eyebrow="Bộ lọc" title="Hàng chờ đăng bài">
        <div className="grid gap-4 xl:grid-cols-[220px_280px_220px_minmax(0,1fr)]">
          <label className="space-y-2">
            <span className="flex items-center gap-2 text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">
              <Filter className="h-3.5 w-3.5" />
              Trạng thái video
            </span>
            <select className={FIELD_CLASS} value={filters.status} onChange={(event) => {
              setPage(1);
              setFilters((current) => ({ ...current, status: event.target.value }));
            }}>
              {STATUS_FILTERS.map((option) => <option key={option.value} value={option.value} style={{ color: '#06101a' }}>{option.label}</option>)}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Chiến dịch</span>
            <select className={FIELD_CLASS} value={filters.campaignId} onChange={(event) => {
              setPage(1);
              setFilters((current) => ({ ...current, campaignId: event.target.value }));
            }}>
              <option value="all" style={{ color: '#06101a' }}>Tất cả chiến dịch</option>
              {campaigns.map((campaign) => <option key={campaign.id} value={campaign.id} style={{ color: '#06101a' }}>{campaign.name}</option>)}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Nguồn nội dung</span>
            <select className={FIELD_CLASS} value={filters.sourcePlatform} onChange={(event) => {
              setPage(1);
              setFilters((current) => ({ ...current, sourcePlatform: event.target.value }));
            }}>
              {SOURCE_PLATFORM_FILTERS.map((option) => <option key={option.value} value={option.value} style={{ color: '#06101a' }}>{option.label}</option>)}
            </select>
          </label>
          <div className="grid gap-3 sm:grid-cols-5">
            <InfoRow label="Khớp bộ lọc" value={filteredVideoTotal} emphasis />
            <InfoRow label="TikTok sẵn sàng" value={stats.by_source?.tiktok?.ready ?? 0} />
            <InfoRow label="Shorts sẵn sàng" value={stats.by_source?.youtube?.ready ?? 0} />
            <InfoRow label="Đến lượt kế tiếp" value={formatRelTime(stats.next_publish)} />
            <InfoRow label="Cuối hàng chờ" value={formatDateTime(stats.queue_end)} />
          </div>
        </div>
      </Panel>

      <Panel eyebrow="Danh sách video" title="Can thiệp trực tiếp vào lịch đăng" action={<div className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-3 text-sm text-[var(--text-soft)]">Trang {page} / {totalPages}</div>}>
        {videos.length === 0 ? (
          <EmptyState title="Không có video phù hợp bộ lọc" description="Thử đổi bộ lọc." />
        ) : (
          <div className="space-y-4">
            {videos.map((video) => {
              const isExpanded = !!expandedItems[`video:${video.id}`];
              const sourcePlatformMeta = getSourcePlatformMeta(video.source_platform);
              return (
                <article key={video.id} className="rounded-[22px] border border-white/8 bg-black/10 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">{video.campaign_name || 'Chưa rõ chiến dịch'}</div>
                      <div className="mt-2 font-display text-base font-semibold text-white sm:text-[1.05rem]">{video.original_id}</div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <span className={cx('inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium', getStatusClasses(video.status))}>
                          <StatusIcon status={video.status} />
                          {getStatusLabel(video.status)}
                        </span>
                        <StatusPill tone={sourcePlatformMeta.tone}>{sourcePlatformMeta.label}</StatusPill>
                        <StatusPill tone="slate">{getSourceKindLabel(video.source_kind)}</StatusPill>
                        <StatusPill tone={video.target_page_name ? 'sky' : 'amber'} icon={Globe2}>{video.target_page_name || video.target_page_id || 'Chưa gắn fanpage'}</StatusPill>
                      </div>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <InfoRow label="Lịch đăng" value={formatDateTime(video.publish_time)} emphasis />
                      <InfoRow label="Số lần retry" value={video.retry_count ?? 0} />
                    </div>
                  </div>
                  <div className="mt-3 text-sm text-[var(--text-soft)]">
                    {summarizeText(captionDrafts[video.id] ?? video.ai_caption ?? video.original_caption, 'Chưa có caption để xem nhanh.')}
                  </div>
                  <div className="mt-3 flex justify-start">
                    <DetailToggle expanded={isExpanded} onClick={() => toggleExpandedItem(`video:${video.id}`)} />
                  </div>
                  {isExpanded ? (
                    <div className="mt-5 grid gap-5 xl:grid-cols-[0.88fr_1.12fr]">
                      <div className="space-y-4">
                        <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">
                            <CloudDownload className="h-3.5 w-3.5" />
                            Nguồn video
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <StatusPill tone={sourcePlatformMeta.tone}>{sourcePlatformMeta.label}</StatusPill>
                            <StatusPill tone="slate">{getSourceKindLabel(video.source_kind)}</StatusPill>
                          </div>
                          {video.source_video_url ? (
                            <a href={video.source_video_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-2 break-all text-sm text-cyan-100 hover:text-white">
                              {video.source_video_url}
                              <ExternalLink className="h-4 w-4 shrink-0" />
                            </a>
                          ) : <div className="mt-3 text-sm text-[var(--text-soft)]">Chưa có đường dẫn nguồn.</div>}
                        </div>
                        <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                          <div className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Caption gốc</div>
                          <div className="mt-3 whitespace-pre-wrap text-sm leading-7 text-[var(--text-soft)]">{video.original_caption || 'Chưa có caption gốc từ nguồn.'}</div>
                        </div>
                        {video.last_error ? <div className="rounded-[24px] border border-rose-400/20 bg-rose-400/10 p-4 text-sm leading-7 text-rose-100">{video.last_error}</div> : null}
                      </div>
                      <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                        <div className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Caption AI có thể chỉnh tay</div>
                        <textarea className={cx(FIELD_CLASS, 'mt-4 min-h-[220px] resize-y')} value={captionDrafts[video.id] ?? ''} onChange={(event) => handleCaptionChange(video.id, event.target.value)} placeholder="Chú thích AI sẽ xuất hiện ở đây..." />
                        <div className="mobile-action-stack mt-4">
                          {video.status === 'ready' ? <button type="button" className={BUTTON_SECONDARY} onClick={() => handlePrioritize(video.id)} disabled={actionState[`video-${video.id}`]}><Play className="h-4 w-4" />{actionState[`video-${video.id}`] ? 'Đang ưu tiên...' : 'Đẩy lên đầu hàng chờ'}</button> : null}
                          {video.status === 'failed' ? <button type="button" className={BUTTON_SECONDARY} onClick={() => handleRetryVideo(video.id)} disabled={actionState[`video-retry-${video.id}`]}><RefreshCw className="h-4 w-4" />{actionState[`video-retry-${video.id}`] ? 'Đang retry...' : 'Retry video'}</button> : null}
                          <button type="button" className={BUTTON_GHOST} onClick={() => handleRegenerateCaption(video.id)} disabled={actionState[`video-generate-${video.id}`]}>
                            <Zap className="h-4 w-4" />
                            {actionState[`video-generate-${video.id}`] ? 'Đang tạo lại...' : 'Tạo lại caption'}
                          </button>
                          <button type="button" className={BUTTON_PRIMARY} onClick={() => handleSaveCaption(video.id)} disabled={actionState[`video-caption-${video.id}`]}>
                            <CircleCheck className="h-4 w-4" />
                            {actionState[`video-caption-${video.id}`] ? 'Đang lưu...' : 'Lưu caption'}
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>
        )}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-white/8 pt-5">
          <div className="text-sm text-[var(--text-soft)]">Đang xem {videos.length} video ở trang {page}.</div>
          <div className="mobile-action-stack sm:justify-end">
            <button type="button" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))} className={BUTTON_GHOST}>Trước</button>
            <button type="button" disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))} className={BUTTON_GHOST}>Sau</button>
          </div>
        </div>
      </Panel>
    </div>
  );

  const renderEngagementSection = () => (
    <div className="space-y-6">
      <Panel eyebrow="Luồng bình luận" title="Phản hồi Facebook theo từng tình huống">
        <div className="grid gap-4 lg:grid-cols-3">
          <InfoRow label="Bình luận đang chờ" value={systemInfo?.pending_comment_replies ?? 0} emphasis />
          <InfoRow label="Tổng mục đang hiển thị" value={interactions.length} />
          <InfoRow label="Trang đã kết nối" value={stats.connected_pages ?? 0} />
        </div>
      </Panel>
      <Panel eyebrow="Nhật ký tương tác" title="Các bình luận gần nhất">
        {interactions.length === 0 ? (
          <EmptyState title="Chưa có bình luận nào" description="Bình luận sẽ hiện tại đây." />
        ) : (
          <div className="space-y-4">
            {interactions.map((log) => {
              const targetPage = fbPages.find((pageItem) => pageItem.page_id === log.page_id);
              const isExpanded = !!expandedItems[`comment:${log.id}`];
              return (
                <article key={log.id} className="rounded-[22px] border border-white/8 bg-black/10 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="font-medium text-white">{targetPage?.page_name || log.page_id}</div>
                      <div className="mt-1 text-xs text-[var(--text-muted)]">Người dùng: {log.user_id} • Bình luận: {log.comment_id}</div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={cx('inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium', getStatusClasses(log.status))}>
                        <StatusIcon status={log.status} />
                        {getStatusLabel(log.status)}
                      </span>
                      <StatusPill tone="slate" icon={Clock}>{formatDateTime(log.created_at)}</StatusPill>
                    </div>
                  </div>
                  <div className="mt-3 text-sm text-[var(--text-soft)]">{summarizeText(log.user_message, 'Chưa có bình luận.')}</div>
                  <div className="mt-3 flex justify-start">
                    <DetailToggle expanded={isExpanded} onClick={() => toggleExpandedItem(`comment:${log.id}`)} />
                  </div>
                  {isExpanded ? (
                    <div className="mt-5 grid gap-4 xl:grid-cols-2">
                      <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                        <div className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Tin nhắn người dùng</div>
                        <div className="mt-3 whitespace-pre-wrap text-sm leading-7 text-white">{log.user_message}</div>
                      </div>
                      <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                        <div className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Phản hồi AI</div>
                        <div className="mt-3 whitespace-pre-wrap text-sm leading-7 text-[var(--text-soft)]">{log.ai_reply || 'AI chưa tạo phản hồi cho mục này.'}</div>
                      </div>
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>
        )}
      </Panel>
    </div>
  );

  const renderMessagesSection = () => (
    <div className="space-y-6">
      <Panel eyebrow="Thiết lập theo fanpage" title="Prompt AI cho comment và inbox">
        <div className="grid gap-4 lg:grid-cols-3">
          <InfoRow label="Inbox đang chờ" value={systemInfo?.pending_message_replies ?? 0} emphasis />
          <InfoRow label="Fanpage bật inbox AI" value={systemInfo?.message_auto_reply_pages ?? 0} />
          <InfoRow label="Fanpage bật aff comment" value={affiliateEnabledPages} />
          <InfoRow label="Webhook fanpage đã nối" value={`${connectedMessagePages}/${fbPages.length || 0}`} />
          <InfoRow label="Cần operator xử lý" value={handoffConversations.length} emphasis={handoffConversations.length > 0} />
          <InfoRow label="Aff cần operator" value={affiliateOperatorItems.length} emphasis={affiliateOperatorItems.length > 0} />
          <InfoRow label="Đã xử lý" value={resolvedConversations.length} />
          <InfoRow label="Tổng conversation" value={conversationList.length} />
        </div>
      </Panel>

      <Panel eyebrow="Prompt theo trang" title="Bật tắt và soạn quy tắc trả lời">
        {fbPages.length === 0 ? (
          <EmptyState title="Chưa có fanpage" description="Thêm fanpage trước khi cấu hình AI." />
        ) : (
          <div className="space-y-4">
            {fbPages.map((pageItem) => {
              const draft = replyAutomationDrafts[pageItem.page_id] || buildReplyAutomationDraft(pageItem);
              const validation = pageChecks[pageItem.page_id];
              const tokenMeta = getPageTokenMeta(getResolvedPageTokenKind(pageItem, validation));
              const messengerMeta = getMessengerConnectionMeta(validation);
              const isExpanded = !!expandedItems[`page-ai:${pageItem.page_id}`];

              return (
                <article key={pageItem.page_id} className="rounded-[22px] border border-white/8 bg-black/10 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="font-display text-lg font-semibold text-white sm:text-[1.15rem]">{pageItem.page_name}</div>
                      <div className="mt-1 text-xs text-[var(--text-muted)]">{pageItem.page_id}</div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <StatusPill tone={tokenMeta.tone}>{tokenMeta.label}</StatusPill>
                        <StatusPill tone={messengerMeta.tone}>{messengerMeta.label}</StatusPill>
                        <StatusPill tone={draft.comment_auto_reply_enabled ? 'emerald' : 'slate'}>
                          Comment: {draft.comment_auto_reply_enabled ? 'Bật' : 'Tắt'}
                        </StatusPill>
                        <StatusPill tone={draft.message_auto_reply_enabled ? 'emerald' : 'slate'}>
                          Inbox: {draft.message_auto_reply_enabled ? 'Bật' : 'Tắt'}
                        </StatusPill>
                        <StatusPill tone={draft.message_reply_schedule_enabled ? 'sky' : 'slate'}>
                          Giờ: {draft.message_reply_schedule_enabled ? `${draft.message_reply_start_time}-${draft.message_reply_end_time}` : 'Cả ngày'}
                        </StatusPill>
                        <StatusPill tone={draft.message_reply_cooldown_minutes > 0 ? 'amber' : 'slate'}>
                          Cooldown: {draft.message_reply_cooldown_minutes > 0 ? `${draft.message_reply_cooldown_minutes} phút` : 'Tắt'}
                        </StatusPill>
                        <StatusPill tone={draft.affiliate_comment_enabled ? 'rose' : 'slate'}>
                          Aff: {draft.affiliate_comment_enabled ? `${draft.affiliate_comment_delay_seconds}s` : 'Tắt'}
                        </StatusPill>
                      </div>
                      <div className="mt-3 rounded-[20px] border border-white/8 bg-black/10 px-4 py-3 text-sm text-[var(--text-soft)]">
                        {messengerMeta.detail}
                      </div>
                    </div>
                    <div className="mobile-action-stack">
                      <button
                        type="button"
                        className={BUTTON_GHOST}
                        onClick={() => handleSubscribeMessages(pageItem.page_id)}
                        disabled={actionState[`page-subscribe-${pageItem.page_id}`]}
                      >
                        <MessagesSquare className="h-4 w-4" />
                    {actionState[`page-subscribe-${pageItem.page_id}`] ? 'Đang đăng ký...' : 'Đăng ký webhook'}
                      </button>
                      <button
                        type="button"
                        className={BUTTON_SECONDARY}
                        onClick={() => handleValidatePage(pageItem.page_id)}
                        disabled={actionState[`page-validate-${pageItem.page_id}`]}
                      >
                        <ShieldCheck className="h-4 w-4" />
                        {actionState[`page-validate-${pageItem.page_id}`] ? 'Đang kiểm tra...' : 'Kiểm tra kết nối'}
                      </button>
                      <DetailToggle expanded={isExpanded} onClick={() => toggleExpandedItem(`page-ai:${pageItem.page_id}`)} />
                    </div>
                  </div>
                  {isExpanded ? (
                    <>
                      <div className="mt-4 mobile-action-stack">
                        <button type="button" className={BUTTON_GHOST} onClick={() => handleReplyAutomationReset(pageItem)}>
                          Khôi phục
                        </button>
                        <button
                          type="button"
                          className={BUTTON_PRIMARY}
                          onClick={() => handleReplyAutomationSave(pageItem.page_id)}
                          disabled={actionState[`reply-automation-${pageItem.page_id}`]}
                        >
                          <Bot className="h-4 w-4" />
                          {actionState[`reply-automation-${pageItem.page_id}`] ? 'Đang lưu...' : 'Lưu prompt AI'}
                        </button>
                      </div>
                      <div className="mt-5 grid gap-4 xl:grid-cols-2">
                        <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                          <label className="flex items-center justify-between gap-3 rounded-[20px] border border-white/8 bg-black/10 px-4 py-3">
                            <div>
                              <div className="font-medium text-white">Tự động trả lời comment</div>
                              <div className="mt-1 text-sm text-[var(--text-soft)]">Luồng bình luận hiện có.</div>
                            </div>
                            <input
                              type="checkbox"
                              checked={draft.comment_auto_reply_enabled}
                              onChange={(event) => handleReplyAutomationDraftChange(pageItem.page_id, 'comment_auto_reply_enabled', event.target.checked)}
                            />
                          </label>
                          <div className="mt-4 text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Prompt comment</div>
                          <textarea
                            className={cx(FIELD_CLASS, 'mt-3 min-h-[180px] resize-y')}
                            value={draft.comment_ai_prompt}
                            onChange={(event) => handleReplyAutomationDraftChange(pageItem.page_id, 'comment_ai_prompt', event.target.value)}
                            placeholder="Để trống nếu muốn dùng prompt mặc định cho comment."
                          />
                        </div>

                        <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                          <label className="flex items-center justify-between gap-3 rounded-[20px] border border-white/8 bg-black/10 px-4 py-3">
                            <div>
                              <div className="font-medium text-white">Tự động trả lời inbox</div>
                              <div className="mt-1 text-sm text-[var(--text-soft)]">Luồng Messenger mới.</div>
                            </div>
                            <input
                              type="checkbox"
                              checked={draft.message_auto_reply_enabled}
                              onChange={(event) => handleReplyAutomationDraftChange(pageItem.page_id, 'message_auto_reply_enabled', event.target.checked)}
                            />
                          </label>
                          <div className="mt-4 text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Prompt inbox</div>
                          <textarea
                            className={cx(FIELD_CLASS, 'mt-3 min-h-[180px] resize-y')}
                            value={draft.message_ai_prompt}
                            onChange={(event) => handleReplyAutomationDraftChange(pageItem.page_id, 'message_ai_prompt', event.target.value)}
                            placeholder="Để trống nếu muốn dùng prompt mặc định cho inbox."
                          />
                          <div className="mt-4 grid gap-4 md:grid-cols-2">
                            <label className="space-y-2">
                              <span className="flex items-center justify-between text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">
                                <span>Khung giờ</span>
                                <input
                                  type="checkbox"
                                  checked={draft.message_reply_schedule_enabled}
                                  onChange={(event) => handleReplyAutomationDraftChange(pageItem.page_id, 'message_reply_schedule_enabled', event.target.checked)}
                                />
                              </span>
                              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                                <input
                                  type="time"
                                  className={FIELD_CLASS}
                                  value={draft.message_reply_start_time}
                                  onChange={(event) => handleReplyAutomationDraftChange(pageItem.page_id, 'message_reply_start_time', event.target.value)}
                                  disabled={!draft.message_reply_schedule_enabled}
                                />
                                <input
                                  type="time"
                                  className={FIELD_CLASS}
                                  value={draft.message_reply_end_time}
                                  onChange={(event) => handleReplyAutomationDraftChange(pageItem.page_id, 'message_reply_end_time', event.target.value)}
                                  disabled={!draft.message_reply_schedule_enabled}
                                />
                              </div>
                            </label>
                            <label className="space-y-2">
                              <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Cooldown cùng người gửi</span>
                              <input
                                type="number"
                                min="0"
                                max="1440"
                                className={FIELD_CLASS}
                                value={draft.message_reply_cooldown_minutes}
                                onChange={(event) => handleReplyAutomationDraftChange(pageItem.page_id, 'message_reply_cooldown_minutes', parseInt(event.target.value, 10) || 0)}
                              />
                              <div className="text-sm text-[var(--text-soft)]">Tính theo phút, giờ Việt Nam.</div>
                            </label>
                          </div>
                        </div>
                      </div>
                      <div className="mt-4 rounded-[24px] border border-white/8 bg-black/10 p-4">
                        <label className="flex items-center justify-between gap-3 rounded-[20px] border border-white/8 bg-black/10 px-4 py-3">
                          <div>
                            <div className="font-medium text-white">Comment affiliate sau khi đăng</div>
                            <div className="mt-1 text-sm text-[var(--text-soft)]">Tự comment link aff vào bài đăng mới của fanpage này.</div>
                          </div>
                          <input
                            type="checkbox"
                            checked={draft.affiliate_comment_enabled}
                            onChange={(event) => handleReplyAutomationDraftChange(pageItem.page_id, 'affiliate_comment_enabled', event.target.checked)}
                          />
                        </label>
                        <div className="mt-4 grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
                          <label className="space-y-2">
                            <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Delay sau khi đăng (giây)</span>
                            <input
                              type="number"
                              min="0"
                              max="3600"
                              className={FIELD_CLASS}
                              value={draft.affiliate_comment_delay_seconds}
                              onChange={(event) => handleReplyAutomationDraftChange(pageItem.page_id, 'affiliate_comment_delay_seconds', parseInt(event.target.value, 10) || 0)}
                              disabled={!draft.affiliate_comment_enabled}
                            />
                            <div className="text-sm text-[var(--text-soft)]">Khuyến nghị 60 giây để Facebook kịp tạo object comment.</div>
                          </label>
                          <label className="space-y-2">
                            <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Danh sách link affiliate</span>
                            <textarea
                              className={FIELD_CLASS}
                              value={draft.affiliate_link_url}
                              onChange={(event) => handleReplyAutomationDraftChange(pageItem.page_id, 'affiliate_link_url', event.target.value)}
                              placeholder={'https://link-aff-1\nhttps://link-aff-2'}
                              disabled={!draft.affiliate_comment_enabled}
                              rows={4}
                            />
                            <div className="text-sm text-[var(--text-soft)]">Mỗi link một dòng. Hệ thống sẽ random hoàn toàn 1 link cho mỗi video.</div>
                          </label>
                        </div>
                        <div className="mt-4 text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Danh sách nội dung comment affiliate</div>
                        <textarea
                          className={cx(FIELD_CLASS, 'mt-3 min-h-[140px] resize-y')}
                          value={draft.affiliate_comment_text}
                          onChange={(event) => handleReplyAutomationDraftChange(pageItem.page_id, 'affiliate_comment_text', event.target.value)}
                          placeholder={'Link sản phẩm mình để ở đây nhé.\nMình để link tham khảo ở dưới cho bạn nha.\nBạn xem link chi tiết giúp mình ở đây nhé.'}
                          disabled={!draft.affiliate_comment_enabled}
                        />
                        <div className="mt-3 text-sm text-[var(--text-soft)]">
                          Mỗi nội dung hoặc link nhập trên một dòng. Khi tới lượt comment, hệ thống sẽ random hoàn toàn 1 nội dung và 1 link, ghép lại rồi comment sau {draft.affiliate_comment_delay_seconds || 0} giây. Nếu fail sau retry, mục đó sẽ rơi sang `Comment aff cần operator xử lý`.
                        </div>
                      </div>
                    </>
                  ) : null}
                </article>
              );
            })}
          </div>
        )}
      </Panel>

      <Panel
        eyebrow="Hộp thư operator"
        title="Quản lý hội thoại theo conversation"
        action={(
          <div className="flex flex-wrap gap-2">
            {[
              { value: 'all', label: `Tất cả (${conversationList.length})` },
              { value: 'operator_active', label: `Cần operator (${handoffConversations.length})` },
              { value: 'ai_active', label: `AI đang xử lý (${conversationList.filter((conversation) => conversation.status === 'ai_active').length})` },
              { value: 'resolved', label: `Đã xử lý (${resolvedConversations.length})` },
            ].map((filterItem) => (
              <button
                key={filterItem.value}
                type="button"
                onClick={() => setConversationStatusFilter(filterItem.value)}
                className={cx(
                  BUTTON_GHOST,
                  conversationStatusFilter === filterItem.value ? 'border-cyan-400/20 bg-cyan-400/10 text-cyan-100' : '',
                )}
              >
                {filterItem.label}
              </button>
            ))}
          </div>
        )}
      >
        <div className="grid gap-5 2xl:grid-cols-[0.92fr_1.28fr]">
          <div className="space-y-4">
            {visibleConversations.length === 0 ? (
              <EmptyState title="Chưa có conversation phù hợp" description="Tin nhắn inbox sẽ được gom theo conversation và hiện tại đây." />
            ) : (
              visibleConversations.map((conversation) => {
                const targetPage = fbPages.find((pageItem) => pageItem.page_id === conversation.page_id);
                const statusMeta = getConversationStatusMeta(conversation.status);
                const isSelected = selectedConversationId === conversation.id;
                return (
                  <button
                    key={conversation.id}
                    type="button"
                    onClick={() => setSelectedConversationId(conversation.id)}
                    className={cx(
                      'w-full rounded-[22px] border p-4 text-left transition',
                      isSelected
                        ? 'border-cyan-400/25 bg-cyan-400/10'
                        : 'border-white/8 bg-black/10 hover:border-white/15 hover:bg-black/15',
                    )}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="font-medium text-white">{targetPage?.page_name || conversation.page_id}</div>
                        <div className="mt-1 text-xs text-[var(--text-muted)]">Người gửi: {conversation.sender_id}</div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <StatusPill tone={statusMeta.tone}>{statusMeta.label}</StatusPill>
                        {conversation.current_intent ? <StatusPill tone="amber">{formatIntentLabel(conversation.current_intent)}</StatusPill> : null}
                      </div>
                    </div>
                    <div className="mt-3 text-sm leading-6 text-[var(--text-soft)]">
                      {summarizeText(conversation.latest_preview, 'Chưa có nội dung.')}
                    </div>
                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <InfoRow label="Lượt chat" value={conversation.message_count ?? 0} />
                      <InfoRow label="Cập nhật cuối" value={formatDateTime(conversation.latest_activity_at)} />
                      <InfoRow label="Người xử lý" value={conversation.assigned_user?.display_name || 'Chưa gán'} />
                      <InfoRow label="Nguồn preview" value={conversation.latest_preview_direction === 'page' ? 'Trang' : 'Khách'} />
                    </div>
                  </button>
                );
              })
            )}
          </div>

          <div>
            {!selectedConversation ? (
              <EmptyState title="Chọn một cuộc trò chuyện" description="Danh sách bên trái đã được gom theo conversation để operator xử lý gọn hơn." />
            ) : (
              <div className="space-y-4">
                <div ref={manualReplyPanelRef} className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="font-display text-xl font-semibold text-white">
                        {fbPages.find((pageItem) => pageItem.page_id === selectedConversation.page_id)?.page_name || selectedConversation.page_id}
                      </div>
                      <div className="mt-1 text-sm text-[var(--text-muted)]">Người gửi: {selectedConversation.sender_id}</div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <StatusPill tone={selectedConversationStatusMeta.tone}>{selectedConversationStatusMeta.label}</StatusPill>
                        {selectedConversation.current_intent ? <StatusPill tone="amber">{formatIntentLabel(selectedConversation.current_intent)}</StatusPill> : null}
                        {selectedConversation.assigned_user ? <StatusPill tone="slate">Người xử lý: {selectedConversation.assigned_user.display_name}</StatusPill> : null}
                      </div>
                    </div>
                    <div className="mobile-action-stack">
                      {selectedConversation.facebook_thread_url ? (
                        <a href={selectedConversation.facebook_thread_url} target="_blank" rel="noreferrer" className={BUTTON_GHOST}>
                          <ExternalLink className="h-4 w-4" />
                          Mở trên Facebook
                        </a>
                      ) : null}
                      {selectedConversation.status === 'operator_active' ? (
                        <>
                          <button
                            type="button"
                            className={BUTTON_SECONDARY}
                            onClick={() => handleConversationStatusChange(selectedConversation.id, 'resolved')}
                            disabled={actionState[`conversation-status-resolved-${selectedConversation.id}`]}
                          >
                            <CircleCheck className="h-4 w-4" />
                            {actionState[`conversation-status-resolved-${selectedConversation.id}`] ? 'Đang cập nhật...' : 'Đánh dấu đã xử lý'}
                          </button>
                          <button
                            type="button"
                            className={BUTTON_GHOST}
                            onClick={() => handleConversationStatusChange(selectedConversation.id, 'ai_active')}
                            disabled={actionState[`conversation-status-ai_active-${selectedConversation.id}`]}
                          >
                            <RefreshCw className="h-4 w-4" />
                            {actionState[`conversation-status-ai_active-${selectedConversation.id}`] ? 'Đang cập nhật...' : 'Bật lại AI'}
                          </button>
                        </>
                      ) : selectedConversation.status === 'resolved' ? (
                        <>
                          <button
                            type="button"
                            className={cx(BUTTON_GHOST, 'border-rose-400/20 bg-rose-400/10 text-rose-100 hover:border-rose-300/30 hover:bg-rose-400/15')}
                            onClick={() => handleConversationStatusChange(selectedConversation.id, 'operator_active', 'Đã mở lại để operator hỗ trợ tiếp.')}
                            disabled={actionState[`conversation-status-operator_active-${selectedConversation.id}`]}
                          >
                            <AlertTriangle className="h-4 w-4" />
                            {actionState[`conversation-status-operator_active-${selectedConversation.id}`] ? 'Đang cập nhật...' : 'Mở lại cho operator'}
                          </button>
                          <button
                            type="button"
                            className={BUTTON_GHOST}
                            onClick={() => handleConversationStatusChange(selectedConversation.id, 'ai_active')}
                            disabled={actionState[`conversation-status-ai_active-${selectedConversation.id}`]}
                          >
                            <RefreshCw className="h-4 w-4" />
                            {actionState[`conversation-status-ai_active-${selectedConversation.id}`] ? 'Đang cập nhật...' : 'Bật lại AI'}
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          className={cx(BUTTON_GHOST, 'border-rose-400/20 bg-rose-400/10 text-rose-100 hover:border-rose-300/30 hover:bg-rose-400/15')}
                          onClick={() => handleConversationStatusChange(selectedConversation.id, 'operator_active', 'Đã chuyển cho nhân viên tư vấn hỗ trợ tiếp.')}
                          disabled={actionState[`conversation-status-operator_active-${selectedConversation.id}`]}
                        >
                          <AlertTriangle className="h-4 w-4" />
                          {actionState[`conversation-status-operator_active-${selectedConversation.id}`] ? 'Đang cập nhật...' : 'Chuyển operator'}
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <InfoRow label="Tin khách cuối" value={formatDateTime(selectedConversation.last_customer_message_at)} />
                    <InfoRow label="AI phản hồi cuối" value={formatDateTime(selectedConversation.last_ai_reply_at)} />
                    <InfoRow label="Operator phản hồi cuối" value={formatDateTime(selectedConversation.last_operator_reply_at)} />
                    <InfoRow label="Đóng case lúc" value={formatDateTime(selectedConversation.resolved_at)} />
                  </div>
                </div>

                <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
                  <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Memory hội thoại</div>
                      {selectedConversation.status === 'operator_active' ? <StatusPill tone="rose" icon={AlertTriangle}>Đang cần người thật</StatusPill> : null}
                    </div>
                    <div className="mt-3 text-sm leading-7 text-white">{selectedConversation.conversation_summary || 'Chưa có tóm tắt hội thoại.'}</div>
                    {selectedConversation.handoff_reason ? (
                      <div className="mt-4 rounded-[20px] border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm leading-7 text-rose-100">
                        {selectedConversation.handoff_reason}
                      </div>
                    ) : null}
                  </div>
                  <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                    <div className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Intent và dữ kiện nhớ</div>
                    <div className="mt-3 space-y-3">
                      <InfoRow label="Intent hiện tại" value={formatIntentLabel(selectedConversation.current_intent)} emphasis />
                      <InfoRow label="Người xử lý" value={selectedConversation.assigned_user?.display_name || 'Chưa gán'} />
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {getConversationFactEntries(selectedConversation).length > 0
                        ? getConversationFactEntries(selectedConversation).map(([key, value]) => (
                          <StatusPill key={`${selectedConversation.id}-${key}`} tone="slate">{`${formatIntentLabel(key)}: ${value}`}</StatusPill>
                        ))
                        : <StatusPill tone="slate">Chưa có facts</StatusPill>}
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
                  <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                    <div className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Điều phối operator</div>
                    <div className="mt-4 space-y-4">
                      {isAdmin ? (
                        <label className="block space-y-2">
                          <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Giao cho</span>
                          <select className={FIELD_CLASS} value={conversationAssigneeDraft} onChange={(event) => setConversationAssigneeDraft(event.target.value)}>
                            <option value="">Chưa gán người xử lý</option>
                            {assignableUsers.map((user) => (
                              <option key={user.id} value={user.id}>
                                {(user.display_name || user.username)} • {user.role}
                              </option>
                            ))}
                          </select>
                        </label>
                      ) : (
                        <button type="button" className={BUTTON_GHOST} onClick={() => setConversationAssigneeDraft(currentUser?.id || '')}>
                          <UserPlus className="h-4 w-4" />
                          Nhận xử lý cho mình
                        </button>
                      )}
                      <label className="block space-y-2">
                        <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Ghi chú nội bộ</span>
                        <textarea
                          className={cx(FIELD_CLASS, 'min-h-[140px] resize-y')}
                          value={conversationNoteDraft}
                          onChange={(event) => setConversationNoteDraft(event.target.value)}
                          placeholder="Ghi chú nội bộ cho operator, không gửi cho khách."
                        />
                      </label>
                      <button
                        type="button"
                        className={BUTTON_SECONDARY}
                        onClick={handleConversationMetaSave}
                        disabled={actionState[`conversation-meta-${selectedConversation.id}`]}
                      >
                        <CircleCheck className="h-4 w-4" />
                        {actionState[`conversation-meta-${selectedConversation.id}`] ? 'Đang lưu...' : 'Lưu phân công và ghi chú'}
                      </button>
                    </div>
                  </div>

                  <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Timeline cuộc trò chuyện</div>
                      <StatusPill tone="slate">{selectedConversationLogs.length} bản ghi</StatusPill>
                    </div>
                    {selectedConversationTimeline.length === 0 ? (
                      <div className="mt-4">
                        <EmptyState title="Chưa có timeline" description="Lịch sử chat sẽ hiện ở đây khi có tin nhắn hoặc phản hồi." />
                      </div>
                    ) : (
                      <div className="mt-4 space-y-3">
                        {selectedConversationTimeline.map((event) => (
                          <div
                            key={event.id}
                            className={cx(
                              'rounded-[22px] border px-4 py-3',
                              event.type === 'customer'
                                ? 'border-white/8 bg-black/10'
                                : event.type === 'operator'
                                  ? 'border-amber-400/20 bg-amber-400/10'
                                  : 'border-cyan-400/20 bg-cyan-400/10',
                            )}
                          >
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <div className="font-medium text-white">{event.sourceLabel}</div>
                              <StatusPill tone="slate" icon={Clock}>{formatDateTime(event.time)}</StatusPill>
                            </div>
                            <div className="mt-3 whitespace-pre-wrap text-sm leading-7 text-white">{event.text}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                <div className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Phản hồi thủ công</div>
                      <div className="mt-2 text-sm text-[var(--text-soft)]">
                        {selectedConversation.status === 'ai_active'
                          ? 'AI đang xử lý cuộc chat này. Nếu cần can thiệp tay, hãy chuyển operator trước.'
                          : 'Nhập nội dung để operator phản hồi trực tiếp từ dashboard.'}
                      </div>
                    </div>
                    {selectedConversation.status !== 'ai_active' ? <StatusPill tone="rose">AI đang tạm dừng cho case này</StatusPill> : null}
                  </div>
                  <div className="mt-4 space-y-4">
                    <textarea
                      ref={manualReplyInputRef}
                      className={cx(FIELD_CLASS, 'min-h-[140px] resize-y')}
                      value={manualReplyDraft}
                      onChange={(event) => setManualReplyDraft(event.target.value)}
                      placeholder={selectedConversation.status === 'ai_active' ? 'Chuyển operator để phản hồi tay.' : 'Nhập phản hồi gửi cho khách hàng.'}
                      disabled={selectedConversation.status === 'ai_active'}
                    />
                    <div className="mobile-action-stack">
                      <button
                        type="button"
                        className={BUTTON_PRIMARY}
                        onClick={() => handleManualReply(false)}
                        disabled={selectedConversation.status === 'ai_active' || actionState[`conversation-reply-${selectedConversation.id}`]}
                      >
                        <MessagesSquare className="h-4 w-4" />
                        {actionState[`conversation-reply-${selectedConversation.id}`] ? 'Đang gửi...' : 'Gửi phản hồi'}
                      </button>
                      <button
                        type="button"
                        className={BUTTON_SECONDARY}
                        onClick={() => handleManualReply(true)}
                        disabled={selectedConversation.status === 'ai_active' || actionState[`conversation-reply-${selectedConversation.id}`]}
                      >
                        <CircleCheck className="h-4 w-4" />
                        {actionState[`conversation-reply-${selectedConversation.id}`] ? 'Đang gửi...' : 'Gửi và đánh dấu đã xử lý'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </Panel>

    </div>
  );

  const renderOperationsSection = () => (
    <div className="grid gap-6 2xl:grid-cols-12">
      <Panel className="2xl:col-span-4" eyebrow="Health" title="Sức khỏe hệ thống">
        <div className="space-y-3">
          <InfoRow label="Database" value={healthInfo?.database?.ok ? 'Kết nối ổn' : 'Có lỗi'} emphasis />
          <InfoRow label="Worker trực tuyến" value={onlineWorkers} />
          <InfoRow label="Worker stale" value={staleWorkers.length} />
          <InfoRow label="Task queue poll" value={`${healthInfo?.config?.task_queue_poll_seconds ?? 0} giây`} />
          <InfoRow label="Xác minh chữ ký webhook" value={healthInfo?.config?.webhook_signature_enabled ? 'Đang bật' : 'Chưa bật'} />
          <InfoRow label="Chế độ nền" value={healthInfo?.worker?.expected_mode || 'Chưa có'} />
        </div>
      </Panel>

      <Panel className="2xl:col-span-4" eyebrow="Worker" title="Theo dõi tiến trình nền" action={isAdmin ? <button type="button" className={BUTTON_GHOST} onClick={handleCleanupWorkers} disabled={actionState['cleanup-workers'] || staleWorkers.length === 0}><Trash2 className="h-4 w-4" />{actionState['cleanup-workers'] ? 'Đang dọn...' : 'Dọn worker cũ'}</button> : null}>
        <div className="space-y-3">
          {workers.length === 0 ? (
            <EmptyState title="Chưa ghi nhận worker" description="Worker sẽ hiện tại đây." />
          ) : (
            workers.map((worker) => (
              <div key={worker.worker_name} className="rounded-[24px] border border-white/8 bg-black/10 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-medium text-white">{worker.worker_name}</div>
                    <div className="mt-1 text-xs text-[var(--text-muted)]">{worker.hostname || 'Không có hostname'}</div>
                  </div>
                  <span className={cx('inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium', getStatusClasses(worker.is_online ? 'posted' : 'failed'))}>
                    <StatusIcon status={worker.is_online ? 'posted' : 'failed'} />
                    {worker.is_online ? 'Trực tuyến' : 'Mất kết nối'}
                  </span>
                </div>
                <div className="mt-4 grid gap-3">
                  <InfoRow label="Trạng thái" value={worker.status} />
                  <InfoRow label="Lần cuối heartbeat" value={formatDateTime(worker.last_seen_at)} />
                  {worker.current_task_type ? <InfoRow label="Đang làm" value={worker.current_task_type} /> : null}
                </div>
              </div>
            ))
          )}
        </div>
      </Panel>

      <Panel className="2xl:col-span-4" eyebrow="Queue summary" title="Nhịp hàng đợi nền">
        <div className="grid gap-3 sm:grid-cols-2">
          <InfoRow label="Queued" value={taskSummary.queued ?? 0} emphasis />
          <InfoRow label="Processing" value={taskSummary.processing ?? 0} />
          <InfoRow label="Completed" value={taskSummary.completed ?? 0} />
          <InfoRow label="Failed" value={taskSummary.failed ?? 0} />
        </div>
      </Panel>

      <Panel className="2xl:col-span-6" eyebrow="Task queue" title="Tác vụ gần nhất" action={<div className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-3 text-sm text-[var(--text-soft)]">Trang {taskPage} / {totalTaskPages}</div>}>
        <div className="space-y-3">
          {tasks.length === 0 ? <EmptyState title="Chưa có tác vụ nền" description="Tác vụ sẽ hiện tại đây." /> : pagedTasks.map((task) => (
            <div key={task.id} className="rounded-[24px] border border-white/8 bg-black/10 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-medium text-white">{task.task_type}</div>
                  <div className="mt-1 text-xs text-[var(--text-muted)]">{task.entity_type || 'khác'}: {task.entity_id || 'n/a'}</div>
                </div>
                <span className={cx('inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium', getStatusClasses(task.status))}>
                  <StatusIcon status={task.status} />
                  {getStatusLabel(task.status)}
                </span>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <InfoRow label="Số lần chạy" value={`${task.attempts}/${task.max_attempts}`} />
                <InfoRow label="Ưu tiên" value={task.priority} />
                <InfoRow label="Tạo lúc" value={formatDateTime(task.created_at)} />
                <InfoRow label="Worker nhận" value={task.locked_by || 'Chưa nhận'} />
              </div>
              {task.last_error ? <div className="mt-4 rounded-[20px] border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm leading-7 text-rose-100">{task.last_error}</div> : null}
            </div>
          ))}
        </div>
        {tasks.length > TASK_PAGE_SIZE ? (
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-white/8 pt-5">
            <div className="text-sm text-[var(--text-soft)]">
              Hiển thị {pagedTasks.length} / {tasks.length} tác vụ gần nhất.
            </div>
            <div className="flex gap-2">
              <button type="button" disabled={taskPage <= 1} onClick={() => setTaskPage((current) => Math.max(1, current - 1))} className={BUTTON_GHOST}>
                Trước
              </button>
              <button type="button" disabled={taskPage >= totalTaskPages} onClick={() => setTaskPage((current) => Math.min(totalTaskPages, current + 1))} className={BUTTON_GHOST}>
                Sau
              </button>
            </div>
          </div>
        ) : null}
      </Panel>

      <Panel className="2xl:col-span-6" eyebrow="System events" title="Nhật ký hệ thống" action={<div className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-3 text-sm text-[var(--text-soft)]">Trang {eventPage} / {totalEventPages}</div>}>
        <div className="space-y-3">
          {events.length === 0 ? <EmptyState title="Chưa có sự kiện" description="Sự kiện sẽ hiện tại đây." /> : pagedEvents.map((event) => (
            <div key={event.id} className="rounded-[24px] border border-white/8 bg-black/10 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-medium text-white">{event.message}</div>
                  <div className="mt-1 text-xs text-[var(--text-muted)]">{event.scope} • {event.level}</div>
                </div>
                <StatusPill tone={event.level === 'ERROR' ? 'rose' : event.level === 'WARNING' ? 'amber' : 'emerald'}>{event.level}</StatusPill>
              </div>
              <div className="mt-3 text-sm text-[var(--text-soft)]">{formatDateTime(event.created_at)}</div>
              {event.details && Object.keys(event.details).length > 0 ? <pre className="mt-4 overflow-x-auto rounded-[20px] border border-white/8 bg-black/20 px-4 py-3 text-xs text-[var(--text-soft)]">{JSON.stringify(event.details, null, 2)}</pre> : null}
            </div>
          ))}
        </div>
        {events.length > SYSTEM_EVENT_PAGE_SIZE ? (
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-white/8 pt-5">
            <div className="text-sm text-[var(--text-soft)]">
              Hiển thị {pagedEvents.length} / {events.length} sự kiện gần nhất.
            </div>
            <div className="flex gap-2">
              <button type="button" disabled={eventPage <= 1} onClick={() => setEventPage((current) => Math.max(1, current - 1))} className={BUTTON_GHOST}>
                Trước
              </button>
              <button type="button" disabled={eventPage >= totalEventPages} onClick={() => setEventPage((current) => Math.min(totalEventPages, current + 1))} className={BUTTON_GHOST}>
                Sau
              </button>
            </div>
          </div>
        ) : null}
      </Panel>
    </div>
  );

  const renderSecuritySection = () => (
    <div className="grid gap-6 2xl:grid-cols-12">
      <Panel className="2xl:col-span-4" eyebrow="Phiên hiện tại" title="Tài khoản đang dùng">
        <div className="space-y-3">
          <InfoRow label="Tên đăng nhập" value={currentUser?.username || 'Chưa có'} emphasis />
          <InfoRow label="Tên hiển thị" value={currentUser?.display_name || 'Chưa đặt'} />
          <InfoRow label="Vai trò" value={currentUser?.role === 'admin' ? 'Quản trị viên' : 'Vận hành'} />
          <InfoRow label="Hết hạn phiên" value={formatDateTime(sessionExpiresAt)} />
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          <StatusPill tone={currentUser?.must_change_password ? 'amber' : 'emerald'} icon={ShieldCheck}>{currentUser?.must_change_password ? 'Cần đổi mật khẩu' : 'Đã an toàn'}</StatusPill>
          <button type="button" className={BUTTON_GHOST} onClick={handleLogout}><LogOut className="h-4 w-4" />Đăng xuất</button>
        </div>
      </Panel>

      <Panel className="2xl:col-span-4" eyebrow="Đổi mật khẩu" title="Cập nhật thông tin đăng nhập">
        <form onSubmit={handleChangePassword} className="space-y-4">
          <label className="block space-y-2">
            <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Mật khẩu hiện tại</span>
            <input type="password" required className={FIELD_CLASS} value={passwordForm.current_password} onChange={(event) => setPasswordForm((current) => ({ ...current, current_password: event.target.value }))} />
          </label>
          <label className="block space-y-2">
            <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Mật khẩu mới</span>
            <input type="password" required className={FIELD_CLASS} value={passwordForm.new_password} onChange={(event) => setPasswordForm((current) => ({ ...current, new_password: event.target.value }))} />
          </label>
          <button type="submit" disabled={actionState['change-password']} className={cx(BUTTON_PRIMARY, 'w-full')}>
            <ShieldCheck className="h-4 w-4" />
            {actionState['change-password'] ? 'Đang cập nhật...' : 'Đổi mật khẩu'}
          </button>
        </form>
      </Panel>

      <Panel className="2xl:col-span-4" eyebrow="Quy tắc" title="Nhắc nhở bảo mật">
        <div className="space-y-3">
          <div className="rounded-[24px] border border-white/8 bg-black/10 px-4 py-4 text-sm leading-7 text-[var(--text-soft)]">Đổi mật khẩu mặc định sau lần vào đầu.</div>
          <div className="rounded-[24px] border border-white/8 bg-black/10 px-4 py-4 text-sm leading-7 text-[var(--text-soft)]">Chỉ admin được quản lý tài khoản.</div>
          <div className="rounded-[24px] border border-white/8 bg-black/10 px-4 py-4 text-sm leading-7 text-[var(--text-soft)]">Reset sẽ tạo mật khẩu tạm.</div>
        </div>
      </Panel>

      <Panel className="2xl:col-span-12" eyebrow="Quản lý người dùng" title="Tài khoản vận hành trong hệ thống">
        {!isAdmin ? (
          <EmptyState title="Tài khoản hiện tại không có quyền quản trị" description="Cần quyền quản trị." />
        ) : (
          <div className="space-y-5">
            <form onSubmit={handleCreateUser} className="grid gap-4 lg:grid-cols-4">
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Tên đăng nhập</span>
                <input type="text" required className={FIELD_CLASS} value={userForm.username} onChange={(event) => setUserForm((current) => ({ ...current, username: event.target.value }))} />
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Tên hiển thị</span>
                <input type="text" className={FIELD_CLASS} value={userForm.display_name} onChange={(event) => setUserForm((current) => ({ ...current, display_name: event.target.value }))} />
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Mật khẩu ban đầu</span>
                <input type="password" required className={FIELD_CLASS} value={userForm.password} onChange={(event) => setUserForm((current) => ({ ...current, password: event.target.value }))} />
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.24em] text-[var(--text-muted)]">Vai trò</span>
                <select className={FIELD_CLASS} value={userForm.role} onChange={(event) => setUserForm((current) => ({ ...current, role: event.target.value }))}>
                  <option value="operator" style={{ color: '#06101a' }}>Vận hành</option>
                  <option value="admin" style={{ color: '#06101a' }}>Quản trị viên</option>
                </select>
              </label>
              <div className="lg:col-span-4 flex justify-end">
                <button type="submit" disabled={actionState['create-user']} className={BUTTON_PRIMARY}>
                  <UserPlus className="h-4 w-4" />
                  {actionState['create-user'] ? 'Đang tạo...' : 'Tạo tài khoản mới'}
                </button>
              </div>
            </form>
            {users.length === 0 ? <EmptyState title="Chưa có thêm tài khoản" description="Tạo tài khoản để bắt đầu." /> : (
              <div className="grid gap-4 xl:grid-cols-2">
                {users.map((user) => (
                  <article key={user.id} className="rounded-[22px] border border-white/8 bg-black/10 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <div className="font-medium text-white">{user.display_name || user.username}</div>
                        <div className="mt-1 text-xs text-[var(--text-muted)]">@{user.username}</div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <StatusPill tone={user.role === 'admin' ? 'emerald' : 'sky'}>{user.role === 'admin' ? 'Quản trị viên' : 'Vận hành'}</StatusPill>
                          <StatusPill tone={user.is_active ? 'emerald' : 'rose'}>{user.is_active ? 'Đang hoạt động' : 'Đã khóa'}</StatusPill>
                          {user.must_change_password ? <StatusPill tone="amber">Buộc đổi mật khẩu</StatusPill> : null}
                        </div>
                      </div>
                      <div className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-3 text-right">
                        <div className="text-[10px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Lần đăng nhập gần nhất</div>
                        <div className="mt-2 text-sm text-white">{formatDateTime(user.last_login_at)}</div>
                      </div>
                    </div>
                    <div className="mt-5 grid gap-3 sm:grid-cols-2">
                      <select className={FIELD_CLASS} value={user.role} onChange={(event) => handleUserUpdate(user.id, { role: event.target.value })} disabled={actionState[`user-update-${user.id}`]}>
                        <option value="operator" style={{ color: '#06101a' }}>Vận hành</option>
                        <option value="admin" style={{ color: '#06101a' }}>Quản trị viên</option>
                      </select>
                      <button type="button" className={BUTTON_GHOST} onClick={() => handleUserUpdate(user.id, { is_active: !user.is_active })} disabled={actionState[`user-update-${user.id}`]}>
                        {user.is_active ? 'Khóa tài khoản' : 'Mở khóa tài khoản'}
                      </button>
                    </div>
                    <div className="mobile-action-stack mt-3">
                      <button type="button" className={BUTTON_SECONDARY} onClick={() => handleResetUserPassword(user.id)} disabled={actionState[`user-reset-${user.id}`]}>
                        <RefreshCw className="h-4 w-4" />
                        {actionState[`user-reset-${user.id}`] ? 'Đang đặt lại...' : 'Đặt lại mật khẩu'}
                      </button>
                      <button
                        type="button"
                        className={cx(BUTTON_GHOST, 'border-rose-400/20 bg-rose-400/10 text-rose-100 hover:border-rose-400/30 hover:bg-rose-400/15')}
                        onClick={() => handleDeleteUser(user.id, user.username)}
                        disabled={actionState[`user-delete-${user.id}`] || currentUser?.id === user.id}
                      >
                        <Trash2 className="h-4 w-4" />
                        {actionState[`user-delete-${user.id}`] ? 'Đang xóa...' : 'Xóa vĩnh viễn'}
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        )}
      </Panel>
    </div>
  );

  const renderActiveSection = () => {
    switch (activeSection) {
      case 'campaigns': return renderCampaignSection();
      case 'queue': return renderQueueSection();
      case 'engagement': return renderEngagementSection();
      case 'messages': return renderMessagesSection();
      case 'operations': return renderOperationsSection();
      case 'security': return renderSecuritySection();
      case 'overview':
      default: return renderOverviewSection();
    }
  };

  const renderMobileQuickPanel = () => (
    <Panel className="xl:hidden" eyebrow="Tóm tắt nhanh" title="Điểm cần nhìn ngay">
      <div className="space-y-4">
        <div className="grid gap-3">
          <InfoRow label="Đến lượt kế tiếp" value={formatRelTime(stats.next_publish)} emphasis />
          <InfoRow label="Cuối hàng chờ" value={formatDateTime(stats.queue_end)} />
          <InfoRow label="Worker trực tuyến" value={onlineWorkers} />
        </div>
        <div className="grid gap-3">
          <button type="button" onClick={() => handleSectionChange('campaigns')} className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-4 text-left transition hover:border-cyan-400/20 hover:bg-cyan-400/6">
            <div className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Chiến dịch</div>
            <div className="mt-2 font-medium text-white">
              {focusCampaigns.length ? `${focusCampaigns.length} chiến dịch cần xem ngay` : 'Không có chiến dịch nóng'}
            </div>
          </button>
          <button type="button" onClick={() => handleSectionChange('messages')} className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-4 text-left transition hover:border-cyan-400/20 hover:bg-cyan-400/6">
            <div className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Webhook fanpage</div>
            <div className="mt-2 font-medium text-white">{connectedMessagePages}/{fbPages.length || 0} trang đã nối đủ feed và messages</div>
          </button>
          <button type="button" onClick={() => handleSectionChange('operations')} className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-4 text-left transition hover:border-cyan-400/20 hover:bg-cyan-400/6">
            <div className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">Vận hành</div>
            <div className="mt-2 font-medium text-white">
              {staleWorkers.length ? `${staleWorkers.length} worker cần dọn` : 'Không có worker stale'}
            </div>
          </button>
        </div>
      </div>
    </Panel>
  );

  const metricCards = [
    { label: 'Chiến dịch đang chạy', value: stats.active_campaigns ?? 0, detail: `${stats.paused_campaigns ?? 0} chiến dịch đang tạm dừng`, icon: Share2, tone: 'emerald' },
    { label: 'Video sẵn sàng', value: stats.ready ?? 0, detail: stats.next_publish ? `Lượt gần nhất sẽ tới ${formatRelTime(stats.next_publish)}` : 'Chưa có video sẵn sàng đăng', icon: Clock, tone: 'amber' },
    { label: 'Fanpage kết nối', value: stats.connected_pages ?? 0, detail: invalidPages.length ? `${invalidPages.length} trang cần xem lại token` : 'Mọi fanpage đang ở trạng thái tốt', icon: Globe2, tone: invalidPages.length ? 'rose' : 'sky' },
    {
      label: 'Phản hồi chờ AI',
      value: systemInfo?.pending_replies ?? 0,
      detail: `${systemInfo?.pending_comment_replies ?? 0} comment • ${systemInfo?.pending_message_replies ?? 0} inbox`,
      icon: Bot,
      tone: 'sky',
    },
    {
      label: 'Nguồn TikTok',
      value: stats.by_source?.tiktok?.campaigns ?? 0,
      detail: `${stats.by_source?.tiktok?.ready ?? 0} video sẵn sàng`,
      icon: Share2,
      tone: 'sky',
    },
    {
      label: 'Nguồn Shorts',
      value: stats.by_source?.youtube?.campaigns ?? 0,
      detail: `${stats.by_source?.youtube?.ready ?? 0} video sẵn sàng`,
      icon: Play,
      tone: 'rose',
    },
    { label: 'Worker trực tuyến', value: onlineWorkers, detail: staleWorkers.length ? `${staleWorkers.length} worker stale cần dọn` : 'Không có worker mất kết nối', icon: Radio, tone: staleWorkers.length ? 'amber' : 'emerald' },
  ];
  const visibleMetricCards = showAllMetrics ? metricCards : metricCards.slice(0, 4);

  if (!token) {
    return <LoginScreen loginUser={loginUser} setLoginUser={setLoginUser} loginPass={loginPass} setLoginPass={setLoginPass} loginError={loginError} handleLogin={handleLogin} />;
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[var(--shell-bg)] text-white">
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.14),transparent_36%),radial-gradient(circle_at_bottom_right,rgba(245,158,11,0.10),transparent_26%)]" />
      </div>
      {isMobileNavOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button type="button" aria-label="Đóng menu" className="absolute inset-0 bg-[#010d24]/70 backdrop-blur-sm" onClick={() => setIsMobileNavOpen(false)} />
          <div className="mobile-sheet absolute inset-x-3 bottom-3 top-3 rounded-[30px] border border-white/10 bg-[rgba(2,28,68,0.96)] p-4 shadow-[0_24px_80px_rgba(0,9,24,0.52)]">
            <div className="flex items-center justify-between gap-3 border-b border-white/8 pb-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.28em] text-[var(--text-muted)]">Điều hướng</div>
                <div className="mt-1 font-display text-xl font-semibold text-white">Các khu vực làm việc</div>
              </div>
              <button type="button" className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-white" onClick={() => setIsMobileNavOpen(false)}>
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="mt-4 space-y-2 overflow-y-auto">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const count = {
                  overview: warningCount,
                  campaigns: campaigns.length,
                  queue: stats.ready ?? 0,
                  engagement: systemInfo?.pending_comment_replies ?? 0,
                  messages: systemInfo?.pending_message_replies ?? 0,
                  operations: taskSummary.failed ?? 0,
                  security: users.length || (currentUser ? 1 : 0),
                }[item.id];
                return (
                  <button key={item.id} type="button" onClick={() => handleSectionChange(item.id)} className={cx('sidebar-link w-full rounded-[24px] px-4 py-4 text-left transition-all', activeSection === item.id && 'sidebar-link-active')}>
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 rounded-2xl border border-white/8 bg-black/10 p-2.5"><Icon className="h-4 w-4" /></div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-medium text-white">{item.label}</span>
                          <span className="rounded-full border border-white/10 bg-black/10 px-2.5 py-1 text-[11px] text-[var(--text-muted)]">{count}</span>
                        </div>
                        <div className="mt-1 text-sm text-[var(--text-soft)]">{item.description}</div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
            <div className="mt-4 rounded-[24px] border border-white/8 bg-black/10 p-4">
              <div className="text-[11px] uppercase tracking-[0.28em] text-[var(--text-muted)]">Phiên hiện tại</div>
              <div className="mt-2 font-medium text-white">{currentUser?.display_name || currentUser?.username || 'Người dùng'}</div>
              <div className="mt-1 text-sm text-[var(--text-soft)]">{currentUser?.role === 'admin' ? 'Quản trị viên' : 'Vận hành'}</div>
              <button type="button" className={cx(BUTTON_GHOST, 'mt-4 w-full')} onClick={handleLogout}><LogOut className="h-4 w-4" />Đăng xuất</button>
            </div>
          </div>
        </div>
      ) : null}
      <div className="relative flex min-h-screen flex-col">
        <aside className="hidden border-r border-white/8 bg-black/15 px-4 py-5 backdrop-blur-2xl lg:fixed lg:inset-y-0 lg:left-0 lg:z-30 lg:flex lg:h-screen lg:w-[17rem] lg:flex-col lg:overflow-y-auto">
          <div className="panel-strong rounded-[30px] p-5">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-[22px] border border-cyan-400/20 bg-cyan-400/10 text-cyan-100"><Zap className="h-6 w-6" /></div>
              <div>
                <div className="text-[11px] uppercase tracking-[0.28em] text-[var(--text-muted)]">Social workbench</div>
                <div className="mt-1 font-display text-xl font-semibold text-white">Trạm điều phối</div>
              </div>
            </div>
          </div>
          <nav className="mt-6 space-y-2">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const count = {
                overview: warningCount,
                campaigns: campaigns.length,
                queue: stats.ready ?? 0,
                engagement: systemInfo?.pending_comment_replies ?? 0,
                messages: systemInfo?.pending_message_replies ?? 0,
                operations: taskSummary.failed ?? 0,
                security: users.length || (currentUser ? 1 : 0),
              }[item.id];
              return (
                <button key={item.id} type="button" onClick={() => handleSectionChange(item.id)} className={cx('sidebar-link w-full rounded-[24px] px-4 py-4 text-left transition-all', activeSection === item.id && 'sidebar-link-active')}>
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 rounded-2xl border border-white/8 bg-black/10 p-2.5"><Icon className="h-4 w-4" /></div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-medium text-white">{item.label}</span>
                        <span className="rounded-full border border-white/10 bg-black/10 px-2.5 py-1 text-[11px] text-[var(--text-muted)]">{count}</span>
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </nav>
          <div className="mt-auto rounded-[26px] border border-white/8 bg-black/10 p-4">
            <div className="text-[11px] uppercase tracking-[0.28em] text-[var(--text-muted)]">Phiên hiện tại</div>
            <div className="mt-3 font-medium text-white">{currentUser?.display_name || currentUser?.username || 'Người dùng'}</div>
            <div className="mt-1 text-sm text-[var(--text-soft)]">{currentUser?.role === 'admin' ? 'Quản trị viên' : 'Vận hành'}</div>
            <button type="button" className={cx(BUTTON_GHOST, 'mt-4 w-full')} onClick={handleLogout}><LogOut className="h-4 w-4" />Đăng xuất</button>
          </div>
        </aside>
        <div className="min-w-0 flex-1 lg:pl-[17rem]">
          <div className="mx-auto flex min-h-screen w-full max-w-[1720px] flex-col px-3 py-3 sm:px-4 sm:py-4 lg:px-5 xl:px-6">
            <Panel className="sticky top-0 z-20 overflow-hidden border-white/10 bg-[rgba(2,28,68,0.92)] backdrop-blur-xl">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div className="flex items-start gap-3">
                  <button type="button" className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-white lg:hidden" onClick={() => setIsMobileNavOpen(true)}>
                    <Menu className="h-5 w-5" />
                  </button>
                  <div className="min-w-0">
                    <StatusPill tone="sky" icon={Activity}>Dashboard vận hành</StatusPill>
                    <div className="mt-4 text-[11px] uppercase tracking-[0.32em] text-[var(--text-muted)]">{systemInfo?.project_name || 'Hệ thống tự động mạng xã hội'}</div>
                    <h1 className="mt-3 font-display text-[1.4rem] font-semibold text-white sm:text-[1.7rem] md:text-[2rem]">{currentSection.label}</h1>
                    <p className="mt-2 text-sm text-[var(--text-soft)] lg:hidden">{currentSection.description}</p>
                  </div>
                </div>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <button type="button" className={cx(BUTTON_GHOST, 'lg:hidden')} onClick={() => handleSectionChange('overview')}>
                    <Globe2 className="h-4 w-4" />
                    Tổng quan
                  </button>
                  <button type="button" className={BUTTON_SECONDARY} onClick={() => fetchDashboard()}><RefreshCw className={cx('h-4 w-4', isRefreshing ? 'animate-spin' : '')} />Làm mới</button>
                </div>
              </div>
              {notice ? <div className={cx('mt-5 rounded-[24px] border px-4 py-4 text-sm leading-7', notice.type === 'success' ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100' : 'border-rose-400/20 bg-rose-400/10 text-rose-100')}>{notice.message}</div> : null}
            </Panel>
            <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {visibleMetricCards.map((metric) => <MetricCard key={metric.label} {...metric} />)}
            </div>
            {metricCards.length > 4 ? (
              <div className="mt-3 flex justify-start">
                <DetailToggle expanded={showAllMetrics} onClick={() => setShowAllMetrics((current) => !current)} />
              </div>
            ) : null}
            <div className="mt-5">{renderMobileQuickPanel()}</div>
            <div className="mt-6 grid gap-5 2xl:grid-cols-[minmax(0,1fr)_19rem]">
              <div className="min-w-0 space-y-6">{renderActiveSection()}</div>
              <aside className="hidden space-y-5 2xl:sticky 2xl:top-5 2xl:block 2xl:h-fit">
                <Panel eyebrow="Nhịp nhanh" title="Bảng điều phối">
                  <div className="space-y-3">
                    <InfoRow label="Server time" value={formatDateTime(systemInfo?.server_time)} />
                    <InfoRow label="Lần làm mới cuối" value={formatDateTime(lastUpdatedAt)} />
                    <InfoRow label="Đến lượt kế tiếp" value={formatRelTime(stats.next_publish)} />
                    <InfoRow label="Cuối hàng chờ" value={formatDateTime(stats.queue_end)} />
                    <InfoRow label="Bài đăng gần nhất" value={formatDateTime(stats.last_posted)} />
                  </div>
                </Panel>
                <Panel eyebrow="Cần chú ý" title="Chiến dịch nổi bật">
                  <div className="space-y-3">
                    {focusCampaigns.length === 0 ? (
                      <div className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-4 text-sm leading-7 text-[var(--text-soft)]">
                        Chưa có chiến dịch cần chú ý.
                      </div>
                    ) : focusCampaigns.map((campaign) => (
                      <button key={campaign.id} type="button" onClick={() => handleSectionChange('campaigns')} className="w-full rounded-[22px] border border-white/8 bg-black/10 px-4 py-4 text-left transition hover:border-cyan-400/20 hover:bg-cyan-400/6">
                        <div className="font-medium text-white">{campaign.name}</div>
                        <div className="mt-2 text-sm text-[var(--text-soft)]">
                          {campaign.video_counts?.failed ?? 0} video failed • trạng thái sync {getSyncStateMeta(campaign.last_sync_status).label.toLowerCase()}
                        </div>
                      </button>
                    ))}
                  </div>
                </Panel>
                <Panel eyebrow="Fanpage" title="Kết nối nhanh">
                  <div className="space-y-3">
                    {fbPages.length === 0 ? <div className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-4 text-sm text-[var(--text-soft)]">Chưa cấu hình fanpage nào.</div> : fbPages.slice(0, 4).map((pageItem) => {
                      const validation = pageChecks[pageItem.page_id];
                      const tokenMeta = getPageTokenMeta(getResolvedPageTokenKind(pageItem, validation));
                      const messengerMeta = getMessengerConnectionMeta(validation);
                      return (
                        <div key={pageItem.page_id} className="rounded-[22px] border border-white/8 bg-black/10 px-4 py-4">
                          <div className="font-medium text-white">{pageItem.page_name}</div>
                          <div className="mt-2 flex flex-wrap gap-2">
                            <StatusPill tone={tokenMeta.tone}>{tokenMeta.label}</StatusPill>
                            <StatusPill tone={messengerMeta.tone}>{messengerMeta.label}</StatusPill>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Panel>
              </aside>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
