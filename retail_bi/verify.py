"""Reconcile every saved chart query to PostgreSQL, including filter boundaries."""
from datetime import datetime, date,timezone
from decimal import Decimal
import json
from .api import API
from .config import ROOT
from .dashboard_spec import DATASETS,METRICS,visuals,context
from .pipeline import query


def key_value(value):
    if isinstance(value,(datetime,date)):
        if not isinstance(value,datetime):value=datetime.combine(value,datetime.min.time())
        return str(int(value.replace(tzinfo=timezone.utc).timestamp()*1000))
    if isinstance(value,(int,float)) and abs(value)>1e11:return str(int(value))
    return str(value)


def direct(item,scenario):
    table,timecol,_=DATASETS[item['dataset']];dim=item.get('dimensions',[item['dimension']]) if item['dimension'] else []
    if item.get('columns'):dim=dim+[item['columns']]
    expr=[]
    for name in dim:
        expression=f"date_trunc('month',{name})" if item['kind'] in ['line','bar'] and name in ['purchased_at','cohort_month'] else '"'+name+'"'
        expr.append(expression+' AS "'+name+'"')
    metrics=item.get('metrics',[item['metric']]);expr += [METRICS[m][1]+' AS "'+m+'"' for m in metrics]
    predicates=[];params=[]
    if scenario.get('country'):predicates.append('country=%s');params.append(scenario['country'])
    if scenario.get('start') and item['dataset']!='customers':
        predicates.append(f'{timecol}>=%s AND {timecol}<%s');params.extend([scenario['start'],scenario['end']])
    statement='SELECT '+','.join(expr)+' FROM analytics.'+table
    if predicates:statement+=' WHERE '+' AND '.join(predicates)
    if dim:statement+=' GROUP BY '+','.join(str(i+1) for i in range(len(dim)))
    if item['kind'] not in ['pivot','kpi']:statement+=' ORDER BY "'+item['metric']+'" DESC'
    statement+=' LIMIT '+str(item.get('limit',1000))
    return query(statement,params),dim,metrics


def compare(actual,expected,dims,metrics):
    if len(actual)!=len(expected):return f'row count {len(actual)} != {len(expected)}'
    actualmap={tuple(key_value(r[d]) for d in dims):r for r in actual}
    for row in expected:
        key=tuple(key_value(row[d]) for d in dims)
        if key not in actualmap:return 'group missing: '+str(key)
        for metric in metrics:
            a=actualmap[key].get(metric);b=row[metric]
            if a is None or b is None:
                if a!=b:return f'{metric}: null mismatch'
            else:
                tolerance=Decimal('0.00000001') if 'retention' in metric or metric=='aov' or metric=='rfm_avg_value' else Decimal('0.0001')
                if abs(Decimal(str(a))-Decimal(str(b)))>tolerance:return f'{metric}: value mismatch'
    return None


def main(keys=None):
    state=json.loads((ROOT/'artifacts/deployment.json').read_text());api=API();results=[]
    if keys is not None:
        previous=json.loads((ROOT/'artifacts/chart-validation.json').read_text())
        results=[r for r in previous['checks'] if r['chart'] not in keys]
    scenarios=[dict(name='all'),dict(name='France',country='France'),
      dict(name='Q1-2011',start='2011-01-01',end='2011-04-01'),
      dict(name='France-Q1',country='France',start='2011-01-01',end='2011-04-01'),
      dict(name='empty',country='__NO_SUCH_COUNTRY__')]
    for scenario in scenarios:
        for item in visuals():
            if keys is not None and item['key'] not in keys:continue
            ds=state['datasets'][item['dataset']];filters=[]
            if scenario.get('country'):filters=[{'col':'country','op':'IN','val':[scenario['country']]}]
            time_range=scenario['start']+' : '+scenario['end'] if scenario.get('start') and item['dataset']!='customers' else 'No filter'
            ctx=context(item,ds,filters,time_range)
            try:
                response=api.request('POST','chart/data',json=ctx)['result'][0]
                if response.get('status')!='success':raise RuntimeError('Chart did not report success')
                expected,dims,metrics=direct(item,scenario)
                error=compare(response['data'],expected,dims,metrics)
                results.append(dict(chart=item['key'],scenario=scenario['name'],rows=len(response['data']),passed=error is None,error=error))
            except Exception as e:results.append(dict(chart=item['key'],scenario=scenario['name'],passed=False,error=str(e)))
        print('Verified scenario:',scenario['name'],flush=True)
    linked=api.request('GET',f'dashboard/{state["dashboard_id"]}/charts')['result']
    result=dict(checks=results,passed=sum(x['passed'] for x in results),total=len(results),
      dashboard_linked_chart_count=len(linked),expected_chart_count=len(visuals()))
    (ROOT/'artifacts/chart-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    failed=[r for r in results if not r['passed']]
    print(json.dumps({'passed':result['passed'],'total':result['total'],'linked_charts':len(linked),'failed':failed},ensure_ascii=False))
    if failed or len(linked)!=len(visuals()):raise SystemExit(1)


if __name__=='__main__':main()
