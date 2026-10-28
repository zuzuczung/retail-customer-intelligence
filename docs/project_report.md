# Đánh giá project Retail Customer Intelligence

Trạng thái ngày 28/10/2026: đã triển khai PostgreSQL và dashboard Apache Superset với dữ liệu thật UCI. Nguồn chỉ phản ánh nhà bán lẻ trong giai đoạn 01/12/2010–09/12/2011, không phải hoạt động hiện tại. Số liệu mô phỏng của demo được tách khỏi pipeline thực.

## 1. Xác định vấn đề

**Đã thực hiện:** Xác định bốn nhóm câu hỏi: quy mô/xu hướng bán hàng; đóng góp của sản phẩm; phân nhóm khách theo RFM; hành vi quay lại theo tháng mua đầu trong nguồn. Phạm vi hàng hóa được tách khỏi bưu phí, phí thủ công và điều chỉnh không phải mã hàng. Đầu ra là dashboard 4 tab cho phân tích portfolio.

**Bằng chứng/kết quả:** `docs/data-contract.md`, bộ metric trong `retail_bi/dashboard_spec.py`, 24 chart và 5 dataset trong `artifacts/deployment.json`. Định nghĩa doanh thu bán dương, AOV, khách hợp lệ, attribution quốc gia, snapshot RFM và mẫu số cohort được ghi rõ.

**Hạn chế:** Không có giá vốn, chi phí marketing, số dư tài khoản hay log sử dụng sản phẩm. Không đo được lợi nhuận, CAC, churn thực tế hoặc hiệu quả một chiến dịch chăm sóc. Tháng mua đầu trong nguồn có thể không phải lần mua đầu của khách trong đời.

**Đề xuất bổ sung, chưa thực hiện:** Bổ sung chi phí/lịch sử trước kỳ quan sát và xác nhận định nghĩa kinh doanh nếu chuyển project sang doanh nghiệp thật.

## 2. Thu thập dữ liệu

**Đã thực hiện:** Tải ZIP/XLSX từ UCI, kiểm tra 8 trường, lưu bản gốc và SHA-256. Đọc XLSX, tạo CSV trung gian có số dòng Excel và bộ tổng kiểm soát bằng Python/Decimal; nạp staging riêng trong PostgreSQL.

**Bằng chứng/kết quả:** Đủ **541.909 dòng**, thời gian 01/12/2010 08:26 đến 09/12/2011 12:50. `source-manifest.json`, `artifacts/source-profile.json`, `staging.load_audit`. Nguồn: Chen, D. (2015), [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail), DOI 10.24432/C5BW33, CC BY 4.0.

**Hạn chế:** **135.080 dòng thiếu mã khách**, chiếm khoảng 24,93% số dòng nguồn; 1.371 hóa đơn bán hợp lệ thiếu mã khách, với £1.509.593,23 doanh thu. Phần này được giữ trong bán hàng nhưng không tham gia RFM/cohort. Dữ liệu tháng 12/2011 chỉ đến ngày 9.

**Đề xuất bổ sung, chưa thực hiện:** Bổ sung định danh khách hoặc đánh giá cách thu thập nếu có nguồn doanh nghiệp thực. Chưa gán mã khách giả hoặc suy đoán danh tính cho các dòng thiếu.

## 3. Làm sạch dữ liệu

**Đã thực hiện:** Khử trùng chính xác trên 8 trường, giữ staging gốc; phân loại hàng hóa, giá không hợp lệ và dòng âm; chuẩn hóa ngày/số. Tổng hợp fact ở đúng grain. Quốc gia khách có mã được gán theo lần mua hợp lệ đầu tiên. Timestamp phân tích của từng hóa đơn dùng thời gian sớm nhất, còn timestamp nguồn vẫn được lưu.

**Bằng chứng/kết quả:** Phân hoạch đầy đủ 541.909 dòng thành:

| Loại dòng | Số dòng |
|---|---:|
| Bán hàng hóa hợp lệ | 522.504 |
| Hủy/điều chỉnh âm hàng hóa hợp lệ | 8.668 |
| Trùng hoàn toàn | 5.268 |
| Không phải mã hàng hóa theo quy tắc | 2.989 |
| Giá không hợp lệ trong phần còn lại | 2.480 |

Có 42 hóa đơn chênh timestamp một phút, đã chuẩn hóa; 169 dòng có quốc gia giao dịch khác quốc gia lần mua đầu. Kiểm tra nguồn/mô hình **19/19 đạt**; các tình huống giá 0/âm, mã C, dòng âm không có C, mã phí và ranh giới RFM được kiểm thử. Bằng chứng: `artifacts/data-validation.json`, `tests/`, `sql/02_analytics.sql`.

**Hạn chế:** Quy tắc mã hàng dựa vào định dạng StockCode, không phải danh mục quản trị được doanh nghiệp xác nhận. Dòng bán lớn nhất vẫn được giữ: £168.469,60 và £77.183,60; nguồn có dòng âm cùng mã/số lượng. Không tự nối chúng thành “đã hoàn tiền” vì thiếu tham chiếu hóa đơn gốc.

**Đề xuất bổ sung, chưa thực hiện:** Bổ sung mapping mã hàng chuẩn và đối soát hoàn/hủy với nguồn kế toán. Đánh giá độ nhạy của bảng xếp hạng khi dùng giá trị ròng hoặc loại giao dịch đã được xác nhận đảo chiều; chưa tự xóa ngoại lai chỉ vì lớn.

## 4. Phân tích dữ liệu

**Đã thực hiện:** Xây fact hóa đơn/dòng hàng, snapshot RFM theo ngưỡng, scaffold cohort theo tháng hoàn chỉnh và dashboard Superset. Bộ lọc ngày áp dụng cho bán hàng, tháng gia nhập áp dụng cho cohort; RFM giữ snapshot 10/12/2011 và được loại khỏi bộ lọc ngày. Quốc gia dùng cùng attribution ở các tab.

**Bằng chứng/kết quả:**

- **19.773 hóa đơn**, **4.334 khách có mã**, **£10.246.820,87** doanh thu bán dương hàng hóa, AOV **£518,22**. Giá trị tuyệt đối các dòng âm hàng hóa: **£475.901,16**, được trình bày riêng.
- Snapshot RFM có 747 khách nhóm Giá trị cao, 973 Thân thiết, 278 Có nguy cơ rời bỏ, 1.171 Ngủ đông và 1.165 Đang phát triển. Đây là nhãn theo quy tắc, không phải dự đoán hành vi đã được kiểm định.
- 747 khách nhóm Giá trị cao chiếm khoảng **63,08% giá trị mua của nhóm có mã**, không phải 63,08% tổng doanh thu toàn bộ nguồn.
- Cohort các tháng hoàn chỉnh có 4.293 khách. M1 tính trên 3.970 khách đủ thời gian quan sát, trong đó 932 khách quay lại: **23,48%**. M0 bằng 100%, tỷ lệ 0 thật được giữ, ô tương lai không được tạo.
- **120/120 đối soát chart–SQL** đạt qua 5 tình huống. 10/10 unit/integration tests đạt; chạy lại giữ nguyên ID các tài nguyên. Xem `artifacts/chart-validation.json`, `idempotency.json`, `insights.json`.

**Hạn chế:** Chưa trừ dòng âm khỏi monetary RFM; khách bán buôn và ngoại lai có thể ảnh hưởng giá trị trung bình/xếp hạng. Tháng 12/2011 chưa đủ nên không so trực tiếp với tháng đầy đủ. Đường retention gộp thay đổi tập cohort đủ tuổi theo từng mốc; không diễn giải như quỹ đạo của một tập khách cố định. Chưa đo tác động nhân quả.

**Đề xuất bổ sung, chưa thực hiện:** So sánh RFM theo giá trị ròng sau khi xác nhận cách hạch toán điều chỉnh; nghiên cứu cohort đồng nhất theo cùng cửa sổ; có thể thử mô hình phân cụm/predictive nếu có bài toán đánh giá và nhãn phù hợp. Không bắt buộc thêm machine learning chỉ để có đủ công cụ.

## 5. Diễn giải kết quả

**Đã thực hiện:** Dashboard phân biệt doanh thu bán hàng với dòng âm, khách thiếu mã với khách đủ điều kiện, snapshot với số liệu theo kỳ và tháng chưa đủ quan sát. Báo cáo tách các kết quả quan sát khỏi kiến nghị.

**Bằng chứng/kết quả:** Giá trị mua của nhóm có mã tập trung ở nhóm Giá trị cao theo quy tắc RFM, nên đây là nhóm phù hợp để tiếp tục nghiên cứu chăm sóc khách trong bài toán portfolio. 278 khách được gắn nhãn Có nguy cơ rời bỏ có lịch sử mua lặp nhưng lần mua cuối cách mốc chốt tương đối xa; chưa có bằng chứng họ thực sự rời bỏ. Tỷ lệ M1 23,48% là mô tả mẫu đủ điều kiện, chưa có benchmark để kết luận cao hay thấp.

**Hạn chế:** Không biết lý do khách không quay lại; không thể quy kết sản phẩm, mùa vụ hay chất lượng dịch vụ là nguyên nhân. Không thể coi hai sản phẩm có số lượng bán lớn bất thường là nhu cầu bền vững khi nguồn có dòng âm cùng mã/số lượng.

**Đề xuất bổ sung, chưa thực hiện:** Quay lại bước xác định vấn đề với một thử nghiệm cụ thể, ví dụ đánh giá chương trình giữ chân trên nhóm đủ điều kiện; bổ sung chi phí và quan sát sau can thiệp để đo giá trị ròng/tác động. Chưa triển khai chiến dịch, dự báo hoặc đưa ra kết luận về hiệu quả một hành động kinh doanh.
