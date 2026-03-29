# Nâng Cấp Hỗ Trợ YouTube Shorts

## Goal
Thêm luồng cào video từ YouTube Shorts vào hệ thống hiện có mà không làm gãy flow TikTok, đồng thời giữ nguyên task queue, worker, lịch đăng và dashboard vận hành.

## Tasks

- [ ] Chuẩn hóa khái niệm `nguồn nội dung` trong dữ liệu campaign và video: thêm trường nhận diện platform/source type, cân nhắc lưu metadata như `tiktok`, `youtube_shorts`, `youtube_channel_shorts` → Verify: migration chạy được và campaign mới vẫn tạo thành công với nguồn TikTok cũ.
- [ ] Tạo service nhận diện URL nguồn và chuẩn hóa đầu vào: phân biệt được TikTok video/profile với YouTube Shorts URL, kênh Shorts hoặc playlist Shorts, đồng thời chặn video YouTube dài không phải Shorts nếu không nằm trong scope → Verify: có test cho từng loại URL và service trả về platform/source kind đúng.
- [ ] Refactor `ytdlp_crawler` thành crawler tổng quát dùng chung cho nhiều platform, trả về metadata chuẩn hóa `original_id`, `video_url`, `title`, `description`, `platform`, `published_at` → Verify: một interface duy nhất đọc được cả TikTok và YouTube Shorts, prefix file tải xuống không còn hard-code `tiktok`.
- [ ] Cập nhật `sync_campaign_content` để xử lý nguồn YouTube Shorts qua metadata chuẩn hóa thay vì giả định TikTok, đồng thời giữ nguyên cơ chế duplicate theo campaign và lịch đăng → Verify: sync TikTok cũ vẫn pass, sync YouTube Shorts tạo video mới đúng hàng chờ.
- [ ] Mở rộng dashboard tạo campaign: thêm selector hoặc auto-detect platform, hướng dẫn nhập URL cho YouTube Shorts, và hiển thị source platform trong thẻ campaign/video để người vận hành dễ theo dõi → Verify: tạo được campaign YouTube Shorts từ UI và nhìn thấy platform/source label rõ ràng.
- [ ] Bổ sung quan sát vận hành và guardrail: log platform trong system events, cảnh báo khi URL không phải Shorts, cảnh báo khi crawl trả về danh sách rỗng, và phân biệt lỗi tải metadata với lỗi tải file → Verify: overview/log hiển thị được nguồn lỗi và người vận hành biết campaign thất bại ở bước nào.
- [ ] Bổ sung test backend cho URL resolver, sync job, duplicate filtering và migration; nếu có test UI thì thêm ít nhất một case tạo campaign YouTube Shorts → Verify: `python -m pytest -q` pass cho backend và không làm gãy test hiện có.
- [ ] Verification cuối: chạy `python -m compileall app alembic`, `python -m pytest -q`, `npm run lint`, `npm run build`, sau đó test tay 3 case gồm TikTok cũ, một Shorts URL đơn lẻ, và một nguồn Shorts nhiều video → Verify: cả 3 flow đều tạo queue đúng, không phá comment/inbox/runtime config hiện có.

## Done When

- [ ] Dashboard tạo được campaign từ YouTube Shorts.
- [ ] Worker sync được video Shorts và đưa vào queue giống TikTok.
- [ ] Người vận hành nhìn thấy rõ source platform ở campaign, video và log.
- [ ] TikTok cũ vẫn hoạt động bình thường.

## Notes

- Critical path là `URL resolver` + `crawler chuẩn hóa` + `sync pipeline`.
- `yt-dlp` đã là lợi thế lớn vì bản thân service tải video hiện không bị khóa cứng vào TikTok ở tầng thư viện, chủ yếu bị khóa ở naming, giả định URL và UI.
- Nên giữ scope đầu tiên hẹp: chỉ hỗ trợ `YouTube Shorts URL` và `nguồn Shorts`, chưa mở rộng sang video YouTube dài.
- Khi rollout thật, nên thêm cảnh báo rõ trong UI nếu người dùng dán URL YouTube thường nhưng không phải Shorts.
