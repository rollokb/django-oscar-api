import json
import unittest

from oscar.core.loading import get_model
from oscarapi.tests.utils import APITest


Basket = get_model('basket', 'Basket')


class CheckOutTest(APITest):
    fixtures = [
        'product', 'productcategory', 'productattribute', 'productclass',
        'productattributevalue', 'category', 'attributeoptiongroup', 'attributeoption',
        'stockrecord', 'partner', 'orderanditemcharges', 'country'
    ]
    
    def test_checkout(self):
        "Test if an order can be placed as an authenticated user with session based auth."
        self.login(username='nobody', password='nobody')
        response = self.get('api-basket')
        self.assertTrue(response.status_code, 200)
        basket = json.loads(response.content)
        basket_url = basket.get('url')
        basket_id = basket.get('id')

        request = {
            'basket': basket_url,
            'total': '50.0',
            'shipping_method_code': "no-shipping-required",
            'shipping_charge': {
                'currency': 'EUR',
                'excl_tax':'0.00',
                'tax':'0.00'
            },
            "shipping_address": {
                "country": "http://127.0.0.1:8000/api/countries/NL/",
                "first_name": "Henk",
                "last_name": "Van den Heuvel",
                "line1": "Roemerlaan 44",
                "line2": "",
                "line3": "",
                "line4": "Kroekingen",
                "notes": "Niet STUK MAKEN OK!!!!",
                "phone_number": "+31 26 370 4887",
                "postcode": "7777KK",
                "state": "Gerendrecht",
                "title": "Mr"
            }
        }
        response = self.post('api-checkout', **request)
        self.assertEqual(response.status_code, 406)
        response = self.post('api-basket-add-product', url="http://testserver/api/products/1/", quantity=5)
        self.assertEqual(response.status_code, 200)
        response = self.post('api-checkout', **request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Basket.objects.get(pk=basket_id).status, 'Frozen', 'Basket should be frozen after placing order and before payment')

    def test_checkout_implicit_shipping(self):
        "Test if an order can be placed without specifying shipping method."
        self.login(username='nobody', password='nobody')
        response = self.get('api-basket')
        self.assertTrue(response.status_code, 200)
        basket = json.loads(response.content)
        basket_url = basket.get('url')
        basket_id = basket.get('id')

        request = {
            'basket': basket_url,
            'total': '50.0',
            "shipping_address": {
                "country": "http://127.0.0.1:8000/api/countries/NL/",
                "first_name": "Henk",
                "last_name": "Van den Heuvel",
                "line1": "Roemerlaan 44",
                "line2": "",
                "line3": "",
                "line4": "Kroekingen",
                "notes": "Niet STUK MAKEN OK!!!!",
                "phone_number": "+31 26 370 4887",
                "postcode": "7777KK",
                "state": "Gerendrecht",
                "title": "Mr"
            }
        }
        response = self.post('api-checkout', **request)
        self.assertEqual(response.status_code, 406)
        response = self.post('api-basket-add-product', url="http://testserver/api/products/1/", quantity=5)
        self.assertEqual(response.status_code, 200)
        response = self.post('api-checkout', **request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Basket.objects.get(pk=basket_id).status, 'Frozen', 'Basket should be frozen after placing order and before payment')

    def test_checkout_total_error(self):
        "When sending a wrong total, checkout should raise an error"
        self.login(username='nobody', password='nobody')
        response = self.get('api-basket')
        self.assertTrue(response.status_code, 200)
        basket = json.loads(response.content)
        basket_url = basket.get('url')
        basket_id = basket.get('id')

        request = {
            'basket': basket_url,
            'total': '150.0',
            "shipping_address": {
                "country": "http://127.0.0.1:8000/api/countries/NL/",
                "first_name": "Henk",
                "last_name": "Van den Heuvel",
                "line1": "Roemerlaan 44",
                "line2": "",
                "line3": "",
                "line4": "Kroekingen",
                "notes": "Niet STUK MAKEN OK!!!!",
                "phone_number": "+31 26 370 4887",
                "postcode": "7777KK",
                "state": "Gerendrecht",
                "title": "Mr"
            }
        }
        self.response = self.post('api-basket-add-product', url="http://testserver/api/products/1/", quantity=5)
        self.response.assertStatusEqual(200)
        self.response = self.post('api-checkout', **request)
        self.response.assertStatusEqual(406)
        self.response.assertValueEqual('non_field_errors', ["Total incorrect 150.0 != 50.00"])

    def test_total_is_optional(self):
        "Total should be an optional value"
        self.login(username='nobody', password='nobody')
        response = self.get('api-basket')
        self.assertTrue(response.status_code, 200)
        basket = json.loads(response.content)
        basket_url = basket.get('url')
        basket_id = basket.get('id')

        request = {
            'basket': basket_url,
            "shipping_address": {
                "country": "http://127.0.0.1:8000/api/countries/NL/",
                "first_name": "Henk",
                "last_name": "Van den Heuvel",
                "line1": "Roemerlaan 44",
                "line2": "",
                "line3": "",
                "line4": "Kroekingen",
                "notes": "Niet STUK MAKEN OK!!!!",
                "phone_number": "+31 26 370 4887",
                "postcode": "7777KK",
                "state": "Gerendrecht",
                "title": "Mr"
            }
        }
        self.response = self.post('api-basket-add-product', url="http://testserver/api/products/1/", quantity=5)
        self.response.assertStatusEqual(200)
        self.response = self.post('api-checkout', **request)
        self.response.assertStatusEqual(200)
        
    def test_can_login_with_frozen_user_basket(self):
        "When a user has an unpaid order, he should still be able to log in"
        self.test_checkout()
        self.delete('api-login')
        self.get('api-basket')
        self.post('api-basket-add-product', url="http://testserver/api/products/1/", quantity=5)
        self.response = self.post('api-login', username='nobody', password='nobody')
        self.response.assertStatusEqual(200)
        self.login(username='nobody', password='nobody')

    def test_checkout_creates_an_order(self):
        "After checkout has been done, a user should have gained an order object"
        self.test_checkout()
        self.response = self.get('order-list')
        self.assertEqual(len(self.response), 1, 'An order should have been created.')

    @unittest.skip
    def test_checkout_header(self):
        "Prove that the user 'nobody' can checkout his cart when authenticating with header session"
        self.fail('Please add implementation')

    @unittest.skip
    def test_anonymous_checkout(self):
        "Can anonymous users check out a cart? If so prove it with a test"
        self.fail('Please add implementation')

    @unittest.skip
    def test_checkout_permissions(self):
        "Prove that someone can not check out someone elses cart by mistake"
        self.fail('Please add implementation')
    
    @unittest.skip
    def test_cart_immutable_after_checkout(self):
        "Prove that the cart can not be changed with the webservice by users in any way after checkout has been made."
        self.fail("It might be that admin users can actually still modify a checked out cart (frozen)")

    @unittest.skip
    def test_client_can_not_falsify_picing(self):
        "Prove that the total and shippingcharge variable sent along with a checkout request, can not be manipulated"
        self.fail('checkout variable can not be used to buy products for prices they are not available at.')
