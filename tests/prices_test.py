import unittest,importlib.util,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('refresh',Path(__file__).resolve().parents[1]/'scripts/refresh-prices.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
from unittest.mock import patch
class Prices(unittest.TestCase):
 def test_area_and_errors(self):
  def request(path,body=None):
   if body is not None:return {},{'x-customer-wh':'svq1','x-customer-pc':'41011'}
   if '/2/'in path:raise ValueError('404 no disponible')
   return {'id':'1','display_name':'Prueba','price_instructions':{'unit_price':'1.50'},'share_url':module.ORIGIN+'/product/1/prueba','ignored':'NO PUBLICAR'},{}
  with patch.object(module,'request',request):r=module.fetch_catalog('41011',['1','2'])
  self.assertEqual(r['records']['1']['context']['warehouse'],'svq1');self.assertNotIn('ignored',r['records']['1']['raw']);self.assertNotIn('2',r['records']);self.assertIn('404',r['errors']['2'])
 def test_area_mismatch(self):
  with patch.object(module,'request',lambda *a:({}, {'x-customer-wh':'mad3','x-customer-pc':'28001'})):
   with self.assertRaises(ValueError):module.area_for('41011')
 def test_no_success_does_not_create_a_fresh_catalog(self):
  with patch.object(module,'area_for',lambda *a:'svq1'),patch.object(module,'request',side_effect=ValueError('Sin red')):
   with self.assertRaisesRegex(ValueError,'Ninguna'):module.fetch_catalog('41011',['1'])
 def test_invalid_postcode(self):
  with self.assertRaises(ValueError):module.area_for('../etc')
