# Hợp đồng dữ liệu Retail Customer Intelligence

Nguồn duy nhất: UCI Online Retail, Chen (2015), DOI 10.24432/C5BW33, CC BY 4.0. Dữ liệu lịch sử, không đại diện doanh nghiệp hiện tại.

- Giữ toàn bộ 8 trường nguồn trong staging, thêm source_row (số dòng Excel, bắt đầu 2). Số dòng nguồn phải là 541909, header đúng và kiểu ngày/số đọc được.
- Bản ghi trùng hoàn toàn trên 8 trường: giữ dòng có source_row nhỏ nhất trong analytics; giữ bản gốc trong staging.
- Hàng hóa: StockCode khớp `^[0-9]{5}[A-Za-z]*$`. Mã bưu phí, phí, điều chỉnh và các mã khác bị loại khỏi phân tích hàng hóa; ghi số dòng và giá trị loại.
- Bán hàng hợp lệ: hàng hóa, Quantity > 0, UnitPrice > 0, InvoiceNo không bắt đầu bằng C, InvoiceDate hợp lệ. Cho phép thiếu CustomerID trong doanh thu/số đơn; loại khỏi chỉ tiêu khách hàng, RFM và cohort.
- Hủy/điều chỉnh hợp lệ: hàng hóa, Quantity < 0, UnitPrice > 0, bất kể có mã C hay không. Giá trị âm không được diễn giải thành chi phí hay lợi nhuận. Không giả định tất cả mã C đều đã hoàn tiền thực tế.
- Tính tiền bằng numeric; staging và analytics phải đối soát giá trị theo cùng điều kiện. Fact order một dòng mỗi InvoiceNo bán hợp lệ; không nối nhiều dòng hàng làm tăng số đơn.
- Khách có ID được gán quốc gia theo lần mua hợp lệ đầu tiên trong toàn bộ nguồn; mọi tab dùng cùng quy tắc. Giữ quốc gia của giao dịch riêng để kiểm tra khác biệt. Khách thiếu ID dùng quốc gia nguồn cho biểu đồ doanh thu.
- AOV = doanh thu bán hàng / số hóa đơn bán hợp lệ, bao gồm đơn thiếu CustomerID. Khách xác định = COUNT(DISTINCT CustomerID), không tính NULL.
- RFM: snapshot tại ngày sau ngày cuối cùng của nguồn, toàn bộ lịch sử mua hợp lệ; bộ lọc thời gian không áp dụng cho tab Khách hàng. Lọc quốc gia có áp dụng. R: <=30/60/90/180/>180 ngày có điểm 5/4/3/2/1. F: >=10/6/3/2/<2 đơn có điểm 5/4/3/2/1. M: >=5000/2000/1000/500/<500 GBP có điểm 5/4/3/2/1. Phân nhóm theo quy tắc, không phải mô hình dự đoán rời bỏ.
- Cohort: tháng mua hợp lệ đầu tiên trong toàn bộ nguồn. Một dòng cho cohort × quốc gia × tuổi tháng. Dựng cả ô có 0 khách quay lại. Chỉ dùng tháng quan sát hoàn chỉnh; bỏ tháng cuối nếu dữ liệu dừng trước cuối tháng. M0 = 100%; 0 <= active <= cohort_size; các tháng tương lai không tạo dòng, không điền 0. Bộ lọc thời gian trên tab Giữ chân lọc tháng gia nhập cohort, không lọc tháng giao dịch.
- Kiểm tra bắt buộc: khóa fact, số dòng nguồn, phân hoạch loại dòng, doanh thu nguồn→fact line→fact order, khóa nối, số khách snapshot, M0, giới hạn retention, loại tháng chưa đủ và đối soát truy vấn chart với SQL trực tiếp, gồm ít nhất một quốc gia và khoảng ngày.

Phát hiện khi chạy kiểm tra: 42 hóa đơn có hai mốc thời gian cách nhau 1 phút. Mốc phân tích của mọi dòng trong một hóa đơn được chuẩn hóa về thời gian sớm nhất của hóa đơn; giữ source_purchased_at và staging nguyên gốc để truy vết. Không thay đổi số đơn hoặc giá trị.
