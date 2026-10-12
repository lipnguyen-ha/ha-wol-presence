# WOL + Presence

Integration cho Home Assistant: bật máy tính từ xa bằng Wake-on-LAN và cho biết máy đang thức hay ngủ, gộp trong **một công tắc**.

- Bật công tắc: gửi magic packet để đánh thức máy.
- Trạng thái công tắc: máy đang thức (on) hay đang ngủ, đã tắt (off).

Mỗi máy là một thiết bị riêng, thêm và sửa hoàn toàn trên giao diện, không cần viết YAML.

## Vì sao không dùng integration Wake on LAN có sẵn

- Integration có sẵn chỉ kiểm tra bằng ping. **Máy Mac vẫn trả lời ping khi đang ngủ**, nên luôn hiện là đang bật. Integration này có thêm cách kiểm tra bằng TCP, dùng được cho Mac.
- Magic packet được gửi tới cả broadcast của mạng con lẫn `255.255.255.255`, lặp 3 lần, vì mỗi router chuyển tiếp một kiểu.
- Sau khi gửi lệnh bật, integration kiểm tra dồn dập mỗi 5 giây trong 2 phút, nên công tắc chuyển sang "on" gần như ngay khi máy lên.

## Yêu cầu

- Home Assistant 2024.11 trở lên.
- Máy cần bật đã mở Wake-on-LAN trong BIOS và hệ điều hành, cắm mạng dây.
- Home Assistant nằm cùng mạng LAN với máy đó.

## Cài đặt

### Qua HACS

1. Mở HACS, bấm menu ba chấm ở góc phải trên, chọn **Custom repositories**.
2. Dán `https://github.com/lipnguyen-ha/ha-wol-presence`, chọn loại **Integration**, bấm **Add**.
3. Tìm **WOL + Presence** trong HACS, bấm **Download**.
4. Khởi động lại Home Assistant.

### Chép tay

1. Chép thư mục `custom_components/wol_presence` vào `/config/custom_components/wol_presence`.
2. Khởi động lại Home Assistant.

## Thêm thiết bị

Vào **Settings → Devices & Services → Add Integration**, tìm **WOL + Presence**, rồi điền:

| Trường | Ý nghĩa |
|---|---|
| Name | Tên hiển thị của máy |
| MAC address | Địa chỉ MAC của card mạng cần đánh thức |
| IP address | Địa chỉ IP dùng để kiểm tra máy còn thức không. Nên đặt IP tĩnh trên router |
| Presence check | `ping` cho PC, `tcp` cho Mac (xem bên dưới) |
| TCP port | Chỉ dùng khi chọn `tcp`. Mặc định 54321 |
| Broadcast address | Để trống thì tự suy ra từ IP (192.168.0.105 → 192.168.0.255) |
| Broadcast port | Mặc định 9, thường không cần đổi |
| Check every | Số giây giữa hai lần kiểm tra, mặc định 30 |

Sửa lại các thông số sau này bằng nút **Configure** của thiết bị.

## Chọn cách kiểm tra

| Loại máy | Chọn | Lý do |
|---|---|---|
| PC Windows, Linux | `ping` | Máy ngủ hoặc tắt thì không trả lời ping |
| Mac | `tcp` | Mac trả lời ping cả khi ngủ, nên ping luôn báo đang bật |

Với `tcp`, integration thử mở kết nối tới cổng đã chọn. Kết nối thành công **hoặc bị từ chối** đều có nghĩa là máy đang thức, chỉ khi không có phản hồi nào mới coi là đang ngủ. Vì vậy cổng nào cũng dùng được, kể cả cổng không có dịch vụ nào chạy. Mặc định 54321 là một cổng thường không ai dùng.

Một lần kiểm tra không có phản hồi chưa đủ để kết luận: integration thử hai lần liên tiếp, cả hai đều im lặng mới báo máy đã tắt.

## Lưu ý

- **Tắt công tắc không tắt máy.** Wake-on-LAN chỉ bật được, không tắt được. Khi bạn gạt tắt, công tắc sẽ tự trở về đúng trạng thái thật của máy.
- Nếu Home Assistant và máy cần bật nằm ở hai mạng con khác nhau, hãy điền Broadcast address của mạng chứa máy đó.

## Gỡ lỗi

Thêm vào `configuration.yaml` rồi khởi động lại:

```yaml
logger:
  logs:
    custom_components.wol_presence: debug
```

## Dự án liên quan

- [Aurora Home Theme](https://github.com/lipnguyen-ha/ha-aurora-home-theme): theme nền gradient, thẻ kính mờ cho Home Assistant.
- [IR Remote Card](https://github.com/lipnguyen-ha/ha-ir-remote-card): card remote cho thiết bị hồng ngoại không trạng thái, phát qua ESPHome.

## Giấy phép

Phát hành theo giấy phép [MIT](LICENSE).
