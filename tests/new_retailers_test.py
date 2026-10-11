import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/('refresh-'+name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class PublicRetailers(unittest.TestCase):
 def test_aldi_identity_expiry_and_no_zone(self):
  a=module('aldi');p=dict(objectID='123',name='Queso',productSlug='queso-123',currentPrice=dict(priceValue=2.55,validUntil=1,basePrice=[dict(basePriceValue=6.38,basePriceScale='kg')]),isAvailable=True,assets=[])
  text='<script id="__NEXT_DATA__">'+json.dumps({'props':{'pageProps':{'apiData':json.dumps([['PRODUCT_DETAIL_GET',{'res':{'products':[p]}}]])}}})+'</script>'
  rows=a.parse_page(text,'https://www.aldi.es/producto/queso-123.html','2026-10-11T07:00:00+00:00');self.assertEqual(rows[0]['priceCents'],255);self.assertEqual(rows[0]['referenceCents'],638);self.assertFalse(rows[0]['available']);self.assertFalse(rows[0]['zoneConfirmed'])
  with self.assertRaises(ValueError):a.parse_page(text,'https://www.aldi.es/producto/otro-124.html','2026-10-11T07:00:00+00:00')
 def test_eci_does_not_copy_cart_or_advertising(self):
  a=module('eci');raw=dict(id='B00123',url='/supermercado/B00123-queso/',description='Queso',priceSpecification={'price':'3,00','salePrice':'2,50','measurementUnitPrice':'5,00','pum_description':'Kg'},cart={'secret':'discard'})
  state={'viewData':{'plp':{'products':[raw,{'id':'advert','name':'Advertisement'}],'pagination':{'page':1,'totalPages':2,'path_next':'/supermercado/lacteos/2/'}}}}
  rows,next_path,count=a.parse_page('window.__MOONSHINE_STATE__ = '+json.dumps(state),'2026-10-11T07:00:00+00:00');self.assertEqual(len(rows),1);self.assertEqual(rows[0]['priceCents'],250);self.assertNotIn('cart',rows[0]);self.assertFalse(rows[0]['zoneConfirmed']);self.assertEqual(next_path,'/supermercado/lacteos/2/')
if __name__=='__main__':unittest.main()
