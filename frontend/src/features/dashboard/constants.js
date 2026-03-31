import { Bot, Clock, Globe2, MessagesSquare, Server, Share2, ShieldCheck } from 'lucide-react';

export const API_URL = '/api';
export const AUTO_REFRESH_MS = 5000;
export const TASK_PAGE_SIZE = 3;
export const TASK_FETCH_LIMIT = 24;
export const SYSTEM_EVENT_PAGE_SIZE = 3;
export const SYSTEM_EVENT_FETCH_LIMIT = 24;
export const FIELD_CLASS = 'field-input w-full rounded-2xl px-4 py-3 text-sm text-white';
export const BUTTON_DISABLED = 'disabled:cursor-not-allowed disabled:opacity-50';
export const BUTTON_PRIMARY = `btn-primary inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold ${BUTTON_DISABLED}`;
export const BUTTON_SECONDARY = `btn-secondary inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-medium ${BUTTON_DISABLED}`;
export const BUTTON_GHOST = `btn-ghost inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-medium ${BUTTON_DISABLED}`;

export const DEFAULT_STATS = {
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

export const DEFAULT_TASK_SUMMARY = { queued: 0, processing: 0, completed: 0, failed: 0 };
export const DEFAULT_RUNTIME_FORM = {
  BASE_URL: '',
  FB_VERIFY_TOKEN: '',
  FB_APP_SECRET: '',
  GEMINI_API_KEY: '',
  TUNNEL_TOKEN: '',
};

export const STATUS_FILTERS = [
  { value: 'all', label: 'Tất cả trạng thái' },
  { value: 'pending', label: 'Đang xử lý' },
  { value: 'ready', label: 'Sẵn sàng đăng' },
  { value: 'posted', label: 'Đã đăng' },
  { value: 'failed', label: 'Thất bại' },
];

export const SOURCE_PLATFORM_FILTERS = [
  { value: 'all', label: 'Tất cả nguồn' },
  { value: 'tiktok', label: 'TikTok' },
  { value: 'youtube', label: 'YouTube Shorts' },
];

export const NAV_ITEMS = [
  { id: 'overview', label: 'Tổng quan', description: 'Chỉ số và cảnh báo.', icon: Globe2 },
  { id: 'campaigns', label: 'Chiến dịch', description: 'Nguồn, trang và chiến dịch.', icon: Share2 },
  { id: 'queue', label: 'Lịch đăng', description: 'Video, lịch và caption.', icon: Clock },
  { id: 'engagement', label: 'Tương tác', description: 'Bình luận và phản hồi AI.', icon: Bot },
  { id: 'messages', label: 'Tin nhắn AI', description: 'Prompt và inbox tự động.', icon: MessagesSquare },
  { id: 'operations', label: 'Vận hành', description: 'Worker, queue và log.', icon: Server },
  { id: 'security', label: 'Bảo mật', description: 'Phiên, mật khẩu, người dùng.', icon: ShieldCheck },
];

export const STATUS_LABELS = {
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
  page_access_token: 'Token trang',
  user_access_token: 'Token người dùng',
  invalid_token: 'Token không hợp lệ',
  network_error: 'Lỗi kết nối',
  legacy_webhook: 'Webhook cũ',
  invalid_encryption: 'Lỗi giải mã',
  missing: 'Chưa có',
};

export const TONE_CLASSES = {
  slate: 'border-white/10 bg-white/5 text-slate-200',
  sky: 'border-cyan-400/20 bg-cyan-400/10 text-cyan-100',
  emerald: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100',
  amber: 'border-amber-400/20 bg-amber-400/10 text-amber-100',
  rose: 'border-rose-400/20 bg-rose-400/10 text-rose-100',
};

export const PAGE_TOKEN_META = {
  page_access_token: { label: 'Token trang hợp lệ', tone: 'emerald' },
  user_access_token: { label: 'Đang dùng user token', tone: 'rose' },
  invalid_token: { label: 'Token không hợp lệ', tone: 'rose' },
  network_error: { label: 'Chưa kiểm tra được token', tone: 'amber' },
  legacy_webhook: { label: 'Dữ liệu webhook cũ', tone: 'amber' },
  invalid_encryption: { label: 'Lỗi giải mã token', tone: 'rose' },
  missing: { label: 'Chưa có token', tone: 'slate' },
};

export const CONVERSATION_STATUS_META = {
  ai_active: { label: 'AI đang xử lý', tone: 'sky' },
  operator_active: { label: 'Cần operator', tone: 'rose' },
  resolved: { label: 'Đã xử lý', tone: 'emerald' },
};

export const SOURCE_PLATFORM_META = {
  tiktok: { label: 'TikTok', tone: 'sky' },
  youtube: { label: 'YouTube Shorts', tone: 'rose' },
  unknown: { label: 'Chưa rõ nguồn', tone: 'slate' },
};

export const SOURCE_KIND_LABELS = {
  tiktok_video: 'Video TikTok',
  tiktok_profile: 'Hồ sơ TikTok',
  tiktok_shortlink: 'Link TikTok rút gọn',
  tiktok_legacy: 'Nguồn TikTok cũ',
  youtube_short: 'YouTube Short',
  youtube_shorts_feed: 'Nguồn Shorts YouTube',
};

export const TREND_STATUS_META = {
  ready: { label: 'Sẵn sàng', color: '#67e8f9', textClass: 'text-cyan-100' },
  posted: { label: 'Đã đăng', color: '#34d399', textClass: 'text-emerald-100' },
  failed: { label: 'Thất bại', color: '#fb7185', textClass: 'text-rose-100' },
};
