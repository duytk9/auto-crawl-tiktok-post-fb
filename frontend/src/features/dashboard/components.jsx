import {
  ChevronDown,
  ChevronRight,
  ChevronUp,
  CircleCheck,
  CircleX,
  KeyRound,
  Radio,
  RefreshCw,
  Share2,
  ShieldCheck,
  Terminal,
  Zap,
} from 'lucide-react';

import {
  BUTTON_PRIMARY,
  FIELD_CLASS,
  TONE_CLASSES,
  TREND_STATUS_META,
} from './constants';
import { cx, formatTrendLabel } from './utils';

export function StatusIcon({ status, className = '' }) {
  if (['posted', 'completed', 'active', 'replied', 'page_access_token'].includes(status)) {
    return <CircleCheck className={cx('h-3.5 w-3.5', className)} />;
  }
  if (['failed', 'invalid_encryption', 'user_access_token', 'invalid_token'].includes(status)) {
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

export function StatusPill({ tone = 'slate', icon: Icon, children, className = '' }) {
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium',
        TONE_CLASSES[tone] || TONE_CLASSES.slate,
        className,
      )}
    >
      {Icon ? <Icon className="h-3.5 w-3.5" /> : null}
      <span>{children}</span>
    </span>
  );
}

export function MetricCard({ icon, label, value, detail, tone = 'slate' }) {
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

export function Panel({ eyebrow, title, subtitle, action, children, className = '' }) {
  return (
    <section className={cx('panel-surface rounded-[22px] p-3.5 sm:rounded-[24px] sm:p-4 lg:p-5', className)}>
      {(eyebrow || title || subtitle || action) && (
        <div className="mb-4 flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div>
            {eyebrow ? <div className="text-[11px] uppercase tracking-[0.28em] text-[var(--text-muted)]">{eyebrow}</div> : null}
            {title ? <h2 className="mt-2 font-display text-[1.15rem] font-semibold text-white sm:text-[1.25rem]">{title}</h2> : null}
            {subtitle ? <p className="mt-2 text-sm leading-6 text-[var(--text-soft)]">{subtitle}</p> : null}
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>
      )}
      {children}
    </section>
  );
}

export function InfoRow({ label, value, emphasis = false }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-[18px] border border-white/8 bg-black/10 px-4 py-3">
      <span className="text-sm text-[var(--text-soft)]">{label}</span>
      <span className={cx('text-sm text-white', emphasis && 'font-semibold')}>{value}</span>
    </div>
  );
}

export function SourceBreakdownBar({ label, value, max = 1, tone = 'slate', detail }) {
  const width = Math.max(6, Math.round((value / Math.max(max, 1)) * 100));
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-4 text-sm">
        <span className="text-white">{label}</span>
        <span className="text-[var(--text-soft)]">{detail}</span>
      </div>
      <div className="h-2 rounded-full bg-white/5">
        <div className={cx('h-2 rounded-full', TONE_CLASSES[tone] || TONE_CLASSES.slate)} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

export function TrendLegend() {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {Object.entries(TREND_STATUS_META).map(([key, meta]) => (
        <div key={key} className="inline-flex items-center gap-2 text-xs text-[var(--text-soft)]">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: meta.color }} />
          <span className={meta.textClass}>{meta.label}</span>
        </div>
      ))}
    </div>
  );
}

export function TrendTimelineChart({ labels, series }) {
  const width = 420;
  const height = 128;
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
              <polyline key={key} fill="none" stroke={meta.color} strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" points={pointString} />
            ) : null;
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

export function EmptyState({ title, description }) {
  return (
    <div className="rounded-[20px] border border-dashed border-white/10 bg-black/10 px-4 py-6 text-center sm:rounded-[22px] sm:px-5 sm:py-7">
      <div className="font-display text-base font-semibold text-white sm:text-lg">{title}</div>
      <p className="mx-auto mt-2 max-w-md text-[13px] leading-5 text-[var(--text-soft)]">{description}</p>
    </div>
  );
}

export function DetailToggle({ expanded, onClick, className = '' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        'inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] text-[var(--text-soft)] transition hover:border-white/18 hover:bg-white/8 hover:text-white',
        className,
      )}
    >
      {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      {expanded ? 'Thu gọn' : 'Xem thêm'}
    </button>
  );
}

export function LoginFeature({ icon, title, description }) {
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

export function LoginScreen({ loginUser, setLoginUser, loginPass, setLoginPass, loginError, handleLogin }) {
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
