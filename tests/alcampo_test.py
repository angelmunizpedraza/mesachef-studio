import importlib.util,json,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('a',Path(__file__).resolve().parents[1]/'scripts/refresh-alcampo.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class AlcampoTests(unittest.TestCase):
 def test_public_fields_only_and_zone_stays_unconfirmed(self):
  raw={'data':{'customer':{'private':'discarded'},'products':{'productEntities':{'uuid':{'retailerProductId':'123','name':'Leche real','brand':'Marca','price':{'current':{'currency':'EUR','amount':'1.25'},'unit':{'label':'fop.price.per.litre','current':{'currency':'EUR','amount':'1.25'}}},'size':{'value':'1L'},'image':{'src':'https://www.compraonline.alcampo.es/images/1.jpg'},'available':True,'categoryPath':['Leche']}}}}}
  text='<a href="/products/leche-real/123?list=x">Ficha</a><script>window.__INITIAL_STATE__='+json.dumps(raw)+'</script>'
  rows=a.parse_page(text,'2026-10-11T06:00:00+00:00');self.assertEqual(len(rows),1);p=rows[0];self.assertEqual(p['priceCents'],125);self.assertEqual(p['referenceUnit'],'L');self.assertFalse(p['zoneConfirmed']);self.assertIsNone(p['postcode']);self.assertEqual(p['url'],'https://www.compraonline.alcampo.es/products/leche-real/123');self.assertNotIn('customer',p)
 def test_missing_url_or_non_euro_never_becomes_a_valid_fiche(self):
  with self.assertRaises(ValueError):a.parse_page('window.__INITIAL_STATE__='+json.dumps({'data':{'products':{'productEntities':{'a':{'retailerProductId':'1','name':'Producto','price':{'current':{'currency':'USD','amount':'2'}}}}}}}),'2026-10-11T06:00:00+00:00')
 def test_categories_deduplicate_identity_and_skip_campaign_routes(self):
  text='<urlset>'+''.join('<url><loc>'+u+'</loc></url>'for u in ['https://www.compraonline.alcampo.es/categories/leche/OC1','https://www.compraonline.alcampo.es/categories/leche/vaca/OC1','https://www.compraonline.alcampo.es/promotions/leche/OC1','https://evil.invalid/categories/leche/OC2','https://www.compraonline.alcampo.es/categories/campañas/a/OC3'])+'</urlset>'
  self.assertEqual(a.categories(text),['https://www.compraonline.alcampo.es/categories/leche/OC1'])
