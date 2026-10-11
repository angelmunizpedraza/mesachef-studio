import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('catalogs',Path(__file__).resolve().parents[1]/'scripts/refresh-catalogs.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class CatalogTests(unittest.TestCase):
 def test_money(self):
  self.assertEqual(c.cents('4,89 €'),489);self.assertEqual(c.cents('10.625'),1063)
  for value in [True,'NaN','-1',None,'1e3']:self.assertIsNone(c.cents(value))
 def test_source(self):
  with self.assertRaises(ValueError):c.safe_url('dia','https://www.dia.es.evil.invalid/p/1')
 def test_partial_page_never_claims_zone_or_complete(self):
  from unittest.mock import patch
  raw={'INITIAL_STATE':{'products':[{'sku_id':'123','display_name':'Producto real','url':'/p/123','prices':{'currency':'EUR','price':1.25}}]}}
  import json
  text='<script id="vike_pageContext">'+json.dumps(raw)+'</script>'
  with patch.object(c,'request',return_value=(text,{})):
   result=c.page_catalog('dia');self.assertEqual(result['coverage'],'partial');self.assertFalse(result['products'][0]['zoneConfirmed']);self.assertEqual(result['products'][0]['priceCents'],125)
