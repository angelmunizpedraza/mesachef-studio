import importlib.util,json,re,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('dia',Path(__file__).resolve().parents[1]/'scripts/refresh-dia.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
class DiaTests(unittest.TestCase):
 def test_visits_allowed_pages_and_keeps_partial(self):
  visited=[];category='https://www.dia.es/leche/c/L1'
  def request(url):
   visited.append(url);match=re.search('/pag-(\\d+)/',url);n=int(match[1])if match else 1
   raw={'INITIAL_STATE':{'pagination':{'pagination':{'total_pages':6}},'products':[{'sku_id':str(n),'display_name':'Leche '+str(n),'url':'/p/'+str(n),'prices':{'currency':'EUR','price':1.25}}]}}
   links=''.join('<a href="/leche/pag-'+str(i)+'/c/L1">p</a>'for i in range(2,7))
   return '<script id="vike_pageContext">'+json.dumps(raw)+'</script>'+links,{}
  with patch.object(d.c,'request',side_effect=request):_,rows,error=d.read_category(category)
  self.assertEqual(len(rows),5);self.assertEqual(len(visited),5);self.assertFalse(any('/pag-6/'in u for u in visited));self.assertIn('solo se consultaron',error)
 def test_checkpoints_and_preserves_old_dates_on_resume(self):
  category='https://www.dia.es/leche/c/L1';index='<urlset><url><loc>'+category+'</loc></url><url><loc>https://www.dia.es/p/1</loc></url></urlset>'
  product=d.c.product('dia','1','Leche','/p/1',1.25,'2026-10-10T10:00:00+00:00')
  with tempfile.TemporaryDirectory()as tmp,patch.object(d.c,'TARGET',Path(tmp)),patch.object(d.c,'request',return_value=(index,{})),patch.object(d,'read_category',return_value=(category,[product],None))as read:
   first=d.collect();self.assertTrue((Path(tmp)/'dia.json').exists());self.assertEqual(first['checkedCategories'],1)
   again=d.collect(resume=True);self.assertEqual(read.call_count,1);self.assertEqual(again['products'][0]['fetchedAt'],product['fetchedAt'])

 def test_failed_refresh_keeps_previous_fiches_and_their_dates(self):
  category='https://www.dia.es/leche/c/L1';index='<urlset><url><loc>'+category+'</loc></url><url><loc>https://www.dia.es/p/1</loc></url></urlset>'
  product=d.c.product('dia','1','Leche','/p/1',1.25,'2026-10-10T10:00:00+00:00')
  with tempfile.TemporaryDirectory()as tmp,patch.object(d.c,'TARGET',Path(tmp)),patch.object(d.c,'request',return_value=(index,{})),patch.object(d,'read_category',return_value=(category,[],'Fuente no respondió')):
   (Path(tmp)/'dia.json').write_text(json.dumps({'products':[product]}))
   result=d.collect();self.assertEqual(result['products'][0]['fetchedAt'],product['fetchedAt']);self.assertEqual(result['coverage'],'partial');self.assertEqual(result['checkedCategories'],0)
