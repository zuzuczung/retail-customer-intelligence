"""Dashboard semantics and layout, independent of deployment IDs."""
TEAL='#168C92'; BLUE='#4C78A8'; NAVY='#183153'; AMBER='#D89A28'
METRICS={
 'orders':('Số hóa đơn bán','COUNT(*)',',d'),
 'sales':('Doanh thu bán hàng (GBP)','SUM(sales_amount)',',.2f'),
 'known_customers':('Khách có mã','COUNT(DISTINCT customer_id)',',d'),
 'aov':('Giá trị đơn trung bình (GBP)','SUM(sales_amount)/NULLIF(COUNT(*),0)',',.2f'),
 'units':('Số lượng bán','SUM(quantity)',',d'),
 'products':('Số sản phẩm','COUNT(DISTINCT stock_code)',',d'),
 'product_orders':('Số đơn có sản phẩm','COUNT(DISTINCT invoice_no)',',d'),
 'adjustment':('Giá trị hủy/điều chỉnh (GBP)','SUM(adjustment_amount)',',.2f'),
 'rfm_customers':('Số khách','COUNT(*)',',d'),
 'rfm_sales':('Giá trị mua (GBP)','SUM(monetary)',',.2f'),
 'rfm_avg_value':('Giá trị mua TB mỗi khách (GBP)','AVG(monetary)',',.2f'),
 'rfm_risk':('Khách có nguy cơ rời bỏ',"COUNT(*) FILTER(WHERE segment='Có nguy cơ rời bỏ')",',d'),
 'rfm_recency':('Ngày từ lần mua cuối','MAX(recency_days)',',d'),
 'rfm_frequency':('Số lần mua','MAX(frequency)',',d'),
 'cohort_size':('Khách gia nhập cohort','SUM(cohort_size) FILTER(WHERE age_month=0)',',d'),
 'retention':('Tỷ lệ quay lại','SUM(active_customers)::numeric/NULLIF(SUM(cohort_size),0)','.1%'),
 'retention_m1':('Quay lại tháng kế tiếp','SUM(active_customers) FILTER(WHERE age_month=1)::numeric/NULLIF(SUM(cohort_size) FILTER(WHERE age_month=1),0)','.1%'),
}
DATASETS={
 'orders':('fact_order','purchased_at',['orders','sales','known_customers','aov']),
 'lines':('fact_line','purchased_at',['sales','units','products','product_orders']),
 'adjustments':('v_adjustment','purchased_at',['adjustment']),
 'customers':('customer_rfm','snapshot_at',['rfm_customers','rfm_sales','rfm_avg_value','rfm_risk','rfm_recency','rfm_frequency']),
 'cohorts':('cohort_retention','cohort_month',['cohort_size','retention','retention_m1']),
}
LABELS={
 'invoice_no':'Hóa đơn','purchased_at':'Ngày mua','stock_code':'Mã sản phẩm','product_name':'Tên sản phẩm','product_label':'Sản phẩm',
 'country':'Quốc gia','customer_id':'Mã khách','segment':'Nhóm khách','rfm_score':'Điểm RFM',
 'cohort_month':'Tháng mua đầu tiên','age_label':'Tuổi cohort','age_month':'Số tháng từ lần mua đầu',
 'snapshot_at':'Ngày chốt RFM','first_purchased_at':'Lần mua đầu','last_purchased_at':'Lần mua cuối',
 'recency_days':'Ngày từ lần mua cuối','frequency':'Số lần mua','monetary':'Giá trị mua (GBP)',
 'r_score':'Điểm R','f_score':'Điểm F','m_score':'Điểm M','cohort_size':'Khách ban đầu','active_customers':'Khách quay lại',
 'sales_amount':'Doanh thu bán hàng (GBP)','quantity':'Số lượng','adjustment_amount':'Giá trị hủy/điều chỉnh (GBP)',
 'activity_month':'Tháng hoạt động','last_complete_month':'Tháng hoàn chỉnh cuối',
}
SEGMENT_COLORS={'Giá trị cao':TEAL,'Thân thiết':BLUE,'Có nguy cơ rời bỏ':AMBER,'Ngủ đông':'#9B8562','Đang phát triển':'#88A9C9'}


def v(key,title,kind,dataset,metric,dimension=None,**kwargs):
    return dict(key=key,title=title,kind=kind,dataset=dataset,metric=metric,dimension=dimension,**kwargs)


PAGES=[
 dict(key='overview',title='Tổng quan',note='UCI Online Retail · 01/12/2010–09/12/2011 · GBP · Tháng 12/2011 chưa đủ tháng. Doanh thu hàng hóa chưa trừ hủy/điều chỉnh; không phải lợi nhuận.',rows=[
  [v('sales','Doanh thu bán hàng (GBP)','kpi','orders','sales'),v('orders','Số hóa đơn bán','kpi','orders','orders'),v('known','Khách có mã','kpi','orders','known_customers'),v('aov','Giá trị đơn trung bình (GBP)','kpi','orders','aov')],
  [v('monthly-sales','Doanh thu theo tháng','line','orders','sales','purchased_at',width=7),v('country-sales','Top 10 quốc gia theo doanh thu','bar','orders','sales','country',horizontal=True,width=5,limit=10)],
  [v('overview-products','Top 5 sản phẩm theo doanh thu','table','lines','sales','stock_code',dimensions=['stock_code','product_name'],metrics=['sales','units','product_orders'],limit=5)],
 ]),
 dict(key='products',title='Sản phẩm',note='Chỉ mã hàng hóa hợp lệ · Giữ các giao dịch giá trị lớn trong nguồn · Giá trị hủy/điều chỉnh được trình bày riêng, chưa xác nhận hoàn tiền thực tế.',rows=[
  [v('units','Số lượng hàng bán','kpi','lines','units'),v('products','Số sản phẩm có bán','kpi','lines','products'),v('adjustments','Giá trị hủy/điều chỉnh (GBP)','kpi','adjustments','adjustment')],
  [v('product-sales','Top 10 sản phẩm theo doanh thu','bar','lines','sales','stock_code',horizontal=True,limit=10),v('product-units','Top 10 sản phẩm theo số lượng','bar','lines','units','stock_code',horizontal=True,limit=10)],
  [v('product-detail','Chi tiết sản phẩm','table','lines','sales','stock_code',dimensions=['stock_code','product_name'],metrics=['sales','units','product_orders'],limit=30)],
 ]),
 dict(key='customers',title='Khách hàng',note='RFM chốt tại 10/12/2011, dùng toàn bộ lịch sử mua hợp lệ. Tab này chỉ lọc theo quốc gia; bộ lọc thời gian không áp dụng. Phân nhóm theo quy tắc R/F/M, không phải dự đoán rời bỏ.',rows=[
  [v('rfm-customers','Khách có mã trong toàn bộ lịch sử','kpi','customers','rfm_customers'),v('rfm-avg','Giá trị mua TB mỗi khách (GBP)','kpi','customers','rfm_avg_value'),v('rfm-risk','Khách có nguy cơ rời bỏ','kpi','customers','rfm_risk')],
  [v('segment-customers','Số khách theo nhóm RFM','bar','customers','rfm_customers','segment',horizontal=True),v('segment-sales','Giá trị mua theo nhóm RFM','bar','customers','rfm_sales','segment',horizontal=True)],
  [v('customer-detail','Khách có giá trị mua cao','table','customers','rfm_sales','customer_id',dimensions=['customer_id','country','segment','rfm_score'],metrics=['rfm_sales','rfm_frequency','rfm_recency'],limit=20)],
 ]),
 dict(key='retention',title='Giữ chân',note='Cohort = tháng mua đầu tiên trong nguồn · M00: tháng đầu, M01: tháng kế · Bộ lọc thời gian chọn tháng gia nhập cohort. Chỉ dùng tháng hoàn chỉnh đến 11/2011; ô chưa quan sát để trống. Chỉ khách có mã; quốc gia gán theo lần mua đầu.',rows=[
  [v('cohort-customers','Khách gia nhập cohort','kpi','cohorts','cohort_size'),v('retention-m1','Quay lại tháng kế tiếp','kpi','cohorts','retention_m1')],
  [v('cohort-heatmap','Tỷ lệ quay lại theo cohort','pivot','cohorts','retention','cohort_month',columns='age_label')],
  [v('retention-curve','Tỷ lệ quay lại theo tuổi (mẫu cohort thay đổi)','line','cohorts','retention','age_label',width=6),v('cohort-size','Số khách gia nhập theo tháng','bar','cohorts','cohort_size','cohort_month',width=6)],
 ]),
]


def visuals():return [item for page in PAGES for row in page['rows'] for item in row]


def form(item,dataset_id):
    kind=item['kind']; metric=item['metric'];fmt=METRICS[metric][2]
    types={'kpi':'big_number_total','bar':'echarts_timeseries_bar','line':'echarts_timeseries_line','table':'table','pivot':'pivot_table_v2'}
    color=AMBER if metric in ['adjustment','rfm_risk'] else BLUE if metric in ['known_customers','units','products','orders','product_orders','rfm_customers','cohort_size'] else TEAL
    label_colors={k:color for k in [metric,METRICS[metric][0]]}
    label_colors.update(SEGMENT_COLORS)
    f=dict(datasource=f'{dataset_id}__table',viz_type=types[kind],metrics=item.get('metrics',[metric]),
      granularity_sqla=DATASETS[item['dataset']][1],time_range='No filter',adhoc_filters=[],
      row_limit=item.get('limit',1000),order_desc=True,extra_form_data={},color_scheme='supersetColors',
      label_colors=label_colors,number_format=fmt,y_axis_format=fmt,show_legend=False,
      annotation_layers=[],rich_tooltip=True,show_empty_columns=True)
    if kind=='kpi':
        f.update(metric=metric,header_font_size=.32,subheader_font_size=.12,y_axis_format=fmt)
    elif kind=='pivot':
        f.update(groupbyRows=['cohort_month'],groupbyColumns=['age_label'],metricsLayout='COLUMNS',
          aggregateFunction='Sum',rowTotals=False,colTotals=False,rowSubTotals=False,colSubTotals=False,
          valueFormat='.1%',rowOrder='key_a_to_z',colOrder='key_a_to_z',transposePivot=False,combineMetric=True,
          conditional_formatting=[dict(column=metric,operator='None',colorScheme=TEAL)],
          date_format='%Y-%m',allow_render_html=False)
    elif kind=='table':
        f.update(query_mode='aggregate',groupby=item.get('dimensions',[item['dimension']]),
          all_columns=[],percent_metrics=[],include_search=True,show_cell_bars=True,
          table_timestamp_format='%Y-%m',page_length=10,show_totals=False,order_by_cols=[],
          column_config={k:{'d3NumberFormat':METRICS[k][2]} for k in f['metrics']},
          conditional_formatting=[dict(column=metric,operator='None',colorScheme=TEAL)])
    else:
        dim=item['dimension'];temporal=dim in ['purchased_at','cohort_month']
        f.update(x_axis=dim,groupby=[],xAxisForceCategorical=not temporal,
          time_grain_sqla='P1M',x_axis_sort=dim if kind=='line' or temporal else metric,
          x_axis_sort_asc=bool(kind=='line' or temporal or item.get('horizontal')),
          orientation='horizontal' if item.get('horizontal') else 'vertical',
          x_axis_title='' if item.get('horizontal') else LABELS.get(dim,dim),
          y_axis_title=METRICS[metric][0],x_axis_time_format='%Y-%m',
          x_axis_title_margin=28,y_axis_title_margin=55,truncateXAxis=True,
          truncate_metric=True,show_value=kind=='bar',xAxisLabelRotation=0,
          showTooltipTotal=False,zoomable=False,show_legend=False)
        if metric not in ['retention','retention_m1']:
            f.update(y_axis_format='.3s',number_format='.3s')
        if kind=='line':f.update(markerEnabled=True,markerSize=4,truncateYAxis=False)
    return f


def context(item,dataset_id,filters=None,time_range=None):
    f=form(item,dataset_id)
    cols=[]
    if item['dimension']:cols=item.get('dimensions',[item['dimension']])[:]
    if item.get('columns'):cols.append(item['columns'])
    if item['kind'] in ['line','bar'] and item['dimension'] in ['purchased_at','cohort_month']:
        cols=[{'timeGrain':'P1M','columnType':'BASE_AXIS','sqlExpression':item['dimension'],'label':item['dimension'],'expressionType':'SQL'}]
    query=dict(columns=cols,metrics=item.get('metrics',[item['metric']]),filters=filters or [],
      time_range=time_range or 'No filter',granularity=DATASETS[item['dataset']][1],
      extras={'having':'','where':'','time_grain_sqla':'P1M'},row_limit=item.get('limit',1000),
      orderby=[(item['metric'],False)] if item['kind'] not in ['pivot','kpi'] else [],order_desc=True,
      applied_time_extras={})
    return dict(datasource={'id':dataset_id,'type':'table'},force=True,queries=[query],form_data=f,result_format='json',result_type='full')
