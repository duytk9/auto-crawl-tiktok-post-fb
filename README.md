# Hệ Thống Tự Động Nội Dung Từ TikTok Sang Facebook

Hệ thống tự động lấy video từ TikTok, sinh chú thích bằng Gemini, xếp lịch và đăng lên trang Facebook, kèm bảng điều khiển quản trị để theo dõi hàng chờ, chiến dịch, trang Facebook, webhook bình luận và lỗi vận hành.

## Kiến trúc hiện tại

- `backend` chạy FastAPI API.
- `worker` chạy bộ lập lịch riêng để tránh trùng tác vụ khi mở rộng API.
- `frontend` là bảng điều khiển React/Vite.
- PostgreSQL lưu chiến dịch, video, trang Facebook và nhật ký tương tác.
- Hàng đợi `TaskQueue` chạy bằng worker riêng để xử lý đồng bộ chiến dịch, thử tải lại video và phản hồi bình luận.
- Alembic quản lý migration schema.

## 🛠 Tech Stack

- **Backend:** FastAPI, Python 3.10+
- **Worker:** Custom task queue polling system
- **Frontend:** React, Vite, Tailwind CSS
- **Database:** PostgreSQL
- **AI:** Google Gemini Pro API for caption generation and comment replies
- **Tools:** yt-dlp, Docker, Cloudflare Tunnel

## Tính năng chính

- Quét video TikTok bằng `yt-dlp`.
- Sinh và chỉnh sửa AI caption trước khi đăng.
- Tự động đăng Facebook Reels theo lịch.
- Hàng đợi tác vụ nền thật, có theo dõi trạng thái, số lần thử lại và worker đang nhận việc.
- Thử lại video lỗi, đẩy video lên đầu hàng chờ.
- Tạm dừng, kích hoạt lại, xóa và đồng bộ lại chiến dịch.
- Kiểm tra mã truy cập trang Facebook trực tiếp từ bảng điều khiển.
- Xác minh chữ ký webhook Facebook khi có `FB_APP_SECRET`.
- Mã hóa mã truy cập trang Facebook trước khi lưu DB.
- Đăng nhập theo người dùng thật, có vai trò quản trị/vận hành, đổi mật khẩu và đặt lại mật khẩu tạm.
- Dashboard hiển thị sức khỏe hệ thống, worker, hàng đợi và nhật ký sự kiện gần nhất.

## Chạy nhanh với Docker

1. Sao chép biến môi trường mẫu:

```bash
cp .env.example .env
```

2. Điền các giá trị quan trọng trong `.env` hoặc ngay trong `docker-compose.yml`:

```env
GEMINI_API_KEY=
ADMIN_PASSWORD=admin123
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_DISPLAY_NAME=Quản trị viên
BASE_URL=https://your-public-domain.example.com
JWT_SECRET=change-me
TOKEN_ENCRYPTION_SECRET=change-me
FB_VERIFY_TOKEN=change-me
FB_APP_SECRET=
TUNNEL_TOKEN=
TASK_QUEUE_POLL_SECONDS=5
WORKER_STALE_SECONDS=30
WORKER_BATCH_SIZE=3
```

3. Khởi động toàn bộ hệ thống:

```bash
docker compose up -d --build
```

## Truy cập

- Giao diện quản trị: `http://localhost:5173`
- Tài liệu API backend: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

## Lưu ý vận hành

- Đổi ngay `JWT_SECRET` và `TOKEN_ENCRYPTION_SECRET` trước khi dùng thật.
- `BASE_URL` phải là HTTPS public nếu muốn Facebook webhook hoạt động ổn định.
- `backend` mặc định không chạy bộ lập lịch nhúng nữa; tác vụ nền do service `worker` đảm nhiệm.
- Tài khoản mặc định ban đầu là `admin` với mật khẩu `admin123` nếu DB chưa có người dùng nào.
- Sau lần đăng nhập đầu tiên, nên đổi ngay mật khẩu tài khoản quản trị trong giao diện.
- Schema được cập nhật qua Alembic khi container backend/worker khởi động.

## Cấu trúc thư mục

```text
.
├── backend/            # FastAPI, Alembic, worker, services
├── frontend/           # React cho bảng điều khiển
├── database/           # dữ liệu PostgreSQL
├── videos_storage/     # video tải tạm trước khi đăng
├── .env.example        # biến môi trường mẫu
└── docker-compose.yml  # điều phối API + worker + frontend + db + tunnel
```

## 🤝 Contributing

Feel free to open issues or submit pull requests for any improvements.

## Give me a coffee!!

<img width="130" height="166" alt="image" src="https://github.com/user-attachments/assets/a3909d0a-b2ba-4dce-8064-2bc435beaa22" />
---

*Developed for automated social media management workflows.*
=======
>>>>>>> 6369e34 (Enhance social automation: AI comment replies, dashboard UI fix, and auth system)
