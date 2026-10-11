import importlib.util,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('mas',Path(__file__).resolve().parents[1]/'scripts/refresh-mas.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class MasTests(unittest.TestCase):
 def test_uses_only_public_menu_leaf_categories(self):
  text='<a href="https://www.supermercadosmas.com/customer/">cuenta</a><nav data-top-nav><a href="https://www.supermercadosmas.com/frutas/">frutas</a><a href="https://www.supermercadosmas.com/frutas/manzanas/">manzanas</a><a href="https://www.supermercadosmas.com/frutas/marca-x/">marca</a><a href="https://www.supermercadosmas.com/frutas/?p=2">página</a><a href="https://evil.invalid/frutas/">otro</a></nav>'
  self.assertEqual(m.categories(text),['https://www.supermercadosmas.com/frutas/manzanas/'])
 def test_all_first_pages_still_means_partial_without_confirmed_zone(self):
  text='<nav data-top-nav><a href="https://www.supermercadosmas.com/frutas/">frutas</a></nav>';product=m.c.product('mas','1','Manzana','/manzana.html',1.99,m.c.now())
  with tempfile.TemporaryDirectory()as tmp,patch.object(m.c,'TARGET',Path(tmp)),patch.object(m.c,'request',return_value=(text,{})),patch.object(m.c,'page_catalog',return_value={'products':[product]}):
   result=m.collect();self.assertEqual(result['checkedCategories'],1);self.assertEqual(result['coverage'],'partial');self.assertFalse(result['products'][0]['zoneConfirmed']);self.assertEqual(result['pageCoverage'],'first-public-page-only')
