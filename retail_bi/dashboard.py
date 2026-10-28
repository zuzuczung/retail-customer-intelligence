"""Create project-owned Superset resources using UUIDs and REST APIs."""
import json
import os
from urllib.parse import quote
from .api import API,uid
from .config import ROOT,MARKER
from .dashboard_spec import DATASETS,METRICS,LABELS,PAGES,TEAL,BLUE,NAVY,AMBER,SEGMENT_COLORS,visuals,form,context

SLUG='retail-customer-intelligence'


def save(name,value):
    (ROOT/'artifacts'/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n')


def layout(charts):
    pos={'DASHBOARD_VERSION_KEY':'v2',
     'ROOT_ID':dict(type='ROOT',id='ROOT_ID',children=['GRID_ID']),
     'GRID_ID':dict(type='GRID',id='GRID_ID',children=['TABS-RETAIL'],parents=['ROOT_ID']),
     'TABS-RETAIL':dict(type='TABS',id='TABS-RETAIL',children=[],parents=['ROOT_ID','GRID_ID'],meta={})}
    for page in PAGES:
        tab='TAB-RETAIL-'+page['key'];pos['TABS-RETAIL']['children'].append(tab)
        parents=['ROOT_ID','GRID_ID','TABS-RETAIL']
        pos[tab]=dict(id=tab,type='TAB',children=[],parents=parents,meta={'text':page['title']})
        note='NOTE-'+page['key'];row='ROW-NOTE-'+page['key'];pos[tab]['children'].append(row)
        pos[row]=dict(id=row,type='ROW',children=[note],parents=parents+[tab],meta={'background':'BACKGROUND_TRANSPARENT'})
        pos[note]=dict(id=note,type='MARKDOWN',children=[],parents=parents+[tab,row],meta={'code':page['note'],'width':12,'height':8})
        for index,items in enumerate(page['rows']):
            row='ROW-'+page['key']+'-'+str(index);pos[tab]['children'].append(row)
            pos[row]=dict(id=row,type='ROW',children=[],parents=parents+[tab],meta={'background':'BACKGROUND_TRANSPARENT'})
            for item in items:
                ident=charts[item['key']];node='CHART-'+str(ident);pos[row]['children'].append(node)
                height=24 if item['kind']=='kpi' else 66 if item['kind']=='pivot' else 54 if item['kind']=='table' else 50
                pos[node]=dict(id=node,type='CHART',children=[],parents=parents+[tab,row],
                  meta=dict(chartId=ident,uuid=uid('chart:'+item['key']),sliceName=item['title'],width=item.get('width',12//len(items)),height=height))
    return pos


def native_filters(datasets,charts):
    rfm=[charts[v['key']] for v in visuals() if v['dataset']=='customers']
    allids=list(charts.values());timeids=[i for i in allids if i not in rfm]
    return [dict(id='NATIVE_FILTER-RETAIL-TIME',type='NATIVE_FILTER',name='Thời gian / tháng gia nhập cohort',
      filterType='filter_time',targets=[{}],defaultDataMask={'extraFormData':{'time_range':'2010-12-01 : 2011-12-10'},'filterState':{'value':'2010-12-01 : 2011-12-10'},'ownState':{}},
      cascadeParentIds=[],controlValues={'enableEmptyFilter':False},scope={'rootPath':['ROOT_ID'],'excluded':rfm},
      chartsInScope=timeids,tabsInScope=['TAB-RETAIL-'+p['key'] for p in PAGES if p['key']!='customers'],
      description='Ngày mua ở Tổng quan/Sản phẩm; tháng mua đầu ở Giữ chân. Không áp dụng cho RFM.'),
     dict(id='NATIVE_FILTER-RETAIL-COUNTRY',type='NATIVE_FILTER',name='Quốc gia',filterType='filter_select',
      targets=[{'datasetId':i,'column':{'name':'country'}} for i in datasets.values()],
      defaultDataMask={'extraFormData':{},'filterState':{},'ownState':{}},cascadeParentIds=[],
      controlValues={'enableEmptyFilter':False,'multiSelect':True,'searchAllOptions':True,'inverseSelection':False},
      scope={'rootPath':['ROOT_ID'],'excluded':[]},chartsInScope=allids,tabsInScope=['TAB-RETAIL-'+p['key'] for p in PAGES],
      description='Khách có mã: quốc gia lần mua hợp lệ đầu tiên. Khách không mã: quốc gia nguồn.')]


def main():
    api=API();db_name='Retail Customer Intelligence'
    db_uuid=uid('database:retail')
    matches=[d for d in api.all('database') if d['uuid']==db_uuid]
    collision=[d for d in api.all('database') if d['database_name']==db_name and d['uuid']!=db_uuid]
    if collision:raise RuntimeError('Unowned Superset database name collision')
    user=quote(os.environ['SUPERSET_DATABASE_USER'],safe='');pw=quote(os.environ['SUPERSET_DATABASE_PASSWORD'],safe='')
    uri=f'postgresql+psycopg2://{user}:{pw}@host.docker.internal:5432/retail_customer_intelligence'
    body=dict(database_name=db_name,sqlalchemy_uri=uri,expose_in_sqllab=True,allow_ctas=False,allow_cvas=False,allow_dml=False,allow_file_upload=False,
      extra=json.dumps({'metadata_params':{},'engine_params':{},'retail_project':MARKER}),uuid=db_uuid)
    if matches:
        dbid=matches[0]['id'];api.request('PUT',f'database/{dbid}',json=body)
    else:dbid=api.request('POST','database/',json=body)['id']
    datasets={}
    for key,(table,timecol,metric_keys) in DATASETS.items():
        identity=uid('dataset:'+key)
        found=[d for d in api.all('dataset') if d['uuid']==identity]
        if found:
            ident=found[0]['id']
            current=api.request('GET',f'dataset/{ident}')['result']
            if not (current.get('description') or '').startswith(MARKER):raise RuntimeError('Dataset ownership mismatch')
            api.request('PUT',f'dataset/{ident}/refresh',json={})
        else:
            ident=api.request('POST','dataset/',json=dict(database=dbid,schema='analytics',table_name=table,uuid=identity))['id']
            api._lists['dataset'].append({'id':ident,'uuid':identity})
        detail=api.request('GET',f'dataset/{ident}')['result'];oldmetrics={m['metric_name']:m['id'] for m in detail['metrics']}
        metrics=[dict(metric_name=k,verbose_name=METRICS[k][0],expression=METRICS[k][1],d3format=METRICS[k][2],description='Definition: docs/data-contract.md',**({'id':oldmetrics[k]} if k in oldmetrics else {})) for k in metric_keys]
        columns=[dict(id=c['id'],column_name=c['column_name'],verbose_name=LABELS.get(c['column_name'],c['column_name'])) for c in detail['columns']]
        api.request('PUT',f'dataset/{ident}',json=dict(description=MARKER+'; source=UCI Online Retail; '+('RFM fixed at 2011-12-10' if key=='customers' else 'cohort acquisition month filter; complete months only' if key=='cohorts' else 'see data contract'),
          main_dttm_col=timecol,filter_select_enabled=True,metrics=metrics,columns=columns))
        datasets[key]=ident
    charts={}
    for item in visuals():
        ds=datasets[item['dataset']];f=form(item,ds)
        charts[item['key']]=api.upsert('chart',item['key'],dict(slice_name=item['title'],description=MARKER+'; '+next(p['note'] for p in PAGES if any(item in row for row in p['rows'])),
          datasource_id=ds,datasource_type='table',viz_type=f['viz_type'],params=json.dumps(f,ensure_ascii=False),query_context=json.dumps(context(item,ds),ensure_ascii=False)))
    label_colors={}
    for key,(label,expression,fmt) in METRICS.items():
        color=AMBER if key in ['adjustment','rfm_risk'] else BLUE if key in ['orders','known_customers','units','products','product_orders','rfm_customers','cohort_size'] else TEAL
        label_colors.update({key:color,label:color})
    label_colors.update(SEGMENT_COLORS)
    metadata=dict(native_filter_configuration=native_filters(datasets,charts),filter_bar_orientation='HORIZONTAL',
      cross_filters_enabled=False,chart_configuration={},color_scheme='supersetColors',label_colors=label_colors,
      refresh_frequency=0,expanded_slices={},timed_refresh_immune_slices=[],map_label_colors={},shared_label_colors=[],color_scheme_domain=[])
    css='''
.dashboard-content,.dashboard-component-tabs-content{background:#F5F7FA;}
.dashboard-chart{background:transparent!important;border:0!important;border-radius:0!important;}
.dashboard-component-chart-holder .chart-slice{background:transparent;border:0;border-radius:10px;box-shadow:none;}
.dashboard-component-chart-holder .header-title a,.dashboard-header .editable-title{color:#183153!important;}
.dashboard-component-chart-holder .header-title a{font-size:13px!important;line-height:18px!important;font-weight:600;}
.dashboard-component-chart-holder .header-line{color:#183153!important;}
.dashboard-component-tabs .ant-tabs-tab-active .ant-tabs-tab-btn{color:#168C92!important;}
.dashboard-component-tabs .ant-tabs-ink-bar{background:#168C92!important;}
.dashboard-component-chart-holder{border-radius:10px;background:#FFFFFF;border:1px solid #DCE4EB;}
.dashboard-markdown{color:#52677F;font-size:12px;line-height:18px;}
'''
    for item in visuals():
        if item['kind']=='kpi':css+=f' .dashboard-chart-id-{charts[item["key"]]} .big_number {{color:#183153;}}'
    css+=f' .dashboard-chart-id-{charts["cohort-heatmap"]} table td, .dashboard-chart-id-{charts["cohort-heatmap"]} table td a {{color:#111111!important;}}'
    css+=f' .dashboard-chart-id-{charts["cohort-heatmap"]} table thead tr:nth-child(2) {{display:none;}}'
    css+=f' .dashboard-chart-id-{charts["rfm-risk"]} {{border-top:3px solid #D89A28;}}'
    themes=api.all('theme');light=[t for t in themes if t.get('theme_name')=='THEME_DEFAULT' and t.get('is_system')]
    body=dict(dashboard_title='Retail Customer Intelligence',slug=SLUG,published=True,position_json=json.dumps(layout(charts),ensure_ascii=False),json_metadata=json.dumps(metadata,ensure_ascii=False),css=css)
    if light:body['theme_id']=light[0]['id']
    for d in api.all('dashboard'):
        if d.get('slug')==SLUG and d.get('uuid')!=uid('dashboard:main'):raise RuntimeError('Unowned dashboard slug collision')
    dashboard=api.upsert('dashboard','main',body)
    for item in visuals():
        ident=charts[item['key']];ds=datasets[item['dataset']];f=form(item,ds);f.update(slice_id=ident,dashboards=[dashboard])
        ctx=context(item,ds);ctx['form_data']=f
        api.request('PUT',f'chart/{ident}',json={'dashboards':[dashboard],'params':json.dumps(f,ensure_ascii=False),'query_context':json.dumps(ctx,ensure_ascii=False)})
    state=dict(database_id=dbid,datasets=datasets,charts=charts,dashboard_id=dashboard,
       dashboard_url=api.base+'/superset/dashboard/'+SLUG+'/',pages=[p['title'] for p in PAGES],
       source='https://archive.ics.uci.edu/dataset/352/online+retail',palette={'navy':NAVY,'teal':TEAL,'blue':BLUE,'amber':AMBER})
    save('deployment.json',state)
    export=api.request('GET',f'dashboard/export/?q=!({dashboard})')
    (ROOT/'artifacts/retail_superset_dashboard_export.zip').write_bytes(export)
    print(json.dumps({'url':state['dashboard_url'],'charts':len(charts),'datasets':len(datasets),'dashboard_id':dashboard},ensure_ascii=False))


if __name__=='__main__':main()
