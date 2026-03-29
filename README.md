# Social Tool

Hệ thống tự động lấy nội dung từ TikTok, sinh caption bằng AI, xếp lịch và đăng lên Facebook Page, kèm dashboard quản trị để theo dõi chiến dịch, hàng chờ, worker, webhook và cấu hình runtime.

## Tổng quan

- `backend`: FastAPI API cho auth, campaign, Facebook, webhook, health và runtime config
- `worker`: tiến trình nền riêng để chạy task queue, lịch đăng và xử lý reply comment
- `frontend`: dashboard React/Vite/Tailwind cho vận hành hằng ngày
- `db`: PostgreSQL lưu chiến dịch, video, user, task queue, log và runtime settings
- `tunnel`: Cloudflare Tunnel, chỉ cần khi bạn muốn public webhook ra Internet

## Tính năng chính

- Crawl video TikTok bằng `yt-dlp`
- Sinh caption AI và chỉnh tay trước khi đăng
- Lập lịch đăng Facebook Reels theo campaign
- Retry video lỗi, ưu tiên video, pause/resume/delete campaign
- Task queue riêng cho sync campaign, retry video và reply comment
- Dashboard theo dõi worker, task, sự kiện hệ thống và bình luận gần nhất
- Quản lý user theo vai trò `admin` và `operator`
- Cấu hình runtime ngay trên dashboard thay vì sửa hard-code trong repo

## Runtime Config Trên Dashboard

Từ bản hiện tại, các giá trị sau có thể cấu hình trực tiếp trong dashboard admin:

- `BASE_URL`
- `FB_VERIFY_TOKEN`
- `FB_APP_SECRET`
- `GEMINI_API_KEY`
- `TUNNEL_TOKEN`

Hệ thống sẽ:

- lưu override trong database
- mã hóa secret khi lưu
- tự sinh file `backend/runtime.env`
- dùng lại các giá trị này cho webhook, overview/health và worker

Lưu ý:

- `BASE_URL`, `FB_VERIFY_TOKEN`, `FB_APP_SECRET`, `GEMINI_API_KEY` áp dụng ngay sau khi lưu
- `TUNNEL_TOKEN` cần restart service `tunnel` để Cloudflare đọc token mới
- `JWT_SECRET`, `TOKEN_ENCRYPTION_SECRET`, `DATABASE_URL` và bootstrap admin vẫn nên giữ ở cấu hình triển khai

## Chạy Nhanh Với Docker

### 1. Khởi động các service chính

```bash
docker compose up -d --build db backend worker frontend
```

### 2. Đăng nhập dashboard

- Dashboard: [http://localhost:5173](http://localhost:5173)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Tài khoản mặc định lần đầu:
  - username: `admin`
  - password: `admin123`

Sau lần đăng nhập đầu tiên, nên đổi mật khẩu ngay.

### 3. Cấu hình ngay trên trang

Vào dashboard, mở khu `Tổng quan` và điền:

- `BASE_URL`
- `FB_VERIFY_TOKEN`
- `FB_APP_SECRET`
- `GEMINI_API_KEY`
- `TUNNEL_TOKEN` nếu dùng Cloudflare Tunnel

### 4. Nếu dùng Cloudflare Tunnel

Sau khi lưu `TUNNEL_TOKEN` trên dashboard:

```bash
docker compose up -d --force-recreate tunnel
```

Nếu chưa cần public webhook, bạn có thể bỏ qua service `tunnel`.

## Cấu Hình Triển Khai

Các biến dưới đây vẫn là cấu hình triển khai, không nên chuyển hết lên UI:

| Biến | Vai trò |
|------|---------|
| `DATABASE_URL` | Kết nối PostgreSQL |
| `JWT_SECRET` | Ký và xác thực access token |
| `TOKEN_ENCRYPTION_SECRET` | Mã hóa secret lưu trong DB |
| `ADMIN_PASSWORD` | Bootstrap tài khoản admin lần đầu |
| `DEFAULT_ADMIN_USERNAME` | Username admin mặc định |
| `DEFAULT_ADMIN_DISPLAY_NAME` | Tên hiển thị admin mặc định |

## Luồng Hoạt Động

1. Tạo campaign từ dashboard
2. Worker đưa job sync vào hàng đợi
3. Video được crawl và xếp lịch
4. Caption có thể được AI sinh sẵn hoặc chỉnh tay
5. Worker đăng video khi đến lịch
6. Webhook Facebook nhận comment mới và đưa vào queue phản hồi
7. Dashboard hiển thị trạng thái task, worker và sự kiện gần nhất

## Cấu Trúc Thư Mục

```text
.
├── backend/              # API, worker, alembic, services
├── frontend/             # Dashboard React/Vite
├── database/             # Dữ liệu PostgreSQL local
├── videos_storage/       # Video tải tạm
├── docker-compose.yml    # Toàn bộ stack local
└── README.md
```

## Ghi Chú Vận Hành

- `backend` và `worker` tự chạy Alembic khi container khởi động
- `backend/runtime.env` được sinh ra để cấp lại config cho container khi restart
- webhook Facebook cần `BASE_URL` là HTTPS public
- nếu worker stale, có thể dọn trực tiếp từ dashboard
- nếu đổi `TUNNEL_TOKEN`, nhớ recreate service `tunnel`

## Kiểm Tra Chất Lượng

Các lệnh đang dùng trong repo:

```bash
# backend
python -m compileall app alembic
python -m pytest -q

# frontend
npm run lint
npm run build
```

## Contributing

Có thể mở issue hoặc pull request nếu bạn muốn mở rộng tính năng hay cải thiện luồng vận hành.
